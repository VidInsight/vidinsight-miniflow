import time
import threading

from .. import database
from ..database.functions.workflow_orchestration import process_execution_result


class ResultMonitor:
    """
    Amaç: Execution sonuçlarını alır ve workflow orchestration'a besler
    """

    def __init__(self, db_path_or_url, polling_interval=5, manager=None):
        self.db_path_or_url = db_path_or_url
        self.polling_interval = polling_interval
        self.running = False
        self.thread = None
        self.manager = manager

    def start(self):
        """
        Result monitoring'i başlatır
        """
        if self.running:
            return False

        connection_result = database.check_database_connection(self.db_path_or_url)
        if not connection_result.success:
            return False

        self.running = True
        self.thread = threading.Thread(target=self.execution_loop, daemon=True)
        self.thread.start()
        print("[ResultMonitor] Başlatıldı.")
        return True

    def stop(self):
        """
        Result monitoring'i durdurur
        """
        if not self.running:
            return

        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        print("[ResultMonitor] Durduruldu.")

    def is_running(self):
        """
        Servis durumunu kontrol eder
        """
        return self.running and self.thread and self.thread.is_alive()

    def execution_loop(self):
        """
        Ana döngü: output queue'dan sonuçları alır ve işler
        """
        print("[ResultMonitor] execution_loop başladı.")
        while self.running:
            try:
                result = self.get_from_output_queue()
                if result is not None:
                    self.process_result(result)
                time.sleep(self.polling_interval)
            except Exception as e:
                print(f"[ResultMonitor] execution_loop hata: {e}")
                time.sleep(1)

    def get_from_output_queue(self):
        """
        Output queue'dan tamamlanan task sonucunu alır
        """
        if not self.manager:
            return None
        result = self.manager.get_output_item()
        if result is not None:
            print(f"[ResultMonitor] Yeni result alındı: {result}")
        return result

    def process_result(self, result):
        """
        Gelen sonucu işleyip workflow orchestration'a iletir
        """
        try:
            if result is None:
                return False

            required_fields = ['execution_id', 'node_id', 'status']
            for field in required_fields:
                if field not in result:
                    print(f"[ResultMonitor] Eksik alan: {field}")
                    return False

            if result['status'] not in ['success', 'failed']:
                print(f"[ResultMonitor] Geçersiz status: {result['status']}")
                return False

            orchestration_result = process_execution_result(
                db_path_or_url=self.db_path_or_url,
                execution_id=result["execution_id"],
                node_id=result["node_id"],
                status=result["status"],
                result_data=result.get("result_data"),
                error_message=result.get("error_message")
            )
            print(f"[ResultMonitor] process_execution_result sonucu: {orchestration_result}")
            return orchestration_result.success

        except Exception as e:
            print(f"[ResultMonitor] process_result hata: {e}")
            return False

    def process_results(self, results):
        """
        Birden fazla sonucu sırasıyla işler
        """
        processed_count = 0
        for result in results:
            if not self.running:
                break
            if self.process_result(result):
                processed_count += 1
        return processed_count

    def validate_result_format(self, result):
        """
        Gelen sonucun formatını kontrol eder
        """
        if not isinstance(result, dict):
            return False

        required_fields = ['execution_id', 'node_id', 'status']
        for field in required_fields:
            if field not in result or not isinstance(result[field], str):
                return False

        if result['status'] not in ['success', 'failed']:
            return False

        if result['status'] == 'success' and 'result_data' not in result:
            return False
        if result['status'] == 'failed' and 'error_message' not in result:
            return False

        return True

    def simulate_result_processing(self, test_result):
        """
        Test için manuel result işleme
        """
        if not self.validate_result_format(test_result):
            return {"success": False, "error": "Invalid result format"}

        processed = self.process_result(test_result)

        return {
            "success": processed,
            "result": test_result,
            "processed_at": database.generate_timestamp()
        }
