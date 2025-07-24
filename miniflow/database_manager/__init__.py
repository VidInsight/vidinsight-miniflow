"""
MINIFLOW DATABASE MANAGER MODULE
=================================

Bu modül Miniflow sisteminin kalbi olan database yönetimi için tüm bileşenleri sağlar.
Database Manager, workflow orchestration için gerekli tüm database operasyonlarını 
merkezi bir şekilde yönetir ve SQLAlchemy ORM kullanarak type-safe database erişimi sağlar.

MODÜL SORUMLULUKLARI:
====================
1. Database Configuration Management - Farklı DB türleri için konfigrasyon
2. Database Engine Management - Connection pooling, session management
3. ORM Model Definitions - Workflow, Node, Execution vb. modeller
4. CRUD Operations - Create, Read, Update, Delete operasyonları
5. Database Orchestration - Karmaşık iş akışı operasyonları

ARCHITECTURE OVERVIEW:
=====================
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Config        │    │    Engine       │    │    Models       │
│                 │    │                 │    │                 │
│ • DatabaseType  │    │ • Engine Pool   │    │ • Workflow      │
│ • Connection    │────│ • Session Mgmt  │────│ • Node          │
│ • Credentials   │    │ • Transactions  │    │ • Execution     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │  Orchestration  │
                    │                 │
                    │ • Workflow CRUD │
                    │ • Task Queue    │
                    │ • Dynamic Params│
                    │ • Result Mgmt   │
                    └─────────────────┘

USAGE EXAMPLE:
=============
```python
from miniflow.database_manager import (
    DatabaseEngine, DatabaseOrchestration, 
    get_sqlite_config, create_database_engine
)

# 1. Konfigrasyon oluştur
config = get_sqlite_config(db_path="miniflow.db")

# 2. Engine başlat
engine = create_database_engine(config)
engine.initialize_database()

# 3. Orchestration ile işlemler yap
orchestration = DatabaseOrchestration()
with engine.get_session_context() as session:
    workflow = orchestration.create_workflow(session, workflow_data)
```

DOSYA YAPISI:
============
├── config.py      - Database konfigrasyon sınıfları
├── engine.py      - Database engine ve session yönetimi
├── models.py      - SQLAlchemy ORM modelleri
├── orchestration.py - Yüksek seviye iş akışı operasyonları
└── crud/          - Temel CRUD operasyonları
    ├── base_crud.py
    ├── workflow_crud.py
    ├── execution_crud.py
    └── ...
"""

# =============================================================================
# VERSION INFORMATION
# =============================================================================
__version__ = "1.0.0"
__author__ = "Enes Arslan"

# =============================================================================
# CONFIGURATION COMPONENTS
# Database connection ve konfigrasyon bileşenleri
# =============================================================================
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

# =============================================================================
# PUBLIC API EXPORTS
# Bu modülden dışarıya açılan tüm bileşenler
# =============================================================================
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