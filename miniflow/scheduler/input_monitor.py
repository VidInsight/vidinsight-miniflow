import os
import json
import time
import threading
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, as_completed

# Logger setup
import logging
logger = logging.getLogger("miniflow.scheduler.input_monitor")

from .. import database
from . import context_manager


class MiniflowInputMonitor:
    def __init__(self, db_path, polling_interval=0.1, manager=None, batch_size=50, worker_threads=4):
        logger.debug("Input Monitor kuruluyor . . . ")
        logger.debug(f"Input Monitor\n\tdb_path: {db_path}\n\tpooling interval: {polling_interval}\n\tbatch size: {batch_size}\n\tworker_thread: {worker_threads}")
        
        # Veritabanı Parametreleri (SQLite için gerekli)
        self.db_path = db_path                                                                      # Veritabanı yolu
        self.polling_interval = polling_interval                                                    # Polling interval

        # Execution Engine Manager
        self.manager = manager                                                                      # Execution Engine Manager

        # Input Monitor Parametreleri
        self.batch_size = batch_size                                                                # Batch boyutu -> Kaçar Kaçar Görevler İşleme Alınacak
        self.worker_count = min(worker_threads, multiprocessing.cpu_count())                        # Worker sayısı -> Kaç eş zamanlı thread çalıştırılacak
        logger.debug(f"Worker sayısı {self.worker_count} olarak belirlendi")
        self.running = False                                                                        # Çalışma durumu -> Modül çalışıyor mu?
        self.main_thread = None                                                                     # Ana thread 
        self.worker_pool = None                                                                     # Worker pool 
        self.shutdown_event = threading.Event()                                                     # Shutdown event

        # Performans Metrikleri
        self.stats = {
            'tasks_processed': 0,                                                                   # İşlenen görev sayısı
            'batches_processed': 0,                                                                 # İşlenen batch sayısı
            'parallel_operations': 0,                                                               # Paralel işlem sayısı
            'database_operations': 0,                                                               # Veritabanı işlem sayısı
            'queue_operations': 0                                                                   # Kuyruk işlem sayısı
        }
        
        # Scripts directory
        current_dir = os.path.dirname(os.path.abspath(__file__))                                    # Mevcut dizin
        miniflow_dir = os.path.dirname(current_dir)                                                 # Miniflow dizini
        project_root = os.path.dirname(miniflow_dir)                                                # Proje kök dizini
        self.scripts_dir = os.path.join(project_root, 'scripts')                                    # Scripts dizini (Tam Yol)
        
        logger.debug(f"Kullanılacak scripts yolu/path'i {self.scripts_dir}")
        logger.debug("Input Monitor başraıyla kuruldu")

    def is_running(self):
        return self.running and self.main_thread and self.main_thread.is_alive()                   # Çalışıyorsa 'True', Çalışmıyorsa 'False'
    
    def get_stats(self):
        return {
            **self.stats,
            'worker_threads': self.worker_count,                                                    # Worker sayısı
            'batch_size': self.batch_size,                                                          # Batch boyutu
            'running': self.running                                                                 # Çalışma durumu
        } 
    
    def start(self):
        logger.debug("Input monitor başlatılıyor")
        
        if self.running:
            logger.warning("Input monitor zaten çalışıyor")
            return True
        
         # Database connection check
        logger.debug("Database bağlantısı kontrol ediliyor")
        connection_result = database.check_database_connection(self.db_path)                       # Veritabanı bağlantısını kontrol et
        if not connection_result.success:
            logger.error(f"Database bağlantı hatası: {connection_result.error}")
            return False
        logger.debug("Database bağlantısı başarılı")

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
        logger.info("Input monitor durduruluyor")
        
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
    
    def __monitoring_loop(self):
        logger.info("Input Monitor ana işlem döngüsü başlatıldı")

        while self.running and not self.shutdown_event.is_set():                                    
            try:
                # ------------------------------------------------------------
                # 1. Görevleri kontrol eder ve hazır olanları işleme alır 
                # Hazır görevler -> dependency_count = 0 olan görevler -> priority'ye göre sıralanır
                # ------------------------------------------------------------
                ready_tasks = database.fetch_all(
                    db_path=self.db_path,
                    query="""
                    SELECT eq.*, n.name as node_name, n.type as node_type
                    FROM execution_queue eq
                    JOIN nodes n ON eq.node_id = n.id
                    WHERE eq.dependency_count = 0 
                    ORDER BY eq.priority DESC, eq.id ASC
                    LIMIT ?
                    """,
                    params=(self.batch_size,)                                                   
                )

                # Eğer görevleri çekemediysen, polling interval'e göre bekle
                if not ready_tasks.success:
                    logger.warning("Hazır görevler alınırken hata oluştu")
                    logger.debug(f"{self.polling_interval} kadar işleme ara veriliyor")
                    time.sleep(self.polling_interval)
                    continue

                tasks = ready_tasks.data if ready_tasks.data else []

                # ------------------------------------------------------------
                # 2. Görevleri işleme alır ve Execution Engine'e gönderir
                # ------------------------------------------------------------
                if tasks:
                    logger.debug(f"{len(tasks)} hazır görev bulundu")
                    self.__send_tasks(tasks)
                
                # Eğer görevleri çektiysen, polling interval'e göre bekle
                time.sleep(self.polling_interval)
                
            except Exception as e:
                logger.error(f"Input monitor döngü hatası: {e}")
                time.sleep(1)
        
        logger.debug("Input monitor döngüsü sonlandırıldı")

    def __send_tasks(self, tasks):
        if not tasks:
            return
        
        # Check if manager is available
        if not self.manager:
            logger.error("Görev gönderimi için Manager mevcut değil")
            raise ValueError("Input Monitor için Manager mecvut değil")
        
        logger.info(f"{len(tasks)} hazır görev işleniyor")

        # ------------------------------------------------------------
        # 1. Her görev (task) için context oluştur
        # Thread Pool üzeirnde multithread olarak gerçekleştir
        # ------------------------------------------------------------
        payload_futures = []                                                                  
        for task in tasks:
            future = self.worker_pool.submit(self.__create_task_payload, task) 
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
                    task_ids.append(payload['task_id'])
                    logger.debug(f"Payload hazırlandı - task: {payload['node_name']}")
            except Exception as e:
                logger.error(f"Payload oluşturma hatası: {e}")

        logger.info(f"{len(prepared_payloads)} payload hazırlandı ({len(tasks)} task'dan)")
        
        # ------------------------------------------------------------
        # 3. Görevleri Execution Engine'a işleme gönder
        # Manager üzerinde gerçekleştilriyor
        # ------------------------------------------------------------

        if prepared_payloads:
            # ------------------------------------------------------------
            # 3.1 Görevleri Execution Engine'a bulk olrak gönder
            # ------------------------------------------------------------
            logger.info(f"{len(prepared_payloads)} task parallelism engine'e gönderiliyor")
            success = self.manager.put_items_bulk(prepared_payloads)                                # Hazır işlemleri motor'a gönder
            logger.debug(f"Bulk gönderim sonucu: {success}")
            
            if success:
                # ------------------------------------------------------------
                # 3.2 Göreve gönderilen görevleri tablodan sil
                # ------------------------------------------------------------
                delete_operations = [
                    {
                        'type': 'delete',
                        'query': 'DELETE FROM execution_queue WHERE id = ?',
                        'params': (task_id,)
                    }
                    for task_id in task_ids
                ]
                
                logger.debug(f"{len(task_ids)} task kuyruktan kaldırılıyor")
                delete_result = database.execute_bulk_operations(self.db_path, delete_operations)
                if delete_result.success:
                    logger.info(f"{len(prepared_payloads)} task başarıyla işlendi")
                else:
                    logger.error(f"Task'lar kuyruktan kaldırılamadı: {delete_result.error}")
            else:
                logger.error("Task'lar parallelism engine'e gönderilemedi")
        else:
            logger.warning(f"{len(tasks)} task'dan hiç payload hazırlanamadı")

    def __create_task_payload(self, task):
        try:
            # ------------------------------------------------------------
            # 1. Verilen görevin (task) id'si üzerinden görevi çek
            # ------------------------------------------------------------
            node_result = database.fetch_one(
                self.db_path,
                "SELECT id, workflow_id, name, type, script, params FROM nodes WHERE id = ?",
                (task['node_id'],)
            )
            
            if not node_result.success or not node_result.data:
                logger.error(f"Node bilgisi alınamadı - node_id: {task['node_id']}")
                return None
            
            node_info = node_result.data
            
            # ------------------------------------------------------------
            # 2. Düğümüm parametre değerlerini çek - variables
            # ------------------------------------------------------------
            params_dict = database.safe_json_loads(node_info.get('params', '{}'))
            if isinstance(params_dict, str):
                try:
                    params_dict = json.loads(params_dict)
                except json.JSONDecodeError:
                    params_dict = {}
            
            # ------------------------------------------------------------
            # 3. Düğüm için payload oluştur - context manager
            # ------------------------------------------------------------
            context = context_manager.create_context_for_task(
                params_dict,
                task['execution_id'],
                self.db_path
            )
            
            # ------------------------------------------------------------
            # 4. Çıktılar ile JSON/DICT payload oluştur
            # ------------------------------------------------------------
            task_payload = {
                "task_id": task['id'],
                "execution_id": task['execution_id'],
                "workflow_id": node_info['workflow_id'],
                "node_id": task['node_id'],
                "script_path": os.path.join(self.scripts_dir, node_info.get('script', '')),
                "context": context,
                "node_name": node_info['name'],
                "node_type": node_info['type']
            }
            
            return task_payload
            
        except Exception as e:
            logger.error(f"Task payload oluşturma hatası: {e}")
            return None