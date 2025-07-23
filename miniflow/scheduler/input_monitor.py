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

class MiniflowInputMonitor:
    def __init__(self, database_engine: DatabaseEngine, database_orchestration: DatabaseOrchestration, execution_engine,
                 polling_interval=0.1, batch_size=50, worker_threads=4):
       
        # Database Manager Değişkenleri -> MiniflowCore tarafında kullanılacak ve iletilecek 
        self.database_engine = database_engine
        self.database_orchestration = database_orchestration

        # Execution Engine Değişkeni -> MiniflowCore tarafında kullanılacak ve iletilecek 
        self.execution_engine = execution_engine

        # Input Monitor Parametreleri
        self.polling_interval = polling_interval                                                    # Polling interval
        self.batch_size = batch_size                                                                # Batch boyutu -> Kaçar Kaçar Görevler İşleme Alınacak
        self.worker_count = min(worker_threads, multiprocessing.cpu_count())                        # Worker sayısı -> Kaç eş zamanlı thread çalıştırılacak
        self.running = False                                                                        # Çalışma durumu -> Modül çalışıyor mu?
        self.main_thread = None                                                                     # Ana thread 
        self.worker_pool = None                                                                     # Worker pool 
        self.shutdown_event = threading.Event()                                                     # Shutdown event

    def is_running(self):
        return self.running and self.main_thread and self.main_thread.is_alive() 
    
    def start(self):
        if self.is_running():
            logger.warning("Input monitor zaten çalışıyor")
            return
        
        self.running = True                                                                         # Çalışma durumunu True yap
        self.shutdown_event.clear()                                                                 # Shutdown event'i temizle -> ???

        # Initialize thread pool for workers
        logger.debug(f"Worker pool oluşturuluyor - max_workers: {self.worker_count}")
        self.worker_pool = ThreadPoolExecutor(                                                      # Worker pool oluştur -> Execution Engine'na eş zamanlı veri göndermek için threadler
            max_workers=self.worker_count,                                                          # Worker sayısı
            thread_name_prefix="InputWorker"                                                        # Thread ismi
        )

        # Start main monitoring thread
        logger.debug("Input monitor ana thread başlatılıyor")
        self.main_thread = threading.Thread(                                                        # Ana thread oluştur -> Döngü threadi
            target=self.__monitoring_loop,                                                          # Monitoring Loop'u çalıştırır
            name="InputMonitorThread",                                                              # Thread ismi
            daemon=True                                                                             # Thread'in daemon olup olmadığı -> Arka planda çalışır
        )
        self.main_thread.start()                                                                    # Ana thread'i başlat
        
        logger.info("Input monitor başarıyla başlatıldı")
        return True
        
    def stop(self):        
        if not self.running:
            logger.debug("Input monitor zaten durdurulmuş")
            return True                                                                              
        
        self.running = False                                                                         # Çalışma durumunu False yap
        self.shutdown_event.set()                                                                    # Shutdown event'i set et 

        # Shutdown thread pool
        if self.worker_pool:
            logger.debug("Worker pool kapatılıyor")
            self.worker_pool.shutdown(wait=True)                                                    # Worker pool'u shutdown et -> Worker threadleri durdurulur
        
        # Wait for main thread
        if self.main_thread and self.main_thread.is_alive():
            logger.debug("Ana thread sonlandırılması bekleniyor")
            self.main_thread.join(timeout=5)                                                        # Ana thread'i beklemeye al -> 5 saniye bekler 
                                                                                                    # Ana thread'i durdur -> While sorgusu üzerinden çıkılır

        logger.info("Input Monitor başarıyla durduruldu")
        return True

    def _create_task_payload_with_session(self, task):
        """Helper method to create task payload with database session"""
        with self.database_engine.get_session_context() as session:
            return self.database_orchestration.create_task_payload(session, task)
        
    def __monitoring_loop(self):
        logger.info("Input Monitor ana işlem döngüsü başlatıldı")

        while self.running and not self.shutdown_event.is_set():                                    
            try:
                # ------------------------------------------------------------
                # 1. Görevleri kontrol eder ve hazır olanları işleme alır 
                # Hazır görevler -> dependency_count = 0 olan görevler -> priority'ye göre sıralanır
                # ------------------------------------------------------------
                ready_tasks = None
                with self.database_engine.get_session_context() as session:
                    ready_tasks = self.database_orchestration.get_ready_tasks(session, self.batch_size)

                # ------------------------------------------------------------
                # 2. Görevleri işleme alır ve Execution Engine'e gönderir
                # ------------------------------------------------------------
                if ready_tasks:
                    logger.debug(f"{len(ready_tasks)} hazır görev bulundu")
                    self.__send_tasks(ready_tasks)
                
                # Eğer görevleri çektiysen, polling interval'e göre bekle
                time.sleep(self.polling_interval)
                
            except Exception as e:
                logger.error(f"Input monitor döngü hatası: {e}")
                time.sleep(1)
        
        logger.debug("Input monitor döngüsü sonlandırıldı")

    def __send_tasks(self, tasks):
        # Check if manager is available
        if not self.execution_engine:
            logger.error("Görev gönderimi için Execution Engine mevcut değil")
            raise ValueError("Input Monitor için Execution Engine mecvut değil")
        
        logger.info(f"{len(tasks)} hazır görev işleniyor")

        # ------------------------------------------------------------
        # 1. Her görev (task) için context oluştur
        # Thread Pool üzeirnde multithread olarak gerçekleştir
        # ------------------------------------------------------------
        payload_futures = []                                                                  
        for task in tasks:
            future = self.worker_pool.submit(self._create_task_payload_with_session, task)
            payload_futures.append(future)

        # ------------------------------------------------------------
        # 2. Threadlerden gelen çıktıları topla
        # Future yapısı ile işlem gerçekleştiriliyor
        # ------------------------------------------------------------

        prepared_payloads = []
        task_ids = []
        
        for future in as_completed(payload_futures, timeout=10):
            try:
                payload = future.result()
                if payload:
                    prepared_payloads.append(payload)
                    task_ids.append(payload['id'])
                    logger.debug(f"Payload hazırlandı - task: {payload['node_name']}")
            except Exception as e:
                logger.error(f"Payload oluşturma hatası: {e}")

        logger.info(f"{len(prepared_payloads)} payload hazırlandı ({len(tasks)} task'dan)")
        
        # ------------------------------------------------------------
        # 3. Görevleri Execution Engine'a işleme gönder
        #Execution Engine üzerinde gerçekleştilriyor
        # ------------------------------------------------------------

        if prepared_payloads:
            # ------------------------------------------------------------
            # 3.1 Görevleri Execution Engine'a bulk olrak gönder
            # ------------------------------------------------------------
            logger.info(f"{len(prepared_payloads)} task parallelism engine'e gönderiliyor")
            success = self.execution_engine.put_items_bulk(prepared_payloads)                                # Hazır işlemleri motor'a gönder
            logger.debug(f"Bulk gönderim sonucu: {success}")
            
            if success:
                # ------------------------------------------------------------
                # 3.2 Göreve gönderilen görevleri tablodan sil
                # ------------------------------------------------------------
                with self.database_engine.get_session_context() as session:
                    removed_count = self.database_orchestration.remove_completed_tasks(session, task_ids)
                    logger.debug(f"{removed_count} tasks removed from queue")
            else:
                logger.error("Task'lar parallelism engine'e gönderilemedi")
        else:
            logger.warning(f"{len(tasks)} task'dan hiç payload hazırlanamadı")