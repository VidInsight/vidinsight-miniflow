import time
import threading

from .. import database
from ..database.functions.workflow_orchestration import process_execution_result
from ..utils.logger import logger, log_performance

# Webhook functionality removed (API module deleted)
WEBHOOK_AVAILABLE = False


class ResultMonitor:
    """
    Amaç: Execution sonuçlarını alır ve workflow orchestration'a besler
    """
    
    def __init__(self, db_path, polling_interval=5, manager=None):
        """
        Amaç: Result monitor'u başlatır
        Döner: Yok (constructor)
        """
        self.db_path = db_path
        self.polling_interval = polling_interval
        self.running = False
        self.thread = None
        self.manager = manager

    def start(self):
        """
        Amaç: Result monitoring'i başlatır
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
        logger.info("ResultMonitor started")
        return True

    def stop(self):
        """
        Amaç: Result monitoring'i durdurur
        Döner: Yok
        """
        if not self.running:
            return
        
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        logger.info("ResultMonitor stopped")

    def is_running(self):
        """
        Amaç: Servis durumunu kontrol eder
        Döner: Çalışma durumu (True/False)
        """
        return self.running and self.thread and self.thread.is_alive()

    def execution_loop(self):
        """
        Amaç: Ana result monitoring döngüsü
        Döner: Yok (sonsuz döngü)
        """
        #print("[ResultMonitor] execution_loop başladı.")
        while self.running:
            try:
                # Output queue'dan sonuçları al
                result = self.get_from_output_queue()
                #print(f"[ResultMonitor] Output queue'dan alınan result: {result}")
                    
                # Sonucu workflow orchestration'a besle
                self.process_result(result)
                
                # Polling interval bekle
                time.sleep(self.polling_interval)
                
            except Exception as e:
                #print(f"[ResultMonitor] execution_loop hata: {e}")
                time.sleep(1)

    def get_from_output_queue(self):
        """
        Amaç: Output queue'dan tamamlanan task sonuçlarını alır
        Döner: Sonuç listesi
        
        TODO: Bu fonksiyon gerçek output queue implementasyonu ile değiştirilecek
        Şu anda boş liste döner (placeholder)
        """
        # Placeholder implementation
        result = self.manager.get_output_item()
        #print(f"[ResultMonitor] get_output_item çağrıldı: {result}")
        # Gerçek implementasyonda burası output queue'yu okuyacak
        return result

    def process_result(self, result):
        """
        Amaç: Tek sonucu workflow orchestration'a besler ve dependency güncellemelerini tetikler
        Döner: İşlem başarı durumu (True/False)
        
        workflow_orchestration.process_execution_result() kullanarak:
        - Execution results tablosuna kayıt ekler
        - Başarı durumunda bağımlılıkları günceller
        - Hata durumunda workflow'u sonlandırır
        - Tamamlanma kontrolü yapar
        - Webhook bildirim gönderir (eğer workflow tamamlandıysa)
        """
        #print(f"[ResultMonitor] process_result çağrıldı: {result}")
        try:
            # None check first
            if result is None:
                print(f"[ResultMonitor] Result None, atlanıyor")
                return True  # Bu normal bir durum, hata değil
            
            # Result format validation
            if not isinstance(result, dict):
                print(f"[ResultMonitor] Result dict değil: {type(result)}")
                return False
                
            required_fields = ['execution_id', 'node_id', 'status']
            for field in required_fields:
                if field not in result:
                    #print(f"[ResultMonitor] Eksik alan: {field}")
                    return False
            
            # Status validation
            if result['status'] not in ['success', 'failed']:
                #print(f"[ResultMonitor] Geçersiz status: {result['status']}")
                return False
            
            # Workflow orchestration'a besle
            #print(f"[ResultMonitor] process_execution_result çağrılıyor...")
            orchestration_result = process_execution_result(
                db_path=self.db_path,
                execution_id=result["execution_id"],
                node_id=result["node_id"],
                status=result["status"],
                result_data=result.get("result_data"),
                error_message=result.get("error_message")
            )
            #print(f"[ResultMonitor] process_execution_result sonucu: {orchestration_result}")
            
            # Check if workflow execution is complete and send webhook
            if orchestration_result.success:
                self._check_and_send_webhook(result["execution_id"])
            
            return orchestration_result.success
            
        except Exception as e:
            #print(f"[ResultMonitor] process_result hata: {e}")
            return False

    def _check_and_send_webhook(self, execution_id: str):
        """
        Check if workflow execution is complete and send webhook notification
        """
        try:
            if not WEBHOOK_AVAILABLE:
                return
            
            # Get execution status
            execution_result = database.get_execution(self.db_path, execution_id)
            if not execution_result.success:
                return
            
            execution = execution_result.data
            if not execution:
                return
            
            # Only send webhook if execution is completed or failed
            if execution["status"] not in ["completed", "failed"]:
                return
            
            # Get workflow information
            workflow_result = database.get_workflow(self.db_path, execution["workflow_id"])
            if not workflow_result.success:
                return
            
            workflow = workflow_result.data
            if not workflow:
                return
            
            # Get execution results for webhook payload
            from ..database.functions.workflow_orchestration import get_execution_status_summary
            summary_result = get_execution_status_summary(self.db_path, execution_id)
            
            results = {}
            error_message = None
            
            if summary_result.success:
                results = summary_result.data.get("node_results", {})
                if execution["status"] == "failed":
                    # Try to get error message from failed tasks
                    failed_results = {k: v for k, v in results.items() if v.get("status") == "failed"}
                    if failed_results:
                        first_failed = list(failed_results.values())[0]
                        error_message = first_failed.get("error_message", "Workflow execution failed")
            
            # Webhook functionality removed (API module deleted)
            print(f"[ResultMonitor] Execution completed (webhook disabled): {execution_id}")
            
        except Exception as e:
            print(f"[ResultMonitor] Webhook error for execution {execution_id}: {e}")

    def process_results(self, results):
        """
        Amaç: Birden fazla sonucu batch olarak işler
        Döner: İşlenen sonuç sayısı
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
        Amaç: Sonuç formatının doğru olup olmadığını kontrol eder
        Döner: Validation durumu (True/False)
        
        Beklenen format:
        {
            "execution_id": str,
            "node_id": str,
            "status": "success" | "failed",
            "result_data": Dict (success için),
            "error_message": str (failed için)
        }
        """
        if not isinstance(result, dict):
            return False
        
        # Required fields
        required_fields = ['execution_id', 'node_id', 'status']
        for field in required_fields:
            if field not in result:
                return False
            if not isinstance(result[field], str):
                return False
        
        # Status validation
        if result['status'] not in ['success', 'failed']:
            return False
        
        # Success durumunda result_data olmalı
        if result['status'] == 'success':
            if 'result_data' not in result:
                return False
        
        # Failed durumunda error_message olmalı
        if result['status'] == 'failed':
            if 'error_message' not in result:
                return False
        
        return True

    def simulate_result_processing(self, test_result):
        """
        Amaç: Test ve debugging için sonuç işleme simülasyonu
        Döner: İşlem sonucu ve detaylar
        
        Bu fonksiyon test amaçlı kullanılır
        """
        if not self.validate_result_format(test_result):
            return {"success": False, "error": "Invalid result format"}
        
        # Process simulation
        processed = self.process_result(test_result)
        
        return {
            "success": processed,
            "result": test_result,
            "processed_at": database.generate_timestamp()
        }