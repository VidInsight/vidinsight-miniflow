from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing
import threading
import logging
import time

# Utility
from miniflow.utils import setup_logging

# Miniflow Database Module
from miniflow.database_manager import DatabaseEngine
from miniflow.database_manager import DatabaseOrchestration

setup_logging()
logger = logging.getLogger(__name__)
logger.debug(f"{__name__} Logger tanımları tanımlandı")

class MiniflowOutputMonitor:
    def __init__(self, database_engine: DatabaseEngine, database_orchestration: DatabaseOrchestration, execution_engine,
                 polling_interval=0.5, batch_size=50, worker_threads=4):
       
        # Database Manager Değişkenleri -> MiniflowCore tarafında kullanılacak ve iletilecek 
        self.database_engine = database_engine
        self.database_orchestration = database_orchestration

        # Execution Engine Değişkeni -> MiniflowCore tarafında kullanılacak ve iletilecek 
        self.execution_engine = execution_engine

        # Input Monitor Parametreleri
        self.batch_size = batch_size                                                                # Batch boyutu -> Kaçar Kaçar Görevler İşleme Alınacak
        self.worker_count = min(worker_threads, multiprocessing.cpu_count())                        # Worker sayısı -> Kaç eş zamanlı thread çalıştırılacak
        self.running = False                                                                        # Çalışma durumu -> Modül çalışıyor mu?
        self.main_thread = None                                                                     # Ana thread 
        self.worker_pool = None                                                                     # Worker pool 
        self.shutdown_event = threading.Event()                                                     # Shutdown event

        # Adaptive polling parametreleri
        self.min_polling_interval = 0.1
        self.max_polling_interval = 2.0
        self.current_polling_interval = polling_interval
        self.empty_cycles = 0
        
        # Statistics
        self.stats = {
            'failed_results': 0,
            'successful_results': 0,
            'total_processed': 0
        }

    def is_running(self):
        return self.running and self.main_thread and self.main_thread.is_alive() 
    
    def start(self):
        if self.running:
            logger.warning("Output monitor zaten çalışıyor")
            return True

        self.running = True
        self.shutdown_event.clear() 

        # Initialize thread pool for workers
        logger.debug(f"Worker pool oluşturuluyor - max_workers: {self.worker_count}")
        self.worker_pool = ThreadPoolExecutor(
            max_workers=self.worker_count, 
            thread_name_prefix="OutputWorker"
            )

        # Start main monitoring thread
        logger.debug("Output monitor ana thread başlatılıyor")
        self.main_thread = threading.Thread(
            target=self.__monitoring_loop, 
            name="OutputMonitorThread",daemon=True
            )
        self.main_thread.start()

        logger.info("Output monitor başarıyla başlatıldı")
        return True
    
    def stop(self):
        logger.info("Output monitor durduruluyor")
        
        if not self.running:
            logger.debug("Output monitor zaten durdurulmuş")
            return True
        
        self.running = False
        self.shutdown_event.set()
        
        # Shutdown thread pool
        if self.worker_pool:
            logger.debug("Worker pool kapatılıyor")
            self.worker_pool.shutdown(wait=True)
        
        # Wait for main thread
        if self.main_thread and self.main_thread.is_alive():
            logger.debug("Ana thread sonlandırılması bekleniyor")
            self.main_thread.join(timeout=5)

        logger.info("Output Monitor başarıyla durduruldu")
        return True
    
    def __monitoring_loop(self):
        logger.info("Output Monitor ana işlem döngüsü başlatıldı")
        while self.running and not self.shutdown_event.is_set():
            try:
                # ------------------------------------------------------------
                # 1. Görevleri Execution Engine üzerinen toplar
                # ------------------------------------------------------------
                results = self.__collect_results()

                if not results:
                    # ------------------------------------------------------------
                    # 1.1 Eğer herhangi bir sonuç yoksa srogu aralığını düşür
                    # ------------------------------------------------------------
                    self.empty_cycles += 1
                    self.__adjust_polling_interval(idle=True)
                    time.sleep(self.current_polling_interval)
                    continue
                
                # ------------------------------------------------------------
                # 1.2 Görevleri kontrol eder ve hazır olanları işleme alır 
                # ------------------------------------------------------------
                self.empty_cycles = 0
                self.__adjust_polling_interval(idle=False)

                logger.debug(f"{len(results)} sonuç işleme için alındı")

                # ------------------------------------------------------------
                # 2. Gelen çıktıları veri tabanına işle
                # ------------------------------------------------------------
                self.__process_results(results)
                time.sleep(self.current_polling_interval)
            except Exception as e:  
                logger.error(f"Output monitor döngü hatası: {e}")
                time.sleep(1)

        logger.debug("Output monitor döngüsü sonlandırıldı")

    def __collect_results(self):
        if not self.execution_engine:
            logger.error("Execution Engine mevcut değil")
            raise ValueError("Output Monitor için Execution Engine mecvut değil")
        
        # ------------------------------------------------------------
        # 1. Execution Engine üzerinden sonlanmış işlemleri çek
        # ------------------------------------------------------------
        raw_results = self.execution_engine.get_output_items_bulk(
                max_items=self.batch_size, 
                timeout=0.1
                )
        
        logger.debug(f"Execution Engine'dan {len(raw_results)} ham sonuç toplandı")

        # ------------------------------------------------------------
        # 2. Çıtıları valide et
        # ------------------------------------------------------------
        valid_results = []
        for result in raw_results:
            if self.__validate_result_format(result):
                valid_results.append(result)
                logger.debug(f"Geçerli sonuç - node: {result.get('node_id', 'unknown')}")
            else:
                logger.warning(f"Geçersiz sonuç formatı: {result}")
                self.stats['failed_results'] += 1   

        logger.info(f"{len(valid_results)} sonuç doğrulandı")
        return valid_results

    def __validate_result_format(self, result):
        if not isinstance(result, dict):
            logger.debug(f"Sonuç dict değil: {type(result)}")
            return False
        
        required_fields = ['execution_id', 'node_id', 'status']
        for field in required_fields:
            if field not in result:
                logger.debug(f"Gerekli alan eksik: {field}")
                return False
            
        if result['status'] not in ['success', 'failed']:
            logger.debug(f"Geçersiz status: {result['status']}")
            return False
        
        # For failed results, we don't require result_data
        if result['status'] == 'failed':
            return True
            
        # For successful results, accept either 'results' or 'result_data' field
        if 'results' not in result and 'result_data' not in result:
            logger.debug("Result data eksik (ne 'results' ne de 'result_data' var)")
            return False
        
        return True
    
    def __adjust_polling_interval(self, idle=False):
        if idle:
            logger.debug("Pooling Interval aralığı arttırılıyor")
            # Increase interval when idle (up to max)
            self.current_polling_interval = min(
                self.current_polling_interval * 1.2,
                self.max_polling_interval
            )
        else:
            logger.debug("Pooling Interval aralığı azaltılıyor")
            # Decrease interval when busy (down to min)
            self.current_polling_interval = max(
                self.current_polling_interval * 0.8,
                self.min_polling_interval
            )

    def __process_results(self, results):
        if not results:
            return
        
        # ------------------------------------------------------------
        # 1. Execution Id üzerinden görevleri gruplandır
        # ------------------------------------------------------------
        execution_groups = {}
        for result in results:
            execution_id = result.get('execution_id')
            if execution_id not in execution_groups:
                execution_groups[execution_id] = []
            execution_groups[execution_id].append(result)

        # ------------------------------------------------------------
        # 2. Grupları multithreading ile veri tabanına işle
        # ------------------------------------------------------------
        futures = []
        for execution_id, group_result in execution_groups.items():
            future = self.worker_pool.submit(
                self.__process_execution_group, 
                group_result
            )
            futures.append(future)

        # ------------------------------------------------------------
        # 3. İşlem çıktılarını thread'lerden topla
        # ------------------------------------------------------------
        successful_results = 0
        failed_results = 0

        for future in as_completed(futures):
            try:
                success_count, fail_count = future.result()
                successful_results += success_count
                failed_results += fail_count
            except Exception as e:
                logger.error(f"Future işleme hatası: {e}")
                failed_results += 1

        logger.info(f"Sonuç işleme tamamlandı - başarılı: {successful_results}, başarısız: {failed_results}")
        
    def __process_execution_group(self, group_result):
        success_count = 0
        fail_count = 0

        for result in group_result:
            try:
                # Handle both 'results' and 'result_data' field names
                result_data = result.get("result_data") or result.get("results")

                # Sonuçları veri tabanına işle          
                # Process result through database manager
                with self.database_engine.get_session_context() as session:
                    success = self.database_orchestration.process_execution_result(session, result)
                    if success:
                        success_count += 1
                    else:
                        fail_count += 1
            except Exception as e:
                logger.error(f"Error processing result: {e}")
                fail_count += 1
        return success_count, fail_count    
    