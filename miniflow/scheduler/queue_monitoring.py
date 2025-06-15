import time
import threading
import os

from .. import database
from . import context_manager


class QueueMonitor:
    """
    Amaç: Execution queue'yu izler ve hazır taskları işler
    """

    def __init__(self, db_path, polling_interval=5, manager=None):
        """
        Amaç: Queue monitor'u başlatır
        Döner: Yok (constructor)
        """
        self.db_path = db_path
        self.polling_interval = polling_interval
        self.running = False
        self.thread = None
        self.scripts_dir = os.path.join(os.path.dirname(os.path.dirname(os.getcwd())), 'scripts')

        self.manager = manager

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
        Amaç: Tüm active execution'lar için hazır olan taskları alır
        Döner: Ready task listesi
        """
        all_ready_tasks = []

        try:
            # Tüm active execution'ları al
            executions_result = database.list_executions(self.db_path)
            if not executions_result.success:
                return []

            active_executions = [
                exec_data for exec_data in executions_result.data
                if exec_data.get('status') in ['running', 'pending']
            ]

            # Her active execution için ready task'ları al
            for execution in active_executions:
                execution_id = execution['id']

                ready_result = database.get_ready_tasks_for_execution(
                    db_path=self.db_path,
                    execution_id=execution_id,
                    limit=limit
                )

                if ready_result.success:
                    ready_tasks = ready_result.data.get('ready_tasks', [])
                    all_ready_tasks.extend(ready_tasks)

            # Limit uygula
            if limit and len(all_ready_tasks) > limit:
                all_ready_tasks = all_ready_tasks[:limit]

            return all_ready_tasks

        except Exception:
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
                "script_path": os.path.join(self.scripts_dir, node_info.get('script', '')),
                "context": processed_context,
                "node_name": node_info['name'],
                "node_type": node_info['type']
            }

            # Task'ı input queue'ya gönder
            send_success = self.send_to_input_queue(task_payload)

            if send_success:
                # Sadece başarılı gönderimden sonra sil
                delete_result = database.delete_task(self.db_path, task_id)
                return delete_result.success
            else:
                return False

        except Exception:
            return False

    def send_to_input_queue(self, task_payload):
        """
        Amaç: Task'ı input queue'ya gönderir
        Döner: Başarı durumu (True/False)
        
        Bu implementasyon test amaçlı simulated execution yapar.
        Gerçek sistemde burası execution engine'e gönderecek.
        """
        try:
            # Simulated execution result oluştur
            self.manager.put_item(task_payload)
            return True

        except Exception:
            return False
