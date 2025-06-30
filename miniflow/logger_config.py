import shutil
import logging.config
from pathlib import Path
from datetime import datetime


def cleanup_old_logs(max_folders=5):
    """Eski log klasörlerini temizle - en fazla N adet timestamp klasörü tut"""
    logs_dir = Path("logs")
    if not logs_dir.exists():
        return
    
    # Tüm timestamp klasörlerini al ve isme göre sırala (timestamp formatı nedeniyle)
    folders = sorted([f for f in logs_dir.iterdir() if f.is_dir()])
    
    # Eğer klasör sayısı max_folders'ı aşıyorsa, eski olanları sil
    if len(folders) > max_folders:
        folders_to_delete = folders[:-max_folders]  # Son N klasör hariç hepsini al
        for folder in folders_to_delete:
            try:
                shutil.rmtree(folder)
                print(f"Eski log klasörü silindi: {folder.name}")
            except Exception as e:
                print(f"Log klasörü silinirken hata: {folder.name} - {e}")


class FlushingFileHandler(logging.FileHandler):
    """
    Real-time logging için custom FileHandler
    Her log mesajından sonra dosyayı flush eder
    """
    def emit(self, record):
        super().emit(record)
        self.flush()  # Her log mesajından sonra flush et


def setup_logging() -> Path:
    """Log sistemini başlat; timestamp'li klasör oluştur ve log dosyalarını içine yerleştir."""
    # Timestamp'li klasör oluştur
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = Path("logs") / timestamp
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Önce eski log klasörlerini temizle
    cleanup_old_logs(max_folders=5)
    
    # Dynamic CONFIG with timestamp paths
    CONFIG = {
        "version": 1,
        "disable_existing_loggers": False,

        # ---------- FORMATTERS ---------- #
        "formatters": {
            "simple":  {"format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"},
            "detailed": {
                "format": "%(asctime)s [%(process)d] %(name)s:%(lineno)d — %(levelname)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },

        # ---------- HANDLERS ---------- #
        "handlers": {
            # Ana handler - console
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "simple",
                "level": "INFO",
                "stream": "ext://sys.stdout",
            },
            # Main App - Real-time Dosya Handler
            "file_main": {
                "()": FlushingFileHandler,
                "formatter": "detailed",
                "level": "DEBUG",
                "filename": str(log_dir / "main.log"),
                "mode": "a",
                "encoding": "utf-8",
            },
            # Input Monitor - Real-time Dosya Handler
            "file_input_monitor": {
                "()": FlushingFileHandler,
                "formatter": "detailed",
                "level": "DEBUG",
                "filename": str(log_dir / "input_monitor.log"),
                "mode": "a",
                "encoding": "utf-8",
            },
            # Output Monitor - Real-time Dosya Handler
            "file_output_monitor": {
                "()": FlushingFileHandler,
                "formatter": "detailed",
                "level": "DEBUG",
                "filename": str(log_dir / "output_monitor.log"),
                "mode": "a",
                "encoding": "utf-8",
            },
        },

        # ---------- LOGGERS ---------- #
        "loggers": {
            "__main__": {                    
                "handlers": ["console", "file_main"],
                "level": "INFO",
                "propagate": False,
            },
            "miniflow.main": {                    
                "handlers": ["console", "file_main"],
                "level": "INFO",
                "propagate": False,
            },
            "miniflow.scheduler": {               
                "handlers": ["console", "file_main"],
                "level": "DEBUG",
                "propagate": False,
            },
            "miniflow.scheduler.input_monitor": {               
                "handlers": ["console", "file_input_monitor"],
                "level": "DEBUG",
                "propagate": False,
            },
            "miniflow.scheduler.output_monitor": {               
                "handlers": ["console", "file_output_monitor"],
                "level": "DEBUG",
                "propagate": False,
            },
        },

        # Fallback (root) → sadece ciddi hatalar
        "root": {"level": "WARNING", "handlers": ["console"]},
    }
    
    # Logger config'i uygula
    logging.config.dictConfig(CONFIG)
    
    # Log klasörü bilgisini konsola yazdır
    print(f"Log dosyaları şu klasörde oluşturuldu: {log_dir}")
    print("Oluşturulan log dosyaları:")
    print("   • main.log - Ana uygulama ve scheduler logları")
    print("   • input_monitor.log - Task queue monitoring logları")
    print("   • output_monitor.log - Task sonuç işleme logları")
    return log_dir