import time
import threading
import os
import json

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
        current_dir = os.path.dirname(os.path.abspath(__file__))  # miniflow/scheduler
        miniflow_dir = os.path.dirname(current_dir)  # miniflow
        project_root = os.path.dirname(miniflow_dir)  # vi-miniflow (proje kök)
        self.scripts_dir = os.path.join(project_root, 'scripts')
        print(f"[QueueMonitor] scripts_dir: {self.scripts_dir}")


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
        print("[QueueMonitor] Başlatıldı.")
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
        print("[QueueMonitor] Durduruldu.")

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

            print(f"[QueueMonitor] Ready task sayısı: {len(all_ready_tasks)}")
            return all_ready_tasks

        except Exception as e:
            print(f"[QueueMonitor] get_ready_tasks hata: {e}")
            return []

    def reorder_queue(self):
        """
        Amaç: Queue'yu yeniden düzenler (database function kullanır)
        Döner: Güncellenen task sayısı
        """
        result = database.reorder_execution_queue(self.db_path)

        if result.success:
            print(f"[QueueMonitor] Queue reorder: {result.data.get('ready_count', 0)} task ready oldu.")
            return result.data.get('ready_count', 0)
        return 0

    def execution_loop(self):
        """
        Amaç: Ana monitoring döngüsü
        Döner: Yok (sonsuz döngü)
        """
        print("[QueueMonitor] execution_loop başladı.")
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

                    print(f"[QueueMonitor] Task işleniyor: {task}")
                    # Task'ı running olarak işaretle
                    database.mark_task_as_running(self.db_path, task['id'])

                    # Task'ı işle
                    self.process_task(task)

                # Polling interval bekle
                time.sleep(self.polling_interval)

            except Exception as e:
                print(f"[QueueMonitor] execution_loop hata: {e}")
                time.sleep(1)

    def process_task(self, task):
        """
        Amaç: Tek bir task'ı işler
        Döner: İşlem başarı durumu (True/False)
        """
        print(f"[QueueMonitor] process_task çağrıldı: {task}")
        try:
            task_id = task['id']
            node_id = task['node_id']
            execution_id = task['execution_id']

            # Node bilgilerini al
            node_result = database.get_node(self.db_path, node_id)
            if not node_result.success:
                print(f"[QueueMonitor] Node alınamadı: {node_id}")
                return False

            node_info = node_result.data

            # Context oluştur (updated context manager ile execution_results query)
            params_dict = database.safe_json_loads(node_info.get('params', '{}'))
            print("--------------------------------")
            print(f"[QueueMonitor] Raw params: {params_dict}")
            
            # Handle double-encoded JSON
            if isinstance(params_dict, str):
                try:
                    params_dict = json.loads(params_dict)
                except json.JSONDecodeError as e:
                    print(f"[QueueMonitor] Failed to parse params JSON: {e}")
                    return False
            
            print(f"[QueueMonitor] Parsed params: {params_dict}")
            for key, value in params_dict.items():
                print(f"[QueueMonitor] {key}: {value}")
                print(f"[QueueMonitor] {type(key)}: {type(value)}")
            print("--------------------------------")

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

            print(f"[QueueMonitor] Task payload input queue'ya gönderiliyor: {task_payload}")
            # Task'ı input queue'ya gönder
            send_success = self.send_to_input_queue(task_payload)

            if send_success:
                # Sadece başarılı gönderimden sonra sil
                delete_result = database.delete_task(self.db_path, task_id)
                print(f"[QueueMonitor] Task input queue'ya gönderildi ve silindi: {task_id}")
                return delete_result.success
            else:
                print(f"[QueueMonitor] Task input queue'ya gönderilemedi: {task_id}")
                return False

        except Exception as e:
            print(f"[QueueMonitor] process_task hata: {e}")
            return False

    def send_to_input_queue(self, task_payload):
        """
        Amaç: Task'ı input queue'ya gönderir
        Döner: Başarı durumu (True/False)
        
        Bu implementasyon test amaçlı simulated execution yapar.
        Gerçek sistemde burası execution engine'e gönderecek.
        """
        try:
            print(f"[QueueMonitor] send_to_input_queue çağrıldı: {task_payload}")
            self.manager.put_item(task_payload)
            print(f"[QueueMonitor] put_item başarılı.")
            return True

        except Exception as e:
            print(f"[QueueMonitor] send_to_input_queue hata: {e}")
            return False
