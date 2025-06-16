import time
import threading

from .. import database
from .queue_monitoring import QueueMonitor
from .result_monitoring import ResultMonitor
from ..parallelism_engine import Manager


class WorkflowScheduler:
    """
    Amaç: QueueMonitor ve ResultMonitor'u koordine eder ve yönetir
    """
    
    def __init__(self, db_path, queue_polling_interval=5, result_polling_interval=5):
        """
        Amaç: Scheduler'ı başlatır
        Döner: Yok (constructor)
        """
        self.db_path = db_path
        self.queue_polling_interval = queue_polling_interval
        self.result_polling_interval = result_polling_interval

        self.manager = Manager()

        # Monitor nesneleri
        self.queue_monitor = QueueMonitor(db_path, queue_polling_interval, self.manager)
        self.result_monitor = ResultMonitor(db_path, result_polling_interval, self.manager)
        
        # Scheduler durumu
        self.running = False
        self.health_check_thread = None
        self.health_check_interval = 10  # saniye
        
        # Auto-recovery ayarları
        self.auto_recovery_enabled = True
        self.max_restart_attempts = 3
        self.restart_delay = 5  # saniye

    def start(self):
        """
        Amaç: Scheduler'ı ve tüm monitor'ları başlatır
        Döner: Başarı durumu (True/False)
        """
        if self.running:
            return False
        
        # Database bağlantı kontrolü
        connection_result = database.check_database_connection(self.db_path)
        if not connection_result.success:
            return False
        
        try:
            # Sequential startup - Queue monitor önce başlar
            queue_started = self.queue_monitor.start()
            if not queue_started:
                return False
            
            # Result monitor sonra başlar
            result_started = self.result_monitor.start()
            if not result_started:
                self.queue_monitor.stop()  # Rollback
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
                self.result_monitor.is_running())

    def get_status(self):
        """
        Amaç: Detaylı sistem durumu bilgisi verir
        Döner: Status dictionary'si
        """
        return {
            "scheduler_running": self.running,
            "queue_monitor_running": self.queue_monitor.is_running(),
            "result_monitor_running": self.result_monitor.is_running(),
            "health_monitoring_active": self.health_check_thread and self.health_check_thread.is_alive(),
            "auto_recovery_enabled": self.auto_recovery_enabled,
            "database_path": self.db_path,
            "queue_polling_interval": self.queue_polling_interval,
            "result_polling_interval": self.result_polling_interval
        }

    def restart(self):
        """
        Amaç: Scheduler'ı yeniden başlatır
        Döner: Başarı durumu (True/False)
        """
        self.stop()
        time.sleep(self.restart_delay)
        return self.start()

    def start_health_monitoring(self):
        """
        Amaç: Health monitoring thread'ini başlatır
        Döner: Yok
        """
        if self.health_check_thread and self.health_check_thread.is_alive():
            return
        
        self.health_check_thread = threading.Thread(
            target=self.health_check_loop, 
            daemon=True
        )
        self.health_check_thread.start()

    def stop_health_monitoring(self):
        """
        Amaç: Health monitoring thread'ini durdurur
        Döner: Yok
        """
        if self.health_check_thread and self.health_check_thread.is_alive():
            self.health_check_thread.join(timeout=5)

    def health_check_loop(self):
        """
        Amaç: Periyodik health check döngüsü
        Döner: Yok (sonsuz döngü)
        """
        restart_attempts = 0
        
        while self.running:
            try:
                # Health check yap
                if not self.check_health():
                    if self.auto_recovery_enabled and restart_attempts < self.max_restart_attempts:
                        restart_attempts += 1
                        self.attempt_recovery()
                    else:
                        # Max restart attempts aşıldı, scheduler'ı durdur
                        self.running = False
                        break
                else:
                    # Health check başarılı, restart counter'ı sıfırla
                    restart_attempts = 0
                
                # Health check interval bekle
                time.sleep(self.health_check_interval)
                
            except Exception:
                time.sleep(1)

    def check_health(self):
        """
        Amaç: Monitor'ların sağlık durumunu kontrol eder
        Döner: Sağlık durumu (True/False)
        """
        try:
            # Database bağlantısını kontrol et
            db_check = database.check_database_connection(self.db_path)
            if not db_check.success:
                return False
            
            # Queue monitor kontrolü
            if not self.queue_monitor.is_running():
                return False
            
            # Result monitor kontrolü
            if not self.result_monitor.is_running():
                return False
            
            return True
            
        except Exception:
            return False

    def attempt_recovery(self):
        """
        Amaç: Başarısız monitor'ları yeniden başlatmaya çalışır
        Döner: Recovery başarı durumu (True/False)
        """
        try:
            # Queue monitor recovery
            if not self.queue_monitor.is_running():
                self.queue_monitor.stop()
                time.sleep(1)
                if not self.queue_monitor.start():
                    return False
            
            # Result monitor recovery
            if not self.result_monitor.is_running():
                self.result_monitor.stop()
                time.sleep(1)
                if not self.result_monitor.start():
                    return False
            
            return True
            
        except Exception:
            return False

    def update_configuration(self, queue_interval=None, result_interval=None, 
                           health_interval=None, auto_recovery=None):
        """
        Amaç: Runtime configuration güncellemesi
        Döner: Güncelleme başarı durumu (True/False)
        """
        try:
            restart_needed = False
            
            # Polling interval güncellemeleri
            if queue_interval and queue_interval != self.queue_polling_interval:
                self.queue_polling_interval = queue_interval
                restart_needed = True
            
            if result_interval and result_interval != self.result_polling_interval:
                self.result_polling_interval = result_interval
                restart_needed = True
            
            # Health monitoring ayarları
            if health_interval:
                self.health_check_interval = health_interval
            
            if auto_recovery is not None:
                self.auto_recovery_enabled = auto_recovery
            
            # Gerekirse restart
            if restart_needed and self.running:
                return self.restart()
            
            return True
            
        except Exception:
            return False

    def get_statistics(self):
        """
        Amaç: İstatistik bilgileri toplar
        Döner: İstatistik dictionary'si
        """
        stats = {
            "uptime_seconds": 0,
            "total_processed_tasks": 0,
            "total_processed_results": 0,
            "current_queue_size": 0,
            "failed_tasks": 0
        }
        
        try:
            # Database'den aktif execution queue boyutunu al
            queue_result = database.count_tasks(self.db_path, status='queued')
            if queue_result.success:
                stats["current_queue_size"] = queue_result.data.get('count', 0)
            
            # Diğer istatistikler için database sorguları
            # (Bu kısım gerektiğinde genişletilebilir)
            
        except Exception:
            pass
        
        return stats


