import os
import json
import time
import threading
import multiprocessing
from queue import Queue as ThreadQueue
from concurrent.futures import ThreadPoolExecutor, as_completed

from .. import database
from . import context_manager


class MiniflowInputMonitor:
    def __init__(self, db_path, polling_interval=0.1, manager=None, batch_size=50, worker_threads=4):
        # Veritabanı Parametreleri (SQLite için gerekli)
        self.db_path = db_path                                                                      # Veritabanı yolu
        self.polling_interval = polling_interval                                                    # Polling interval

        # Execution Engine Manager
        self.manager = manager                                                                      # Execution Engine Manager

        # Input Monitor Parametreleri
        self.batch_size = batch_size                                                                # Batch boyutu -> Kaçar Kaçar Görevler İşleme Alınacak
        self.worker_count = min(worker_threads, multiprocessing.cpu_count())                        # Worker sayısı -> Kaç eş zamanlı thread çalıştırılacak
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
        

    def is_running(self):
        """
        DESC: Çalışma durumunu kontrol eder
        RETURNS: Çalışıyorsa 'True', Çalışmıyorsa 'False'
        """
        return self.running and self.main_thread and self.main_thread.is_alive()                   # Çalışıyorsa 'True', Çalışmıyorsa 'False'
    
    def get_stats(self):
        """
        DESC: Performans metriklerini döndürür
        RETURNS: Performans metrikleri (dict)
        """
        return {
            **self.stats,
            'worker_threads': self.worker_count,                                                  # Worker sayısı
            'batch_size': self.batch_size,                                                        # Batch boyutu
            'running': self.running                                                               # Çalışma durumu
        } 
    
    def start(self):
        """
        DESC: Modülü başlatır
        RETURNS: Başarılı ise 'True', Başarısız ise 'False'
        """
        if self.running:
            return True
        
        self.running = True                                                                         # Çalışma durumunu True yap
        self.shutdown_event.clear()                                                                 # Shutdown event'i temizle -> ???

        # Initialize thread pool for workers
        self.worker_pool = ThreadPoolExecutor(                                                      # Worker pool oluştur -> Execution Engine'na eş zamanlı veri göndermek için threadler
            max_workers=self.worker_count,                                                          # Worker sayısı
            thread_name_prefix="InputWorker"                                                        # Thread ismi
        )

        # Start main monitoring thread
        self.main_thread = threading.Thread(                                                        # Ana thread oluştur -> Döngü threadi
            target=self.__monitoring_loop,                                                          # Monitoring Loop'u çalıştırır
            name="InputMonitorThread",                                                              # Thread ismi
            daemon=True                                                                             # Thread'in daemon olup olmadığı -> Arka planda çalışır
        )
        self.main_thread.start()                                                                    # Ana thread'i başlat
        
        return True

    def stop(self):
        """
        DESC: Modülü durdurur
        RETURNS: Başarılı ise 'True', Başarısız ise 'False'
        """
        if not self.running:
            return True                                                                              
        
        self.running = False                                                                         # Çalışma durumunu False yap
        self.shutdown_event.set()                                                                    # Shutdown event'i set et 

         # Shutdown thread pool
        if self.worker_pool:
            self.worker_pool.shutdown(wait=True)                                                    # Worker pool'u shutdown et -> Worker threadleri durdurulur
        
        # Wait for main thread
        if self.main_thread and self.main_thread.is_alive():
            self.main_thread.join(timeout=5)                                                        # Ana thread'i beklemeye al -> 5 saniye bekler 
                                                                                                    # Ana thread'i durdur -> While sorgusu üzerinden çıkılır

        return True
    
    def __monitoring_loop(self):
        """
        DESC: Ana işlem döngüsü -> Görevleri kontrol eder ve hazır olanları işleme alır
        RETURNS: None
        """

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
                    time.sleep(self.polling_interval)
                    continue

                tasks = ready_tasks.data if ready_tasks.data else []

                # ------------------------------------------------------------
                # 2. Görevleri işleme alır ve Execution Engine'e gönderir
                # ------------------------------------------------------------
                if tasks:
                    self.__send_tasks(tasks)
                
                # Eğer görevleri çektiysen, polling interval'e göre bekle
                time.sleep(self.polling_interval)
                
            except Exception as e:
                time.sleep(1)

    def __send_tasks(self, tasks):
        """
        DESC: Görevleri işleme alır ve parallelism engine'e gönderir
        RETURNS: None
        """
        if not tasks:
            return
        
        # Check if manager is available
        if not self.manager:
            print("[INPUT_MONITOR] ERROR: No manager available")
            return
        
        print(f"[INPUT_MONITOR] Processing {len(tasks)} ready tasks")

        payload_futures = []                                                                  
        for task in tasks:
            future = self.worker_pool.submit(self.__create_task_payload, task) 
            payload_futures.append(future)

        prepared_payloads = []
        task_ids = []
        
        for future in as_completed(payload_futures, timeout=10):
            try:
                payload = future.result()
                if payload:
                    prepared_payloads.append(payload)
                    task_ids.append(payload['task_id'])
                    print(f"[INPUT_MONITOR] Prepared payload for task: {payload['node_name']}")
            except Exception as e:
                print(f"[INPUT_MONITOR] Error creating payload: {e}")

        self.stats['parallel_operations'] += len(payload_futures)
        print(f"[INPUT_MONITOR] Prepared {len(prepared_payloads)} payloads from {len(tasks)} tasks")
        
        if prepared_payloads:
            # Send tasks to parallelism engine
            print(f"[INPUT_MONITOR] Sending {len(prepared_payloads)} tasks to parallelism engine")
            success = self.manager.put_items_bulk(prepared_payloads)
            print(f"[INPUT_MONITOR] Bulk send result: {success}")
            
            if success:
                # Mark tasks as running and remove from queue
                delete_operations = [
                    {
                        'type': 'delete',
                        'query': 'DELETE FROM execution_queue WHERE id = ?',
                        'params': (task_id,)
                    }
                    for task_id in task_ids
                ]
                
                print(f"[INPUT_MONITOR] Removing {len(task_ids)} tasks from queue")
                delete_result = database.execute_bulk_operations(self.db_path, delete_operations)
                if delete_result.success:
                    self.stats['tasks_processed'] += len(prepared_payloads)
                    self.stats['batches_processed'] += 1
                    self.stats['queue_operations'] += 1
                    self.stats['database_operations'] += 1
                    print(f"[INPUT_MONITOR] Successfully processed {len(prepared_payloads)} tasks")
                else:
                    print(f"[INPUT_MONITOR] Failed to remove tasks from queue: {delete_result.error}")
            else:
                print(f"[INPUT_MONITOR] Failed to send tasks to parallelism engine")
        else:
            print(f"[INPUT_MONITOR] No payloads prepared from {len(tasks)} tasks")

    def __create_task_payload(self, task):
        """
        DESC: Görevleri işleme alır ve parallelism engine'e gönderir
        RETURNS: None
        """

        try:
            # Get node info (this will use connection pool)
            node_result = database.fetch_one(
                self.db_path,
                "SELECT id, workflow_id, name, type, script, params FROM nodes WHERE id = ?",
                (task['node_id'],)
            )
            
            if not node_result.success or not node_result.data:
                # TODO: logger - error
                return None
            
            node_info = node_result.data
            
            # Parse parameters
            params_dict = database.safe_json_loads(node_info.get('params', '{}'))
            if isinstance(params_dict, str):
                try:
                    params_dict = json.loads(params_dict)
                except json.JSONDecodeError:
                    params_dict = {}
            
            # Create context (this can be optimized further with bulk operations)
            context = context_manager.create_context_for_task(
                params_dict,
                task['execution_id'],
                self.db_path
            )
            
            # Build payload
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
            # TODO: logger - error
            return None