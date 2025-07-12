import os
import shutil
import logging.config
from pathlib import Path
from datetime import datetime


def build_config(log_dir: Path) -> dict:
    """log_dir bilgisini alan ve eksiksiz dictConfig döndüren yardımcı."""
    return {
        "version": 1,
        "disable_existing_loggers": False,

        # --------------------------- Formatters --------------------------- #
        "formatters": {
            "simple": {
                "format": "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
                "datefmt": "%H:%M:%S",
            },
            "detailed": {
                "format": (
                    "%(asctime)s [%(process)d] %(name)s:%(lineno)d — "
                    "%(levelname)s: %(message)s"
                ),
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },

        # ---------------------------- Handlers --------------------------- #
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "simple",
                "stream": "ext://sys.stdout",
            },
            "file_main": {
                "class": "logging.FileHandler",
                "level": "DEBUG",
                "formatter": "detailed",
                "filename": str(log_dir / "main.log"),
                "mode": "a",
                "encoding": "utf-8",
            },
        },

        # ---------------------------- Loggers ---------------------------- #
        "loggers": {
            "__main__": {
                "handlers": ["console", "file_main"],
                "level": "DEBUG",
                "propagate": False,
            },
            # Örnek paket logger'ı
            "app.database": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False,
            },
        },

        # ------------------------------ Root ----------------------------- #
        "root": {
            "level": "WARNING",
            "handlers": ["console"],
        },
    }


# DOSYA KONTROLÜ
# ==============================================================
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


# LOGGER KURULUMU
# ==============================================================
def setup_logging(max_folders: int = 5):
    """Hem klasörü hazırlar hem dictConfig'i uygular."""
    today = datetime.now().strftime("%Y%m%d")
    log_dir = Path("logs") / today
    log_dir.mkdir(parents=True, exist_ok=True)

    cleanup_old_logs(max_folders=max_folders)

    logging.config.dictConfig(build_config(log_dir))
    return log_dir  # ileride test/log kaydı için istenir