def create_scheduler(db_path, queue_interval=5, result_interval=5):
    """
    Amaç: Factory function - Scheduler oluşturur
    Döner: WorkflowScheduler instance'ı
    """
    return WorkflowScheduler(db_path, queue_interval, result_interval)


def main():
    """
    Amaç: CLI test fonksiyonu
    Döner: Yok
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Workflow Scheduler')
    parser.add_argument('--db-path', required=True, help='Database path')
    parser.add_argument('--queue-interval', type=int, default=5, help='Queue polling interval')
    parser.add_argument('--result-interval', type=int, default=5, help='Result polling interval')
    
    args = parser.parse_args()
    
    # Scheduler oluştur ve başlat
    scheduler = create_scheduler(
        db_path=args.db_path,
        queue_interval=args.queue_interval,
        result_interval=args.result_interval
    )
    
    if scheduler.start():
        print(f"Scheduler started successfully!")
        print(f"Database: {args.db_path}")
        print(f"Queue interval: {args.queue_interval}s")
        print(f"Result interval: {args.result_interval}s")
        
        try:
            # Süresiz çalıştır
            while scheduler.is_running():
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutdown requested...")
            scheduler.stop()
            print("Scheduler stopped.")
    else:
        print("Failed to start scheduler!")


if __name__ == "__main__":
    main()
