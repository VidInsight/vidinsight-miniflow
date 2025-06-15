import time
import threading

from .. import database
from . import context_manager


class QueueMonitor:
    """
    Amaç: Execution queue'yu izler ve hazır taskları işler
    """
    
    def __init__(self, db_path, polling_interval=5):
        """
        Amaç: Queue monitor'u başlatır
        Döner: Yok (constructor)
        """
        self.db_path = db_path
        self.polling_interval = polling_interval
        self.running = False
        self.thread = None

    def start(self):
        """
        Amaç: Monitoring'i başlatır
        Döner: Başarı durumu (True/False)
        """
        if self.running:
            return False
        
        # Database bağlantı kontrolü
        connection_result = database.check_database_connection(self.db_path)
        if not connection_result.success:
            return False
        
        self.running = True
        self.thread = threading.Thread(target=self.execution_loop, daemon=True)
        self.thread.start()
        return True

    def stop(self):
        """
        Amaç: Monitoring'i durdurur
        Döner: Yok
        """
        if not self.running:
            return
        
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)

    def is_running(self):
        """
        Amaç: Servis durumunu kontrol eder
        Döner: Çalışma durumu (True/False)
        """
        return self.running and self.thread and self.thread.is_alive()

    def get_ready_tasks(self, limit=10):
        """
        Amaç: Hazır olan taskları alır (database function kullanır)
        Döner: Ready task listesi
        """
        result = database.get_ready_tasks_for_execution(
            db_path=self.db_path,
            execution_id=None,
            limit=limit
        )
        
        if result.success:
            return result.data.get('ready_tasks', [])
        return []

    def reorder_queue(self):
        """
        Amaç: Queue'yu yeniden düzenler (database function kullanır)
        Döner: Güncellenen task sayısı
        """
        result = database.reorder_execution_queue(self.db_path)
        
        if result.success:
            return result.data.get('ready_count', 0)
        return 0

    def execution_loop(self):
        """
        Amaç: Ana monitoring döngüsü
        Döner: Yok (sonsuz döngü)
        """
        while self.running:
            try:
                # Queue'yu düzenle
                self.reorder_queue()
                
                # Ready taskları al
                ready_tasks = self.get_ready_tasks(limit=10)
                
                # Her task'ı işle
                for task in ready_tasks:
                    if not self.running:
                        break
                    
                    # Task'ı running olarak işaretle
                    database.mark_task_as_running(self.db_path, task['id'])
                    
                    # Task'ı işle
                    self.process_task(task)
                
                # Polling interval bekle
                time.sleep(self.polling_interval)
                
            except Exception:
                time.sleep(1)

    def process_task(self, task):
        """
        Amaç: Tek bir task'ı işler
        Döner: İşlem başarı durumu (True/False)
        """
        try:
            task_id = task['id']
            node_id = task['node_id']
            execution_id = task['execution_id']
            
            # Node bilgilerini al
            node_result = database.get_node(self.db_path, node_id)
            if not node_result.success:
                return False
            
            node_info = node_result.data
            
            # Context oluştur (updated context manager ile execution_results query)
            params_dict = database.safe_json_loads(node_info.get('params', '{}'))
            processed_context = context_manager.create_context_for_task(
                params_dict, execution_id, self.db_path
            )
            
            # Task payload hazırla
            task_payload = {
                "execution_id": execution_id,
                "workflow_id": node_info['workflow_id'],
                "node_id": node_id,
                "script_path": node_info.get('script', ''),
                "context": processed_context,
                "node_name": node_info['name'],
                "node_type": node_info['type']
            }
            
            # TODO: Send to input queue (later implementation)
            
            # Task'ı queue'dan sil
            delete_result = database.delete_task(self.db_path, task_id)
            return delete_result.success
            
        except Exception:
            return False
        
    def send_to_input_queue(self, task_payload):
        """
        Amaç: Task'ı input queue'ya gönderir
        Döner: Yok
        """
        pass    