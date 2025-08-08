from .config import DatabaseType                               # DB türü enum (SQLite, MySQL, PostgreSQL)
from .config import EngineConfig                               # Engine konfigrasyon sınıfı
from .config import DatabaseConfig                             # Database genel konfigrasyon sınıfı
from .config import (
                    get_sqlite_config,                         # SQLite için konfigrasyon factory
                    get_postgresql_config,                     # PostgreSQL için konfigrasyon factory
                    get_mysql_config                           # MySQL için konfigrasyon factory
                    )

# =============================================================================
# DATABASE ENGINE COMPONENTS  
# Database engine ve session yönetimi bileşenleri
# =============================================================================
from .engine import DatabaseEngine                             # Ana database engine sınıfı
from .engine import create_database_engine                     # Engine factory fonksiyonu

# =============================================================================
# ORM MODEL COMPONENTS
# SQLAlchemy tabloları ve model tanımları
# =============================================================================
from .models import Base                                        # SQLAlchemy declarative base

# =============================================================================
# ORCHESTRATION COMPONENTS
# Yüksek seviye database orchestration bileşenleri
# =============================================================================
from .orchestration import DatabaseOrchestration               # Ana orchestration sınıfı

__all__ = [
    # Configuration exports
    "DatabaseType",
    "EngineConfig", 
    "DatabaseConfig",
    "get_sqlite_config",
    "get_postgresql_config",
    "get_mysql_config",
    
    # Engine exports
    "DatabaseEngine",
    "create_database_engine",
    
    # Model exports
    "Base",
    
    # Orchestration exports
    "DatabaseOrchestration"
]