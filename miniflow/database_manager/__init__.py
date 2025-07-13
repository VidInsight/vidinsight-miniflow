"""
Database Manager Module
=======================
Miniflow system için kapsamlı database management modülü.

Bu modül şunları içerir:
- Database ve Database Engine için konfigrasyon tanımları
- Miniflow veritabanı içn SQLAlchemy modelleri
- CRUD operasyonları
- Orchestration (Orkestrasyon) sınıfı
"""

# VERSIYON ELEMANLARI
# ==============================================================
__version__ = "1.0.0"
__author__ = "Enes Arslan"


# KONFIGRASYON ELEMANLARI
# ==============================================================
from .config import DatabaseType                               
from .config import EngineConfig                               
from .config import DatabaseConfig                             
from .config import (
                    get_sqlite_config,                         
                    get_postgresql_config,                     
                    get_mysql_config                           
                    )


# ENGINE ELEMANLARI
# ==============================================================
from .engine import DatabaseEngine
from .engine import create_database_engine

# MODEL ELEMANLARI
# ==============================================================
from .models import Base

# ORCHESTRATION ELEMANLARI
# ==============================================================
from .orchestration import DatabaseOrchestration


__all__ = [
    "DatabaseType",
    "EngineConfig",
    "DatabaseConfig",
    "get_sqlite_config",
    "get_postgresql_config",
    "get_mysql_config",
    "DatabaseEngine",
    "create_database_engine",
    "Base",
    "DatabaseOrchestration",
    "DatabaseOrchestration"
]