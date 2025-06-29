import time
import threading

# NEW: Database Manager Integration (temporarily disabled)
# Legacy support  
from .. import database
from .input_monitor import MiniflowInputMonitor
from .output_monitor import MiniflowOutputMonitor
from ..parallelism_engine import Manager


class WorkflowScheduler:
    """
    Amaç: QueueMonitor ve ResultMonitor'u koordine eder ve yönetir
    """
    
    def __init__(self, db_path, queue_polling_interval=5, result_polling_interval=5, batch_size=20):
        """
        Amaç: Scheduler'ı başlatır (Parallel processing destekli)
        Döner: Yok (constructor)
        """
        self.db_path = db_path
        self.queue_polling_interval = queue_polling_interval
        self.result_polling_interval = result_polling_interval
        self.batch_size = batch_size

        # NEW: Database Manager Integration (temporarily disabled)
        self.db_manager = None

        self.manager = Manager()

        # ------------------------------------------------------------
        # Input Monitor'u başlatır
        # ------------------------------------------------------------
        self.queue_monitor = MiniflowInputMonitor(
            db_path=db_path, 
            polling_interval=queue_polling_interval, 
            manager=self.manager, 
            batch_size=batch_size, 
            worker_threads=4
        )

        # ------------------------------------------------------------
        # Output Monitor'u başlatır
        # ------------------------------------------------------------
        self.result_monitor = MiniflowOutputMonitor(
            db_path=db_path, 
            polling_interval=result_polling_interval, 
            manager=self.manager, 
            batch_size=25, 
            worker_threads=4
        )
        
        # Scheduler durumu
        self.running = False
        self.health_check_thread = None
        self.health_check_interval = 10  # saniye
        
        # Auto-recovery ayarları
        self.auto_recovery_enabled = True
        self.max_restart_attempts = 3

    def start(self):
        """
        Amaç: Scheduler'ı ve tüm monitor'ları başlatır
        Döner: Başarı durumu (True/False)
        """
        if self.running:
            return False
        
        # Database bağlantı kontrolü - Legacy only for now
        connection_result = database.check_database_connection(self.db_path)
        if not connection_result.success:
            print("❌ Scheduler: Database bağlantı hatası")
            return False
        
        try:
            # CRITICAL FIX: Start manager FIRST before monitors
            self.manager.start()
            
            # Sequential startup - Queue monitor önce başlar
            queue_started = self.queue_monitor.start()
            if not queue_started:
                self.manager.shutdown()  # Clean shutdown
                return False
            
            # Result monitor sonra başlar
            result_started = self.result_monitor.start()
            if not result_started:
                self.queue_monitor.stop()  # Rollback
                self.manager.shutdown()    # Clean shutdown
                return False
            
            # Scheduler durumunu güncelle
            self.running = True
            
            # Health monitoring başlat
            self.start_health_monitoring()
            
            return True
            
        except Exception:
            self.stop()  # Cleanup on error
            return False

    def stop(self):
        """
        Amaç: Scheduler'ı ve tüm monitor'ları durdurur
        Döner: Yok
        """
        if not self.running:
            return
        
        self.running = False
        
        # Health monitoring'i durdur
        self.stop_health_monitoring()

        self.manager.shutdown()

        # Sequential shutdown - Result monitor önce durur
        try:
            self.result_monitor.stop()
        except Exception:
            pass
        
        # Queue monitor sonra durur
        try:
            self.queue_monitor.stop()
        except Exception:
            pass

    def is_running(self):
        """
        Amaç: Scheduler durumunu kontrol eder
        Döner: Çalışma durumu (True/False)
        """
        return (self.running and 
                self.queue_monitor.is_running() and 
                self.result_monitor.is_running()
        )



def create_scheduler(db_path, queue_interval=0.1, result_interval=0.5, batch_size=50):
    """
    Amaç: Factory function - Scheduler oluşturur (Parallel processing optimized)
    Döner: WorkflowScheduler instance'ı
    
    Performance Changes:
    - queue_interval: 5s -> 0.1s (50x faster polling)
    - result_interval: 5s -> 0.5s (10x faster result processing)
    - batch_size: 20 -> 50 (2.5x larger batches)
    - Parallel processing enabled with worker threads
    """
    return WorkflowScheduler(db_path, queue_interval, result_interval, batch_size)