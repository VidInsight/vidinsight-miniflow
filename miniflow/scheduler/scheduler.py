import time
import threading

# Logger setup
import logging
logger = logging.getLogger("miniflow.scheduler")

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
        self.restart_delay = 5  # saniye

    def start(self):
        """
        Amaç: Scheduler'ı ve tüm monitor'ları başlatır
        Döner: Başarı durumu (True/False)
        """
        logger.info("Scheduler başlatılıyor")
        
        if self.running:
            logger.warning("Scheduler zaten çalışıyor")
            return False
        
        # Database bağlantı kontrolü
        logger.debug("Database bağlantısı kontrol ediliyor")
        connection_result = database.check_database_connection(self.db_path)
        if not connection_result.success:
            logger.error(f"Database bağlantı hatası: {connection_result.error}")
            return False
        
        try:
            # CRITICAL FIX: Start manager FIRST before monitors
            logger.debug("Parallelism engine manager başlatılıyor")
            self.manager.start()
            
            # Sequential startup - Queue monitor önce başlar
            logger.info("Input monitor başlatılıyor")
            queue_started = self.queue_monitor.start()
            if not queue_started:
                logger.error("Input monitor başlatılamadı")
                self.manager.shutdown()  # Clean shutdown
                return False
            
            # Result monitor sonra başlar
            logger.info("Output monitor başlatılıyor")
            result_started = self.result_monitor.start()
            if not result_started:
                logger.error("Output monitor başlatılamadı - rollback yapılıyor")
                self.queue_monitor.stop()  # Rollback
                self.manager.shutdown()    # Clean shutdown
                return False
            
            # Scheduler durumunu güncelle
            self.running = True
            
            # Health monitoring başlat
            logger.debug("Health monitoring başlatılıyor")
            self.start_health_monitoring()
            
            logger.info("Scheduler başarıyla başlatıldı")
            return True
            
        except Exception as e:
            logger.error(f"Scheduler başlatma hatası: {e}")
            self.stop()  # Cleanup on error
            return False

    def stop(self):
        """
        Amaç: Scheduler'ı ve tüm monitor'ları durdurur
        Döner: Yok
        """
        logger.info("Scheduler durduruluyor")
        
        if not self.running:
            logger.debug("Scheduler zaten durdurulmuş")
            return
        
        self.running = False
        
        # Health monitoring'i durdur
        logger.debug("Health monitoring durduruluyor")
        self.stop_health_monitoring()

        logger.debug("Parallelism engine manager kapatılıyor")
        self.manager.shutdown()

        # Sequential shutdown - Result monitor önce durur
        try:
            logger.debug("Output monitor durduruluyor")
            self.result_monitor.stop()
        except Exception as e:
            logger.warning(f"Output monitor durdurma hatası: {e}")
        
        # Queue monitor sonra durur
        try:
            logger.debug("Input monitor durduruluyor")
            self.queue_monitor.stop()
        except Exception as e:
            logger.warning(f"Input monitor durdurma hatası: {e}")
        
        logger.info("Scheduler başarıyla durduruldu")

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
        logger.debug("Health check döngüsü başlatıldı")
        restart_attempts = 0
        
        while self.running:
            try:
                # Health check yap
                if not self.check_health():
                    logger.warning(f"Health check başarısız - restart attempt: {restart_attempts + 1}/{self.max_restart_attempts}")
                    if self.auto_recovery_enabled and restart_attempts < self.max_restart_attempts:
                        restart_attempts += 1
                        logger.info("Auto-recovery başlatılıyor")
                        self.attempt_recovery()
                    else:
                        # Max restart attempts aşıldı, scheduler'ı durdur
                        logger.error("Max restart attempts aşıldı - scheduler durduruluyor")
                        self.running = False
                        break
                else:
                    # Health check başarılı, restart counter'ı sıfırla
                    if restart_attempts > 0:
                        logger.info("Health check başarılı - restart counter sıfırlandı")
                    restart_attempts = 0
                
                # Health check interval bekle
                time.sleep(self.health_check_interval)
                
            except Exception as e:
                logger.error(f"Health check döngüsü hatası: {e}")
                time.sleep(1)
        
        logger.debug("Health check döngüsü sonlandırıldı")

    def check_health(self):
        """
        Amaç: Monitor'ların sağlık durumunu kontrol eder
        Döner: Sağlık durumu (True/False)
        """
        try:
            # Database bağlantısını kontrol et
            db_check = database.check_database_connection(self.db_path)
            if not db_check.success:
                logger.warning("Health check - database bağlantı problemi")
                return False
            
            # Queue monitor kontrolü
            if not self.queue_monitor.is_running():
                logger.warning("Health check - input monitor çalışmıyor")
                return False
            
            # Result monitor kontrolü
            if not self.result_monitor.is_running():
                logger.warning("Health check - output monitor çalışmıyor")
                return False
            
            logger.debug("Health check başarılı - tüm bileşenler sağlıklı")
            return True
            
        except Exception as e:
            logger.error(f"Health check hatası: {e}")
            return False

    def attempt_recovery(self):
        """
        Amaç: Başarısız monitor'ları yeniden başlatmaya çalışır
        Döner: Recovery başarı durumu (True/False)
        """
        logger.info("Recovery işlemi başlatılıyor")
        
        try:
            # Queue monitor recovery
            if not self.queue_monitor.is_running():
                logger.info("Input monitor recovery başlatılıyor")
                self.queue_monitor.stop()
                time.sleep(1)
                if not self.queue_monitor.start():
                    logger.error("Input monitor recovery başarısız")
                    return False
                logger.info("Input monitor başarıyla recovery yapıldı")
            
            # Result monitor recovery
            if not self.result_monitor.is_running():
                logger.info("Output monitor recovery başlatılıyor")
                self.result_monitor.stop()
                time.sleep(1)
                if not self.result_monitor.start():
                    logger.error("Output monitor recovery başarısız")
                    return False
                logger.info("Output monitor başarıyla recovery yapıldı")
            
            logger.info("Recovery işlemi başarıyla tamamlandı")
            return True
            
        except Exception as e:
            logger.error(f"Recovery işlemi hatası: {e}")
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
        # TODO: Manager kontrolü eklenecek