import time
import threading
import os
import json

from .. import database
from ..database.utils import safe_json_loads
from . import context_manager
from ..database.functions.workflow_orchestration import get_ready_tasks_for_execution, mark_task_as_running


class QueueMonitor:
    """
    Amaç: Execution queue'yu izler ve hazır taskları işler
    """

    def __init__(self, db_path, polling_interval=5, manager=None):
        self.db_path = db_path
        self.polling_interval = polling_interval
        self.running = False
        self.thread = None
        self.manager = manager
        self.last_ready_count = None
        self.last_total_ready = None

        current_dir = os.path.dirname(os.path.abspath(__file__))
        miniflow_dir = os.path.dirname(current_dir)
        project_root = os.path.dirname(miniflow_dir)
        self.scripts_dir = os.path.join(project_root, 'scripts')
        print(f"[QueueMonitor] scripts_dir: {self.scripts_dir}")

    def start(self):
        if self.running:
            return False

        if not database.check_database_connection(self.db_path).success:
            return False

        self.running = True
        self.thread = threading.Thread(target=self.execution_loop, daemon=True)
        self.thread.start()
        print("[QueueMonitor] Başlatıldı.")
        return True

    def stop(self):
        if not self.running:
            return

        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        print("[QueueMonitor] Durduruldu.")

    def is_running(self):
        return self.running and self.thread and self.thread.is_alive()

    def reorder_queue(self):
        result = database.reorder_execution_queue(self.db_path)
        if result.success:
            ready_count = result.data.get("ready_count", 0)
            if ready_count != self.last_ready_count and ready_count > 0:
                print(f"[QueueMonitor] Queue reorder: {ready_count} task ready oldu.")
            self.last_ready_count = ready_count
            return ready_count
        return 0

    def get_ready_tasks(self, limit=10):
        all_ready_tasks = []
        try:
            executions_result = database.list_executions(self.db_path)
            if not executions_result.success:
                return []

            active_executions = [
                e for e in executions_result.data if e.get('status') in ['running', 'pending']
            ]

            for execution in active_executions:
                execution_id = execution['id']
                ready_result = get_ready_tasks_for_execution(
                    self.db_path, execution_id=execution_id, limit=limit
                )
                if ready_result.success:
                    all_ready_tasks.extend(ready_result.data)

            if limit and len(all_ready_tasks) > limit:
                all_ready_tasks = all_ready_tasks[:limit]

            if len(all_ready_tasks) != self.last_total_ready and len(all_ready_tasks) > 0:
                print(f"[QueueMonitor] Ready task sayısı: {len(all_ready_tasks)}")

            self.last_total_ready = len(all_ready_tasks)
            return all_ready_tasks

        except Exception as e:
            print(f"[QueueMonitor] get_ready_tasks hata: {e}")
            return []

    def execution_loop(self):
        print("[QueueMonitor] execution_loop başladı.")
        while self.running:
            try:
                self.reorder_queue()
                ready_tasks = self.get_ready_tasks(limit=10)

                for task in ready_tasks:
                    if not self.running:
                        break

                    print(f"[QueueMonitor] Task işleniyor: {task}")
                    mark_task_as_running(self.db_path, task['id'])
                    self.process_task(task)

                time.sleep(self.polling_interval)

            except Exception as e:
                print(f"[QueueMonitor] execution_loop hata: {e}")
                time.sleep(1)

    def process_task(self, task):
        print(f"[QueueMonitor] process_task çağrıldı: {task}")
        try:
            task_id = task['id']
            node_id = task['node_id']
            execution_id = task['execution_id']

            node_result = database.get_node(self.db_path, node_id)
            if not node_result.success:
                print(f"[QueueMonitor] Node alınamadı: {node_id}")
                return False

            node_info = node_result.data

            params_dict = safe_json_loads(node_info.get('params', '{}'))
            print("--------------------------------")
            print(f"[QueueMonitor] Raw params: {params_dict}")

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
            send_success = self.send_to_input_queue(task_payload)

            if send_success:
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
        try:
            print(f"[QueueMonitor] send_to_input_queue çağrıldı: {task_payload}")
            self.manager.put_item(task_payload)
            print(f"[QueueMonitor] put_item başarılı.")
            return True

        except Exception as e:
            print(f"[QueueMonitor] send_to_input_queue hata: {e}")
            return False
