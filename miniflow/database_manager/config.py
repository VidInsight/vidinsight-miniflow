"""
DATABASE CONFIGURATION MODULE
==============================

Bu modül Miniflow sisteminin farklı veritabanlarına bağlanabilmesi için gerekli 
konfigrasyon sınıflarını ve factory fonksiyonlarını sağlar.

MODÜL SORUMLULUKLARI:
====================
1. Database Type Definitions - Desteklenen veritabanı türleri
2. Engine Configuration - SQLAlchemy engine ayarları
3. Database Configuration - Connection string ve kimlik bilgileri
4. Factory Functions - Kolay konfigrasyon oluşturma fonksiyonları

DESTEKLENEN VERİTABANLARI:
=========================
• SQLite   - Embedded database, development ve test için ideal
• MySQL    - Production web uygulamaları için popüler seçenek  
• PostgreSQL - Enterprise uygulamalar için güçlü ve güvenilir

CONFIGURATION HIERARCHY:
=======================
DatabaseConfig
├── db_type: DatabaseType (enum)
├── db_name: str (database adı)
├── connection_info: host, port, username, password
└── engine_config: EngineConfig
    ├── pool_size: Connection pool boyutu
    ├── pool_timeout: Connection timeout süresi
    ├── isolation_level: Transaction isolation seviyesi
    └── connect_args: DB-specific connection parametreleri

USAGE EXAMPLES:
==============
```python
# SQLite (development)
config = get_sqlite_config(db_name="miniflow_dev")

# PostgreSQL (production)
config = get_postgresql_config(
    db_name="miniflow_prod",
    host="prod-db.company.com", 
    username="miniflow_user",
    password="secure_password"
)

# MySQL (staging)
config = get_mysql_config(
    db_name="miniflow_staging",
    host="staging-db.company.com",
    port=3306
)
```
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from enum import Enum

# =============================================================================
# DATABASE TYPE DEFINITIONS
# Desteklenen veritabanı türlerinin enum tanımları
# =============================================================================

class DatabaseType(Enum):
    """
    Miniflow tarafından desteklenen veritabanı türleri
    
    Attributes:
        SQLITE: Embedded database - Geliştirme ve test ortamları için
        MYSQL: MySQL/MariaDB - Web uygulamaları için popüler seçenek
        POSTGRESQL: PostgreSQL - Enterprise için güçlü ve feature-rich
    """
    SQLITE = "sqlite"
    MYSQL = "mysql" 
    POSTGRESQL = "postgresql"

# =============================================================================
# ENGINE CONFIGURATION CLASS
# SQLAlchemy engine için detaylı konfigrasyon ayarları
# =============================================================================

@dataclass
class EngineConfig:
    """
    SQLAlchemy Engine için kapsamlı konfigrasyon sınıfı
    
    Bu sınıf connection pooling, transaction management ve performance
    optimization için gerekli tüm ayarları içerir.
    
    CONNECTION POOLING PARAMETERS:
    - pool_size: Havuzda tutulacak maksimum connection sayısı
    - max_overflow: Pool dolduğunda oluşturulacak ekstra connection sayısı  
    - pool_timeout: Connection beklemek için maksimum süre (saniye)
    - pool_recycle: Connection'ın yenilenmesi için süre (saniye, -1 = disable)
    - pool_pre_ping: Connection'ların sağlık kontrolü
    
    DEBUG PARAMETERS:
    - echo: SQL query'lerinin loglanması
    - echo_pool: Connection pool aktivitelerinin loglanması
    
    SESSION PARAMETERS:  
    - autocommit: Otomatik commit (genelde False)
    - autoflush: Otomatik flush işlemi
    - expire_on_commit: Commit sonrası objelerin expire edilmesi
    - isolation_level: Transaction isolation seviyesi
    - connect_args: Database-specific connection argumentları
    """
    
    # Connection Pool Settings
    pool_size: int = 10                    # Varsayılan connection pool boyutu
    max_overflow: int = 20                 # Pool dolduğunda ekstra connection sayısı
    pool_timeout: int = 30                 # Connection almak için maksimum bekleme süresi
    pool_recycle: int = 3600              # Connection yenileme süresi (1 saat)
    pool_pre_ping: bool = True            # Connection sağlık kontrolü aktif

    # Debug and Logging Settings
    echo: bool = False                    # SQL query logging (production'da False)
    echo_pool: bool = False               # Pool activity logging (debug için)

    # Session Management Settings  
    autocommit: bool = False              # Manuel transaction control
    autoflush: bool = True                # Otomatik flush aktif
    expire_on_commit: bool = True         # Commit sonrası object refresh
    isolation_level: Optional[str] = None # DB-specific isolation level
    connect_args: Dict[str, Any] = field(default_factory=dict)  # Extra connection args

    def to_dict(self) -> Dict[str, Any]:
        """
        EngineConfig'i SQLAlchemy'nin create_engine() fonksiyonuna 
        geçirilebilecek dictionary formatına çevirir
        
        Returns:
            Dict[str, Any]: SQLAlchemy engine parametreleri
        """
        return {
            'pool_size': self.pool_size,
            'max_overflow': self.max_overflow, 
            'pool_timeout': self.pool_timeout,
            'pool_recycle': self.pool_recycle,
            'pool_pre_ping': self.pool_pre_ping,
            'connect_args': self.connect_args,
            'echo': self.echo,
            'echo_pool': self.echo_pool,
            'isolation_level': self.isolation_level,
        }

# =============================================================================
# DATABASE CONFIGURATION CLASS
# Ana database konfigrasyon sınıfı - connection bilgileri ve engine config
# =============================================================================

@dataclass
class DatabaseConfig:
    """
    Miniflow Database Manager için merkezi konfigrasyon sınıfı
    
    Bu sınıf hem connection bilgilerini hem de engine ayarlarını
    bir arada tutar ve farklı database türleri için connection string
    oluşturma yetenegi sağlar.
    
    CONNECTION INFO:
    - db_name: Database adı
    - db_type: Database türü (SQLite/MySQL/PostgreSQL)
    - host: Server adresi (SQLite için None)
    - port: Server portu (SQLite için None)  
    - username: Kullanıcı adı (SQLite için None)
    - password: Şifre (SQLite için None)
    
    ENGINE CONFIG:
    - engine_config: SQLAlchemy engine ayarları (EngineConfig instance)
    """
    
    # Database Identity
    db_name: str = None                                    # Database adı
    db_type: DatabaseType = None                          # Database türü (enum)
    
    # Connection Information (MySQL/PostgreSQL için gerekli)
    host: Optional[str] = None                            # Server hostname/IP
    port: Optional[int] = None                            # Server port number  
    username: Optional[str] = None                        # Database username
    password: Optional[str] = None                        # Database password
    
    # Engine Configuration
    engine_config: EngineConfig = field(default_factory=EngineConfig)  # SQLAlchemy engine config

    def get_connection_string(self) -> str:
        """
        Database türüne göre uygun SQLAlchemy connection string oluşturur
        
        Connection String Formats:
        - SQLite: sqlite:///database_name.db
        - MySQL: mysql+pymysql://user:pass@host:port/dbname
        - PostgreSQL: postgresql+psycopg2://user:pass@host:port/dbname
        
        Returns:
            str: SQLAlchemy connection string
            
        Raises:
            ValueError: Desteklenmeyen database türü için
        """
        if self.db_type == DatabaseType.SQLITE:
            # SQLite: Dosya tabanlı database
            return f"sqlite:///{self.db_name}.db" 
            
        elif self.db_type == DatabaseType.MYSQL:
            # MySQL: Network üzerinden MySQL server
            return f"mysql+pymysql://{self.username}:{self.password}@{self.host}:{self.port}/{self.db_name}" 
            
        elif self.db_type == DatabaseType.POSTGRESQL:
            # PostgreSQL: Network üzerinden PostgreSQL server
            return f"postgresql+psycopg2://{self.username}:{self.password}@{self.host}:{self.port}/{self.db_name}" 
            
        else:
            # Desteklenmeyen database türü
            raise ValueError(f"Unsupported database type: {self.db_type}")

# =============================================================================
# DATABASE-SPECIFIC ENGINE CONFIGURATIONS
# Her database türü için optimize edilmiş engine konfigrasyon tanımları
# =============================================================================

DB_ENGINE_CONFIGS = {
    # SQLite Configuration - Single-threaded embedded database
    DatabaseType.SQLITE: EngineConfig(
        pool_size=1,                                      # SQLite tek connection destekler
        max_overflow=0,                                   # Overflow connection yok
        pool_timeout=20,                                  # Kısa timeout
        pool_recycle=-1,                                  # Connection recycle devre dışı
        pool_pre_ping=False,                             # File-based DB için gereksiz
        connect_args={                                   # SQLite-specific ayarlar
            'check_same_thread': False,                  # Multi-thread erişime izin ver
            'timeout': 20                                # Database lock timeout
        },
        isolation_level=None,                            # SQLite default isolation
    ),
    
    # PostgreSQL Configuration - Production-ready enterprise database
    DatabaseType.POSTGRESQL: EngineConfig(
        pool_size=20,                                    # Yüksek concurrency için büyük pool
        max_overflow=30,                                 # Peak load için extra connections
        pool_timeout=60,                                 # Network gecikmesi için uzun timeout
        pool_recycle=3600,                              # 1 saatte bir connection yenile
        pool_pre_ping=True,                             # Network bağlantı kontrolü
        connect_args={                                  # PostgreSQL-specific ayarlar
            'connect_timeout': 30,                      # Initial connection timeout
            'application_name': 'miniflow_app'          # Connection identification
        },
        isolation_level='READ_COMMITTED',               # Safe isolation level
    ),
    
    # MySQL Configuration - Web application optimized
    DatabaseType.MYSQL: EngineConfig(
        pool_size=15,                                   # Orta seviye pool boyutu
        max_overflow=25,                                # Esnek overflow
        pool_timeout=45,                                # Orta seviye timeout
        pool_recycle=7200,                             # 2 saatte bir connection yenile
        pool_pre_ping=True,                            # MySQL server durumu kontrolü
        connect_args={                                 # MySQL-specific ayarlar
            'connect_timeout': 30,                     # Connection establishment timeout
            'charset': 'utf8mb4',                      # Full UTF-8 support
            'autocommit': False                        # Manual transaction control
        },
        isolation_level='READ_COMMITTED',              # Web app için uygun isolation
    ),
}

# =============================================================================
# CONFIGURATION FACTORY FUNCTIONS
# Kolay ve tip-güvenli konfigrasyon oluşturma fonksiyonları
# =============================================================================

def get_sqlite_config(db_name: str = "miniflow_database") -> DatabaseConfig:
    """
    SQLite database için optimize edilmiş konfigrasyon oluşturur
    
    SQLite ideal kullanım alanları:
    - Development ve testing
    - Küçük uygulamalar
    - Embedded sistemler
    - Prototype geliştirme
    
    Args:
        db_name (str): SQLite database dosya adı (.db uzantısı otomatik eklenir)
        
    Returns:
        DatabaseConfig: SQLite için optimize edilmiş konfigrasyon
    """
    return get_database_config(db_type=DatabaseType.SQLITE, db_name=db_name)

def get_postgresql_config(
    db_name: str = "miniflow_database", 
    host: str = "localhost", 
    port: int = 5432, 
    username: str = "postgres", 
    password: str = "password"
) -> DatabaseConfig:
    """
    PostgreSQL database için optimize edilmiş konfigrasyon oluşturur
    
    PostgreSQL ideal kullanım alanları:
    - Enterprise uygulamalar
    - Yüksek concurrency gereksinimleri
    - Complex query'ler
    - ACID compliance önemli olan sistemler
    
    Args:
        db_name (str): PostgreSQL database adı
        host (str): PostgreSQL server adresi
        port (int): PostgreSQL server portu (varsayılan: 5432)
        username (str): Database kullanıcı adı
        password (str): Database şifresi
        
    Returns:
        DatabaseConfig: PostgreSQL için optimize edilmiş konfigrasyon
    """
    return get_database_config(
        db_type=DatabaseType.POSTGRESQL, 
        db_name=db_name, 
        host=host, 
        port=port,
        username=username, 
        password=password
    )

def get_mysql_config(
    db_name: str = "miniflow_database", 
    host: str = "localhost", 
    port: int = 3306,
    username: str = "root", 
    password: str = "password"
) -> DatabaseConfig:
    """
    MySQL database için optimize edilmiş konfigrasyon oluşturur
    
    MySQL ideal kullanım alanları:
    - Web uygulamaları
    - Content management sistemleri
    - E-commerce platformları
    - Blog ve forum siteleri
    
    Args:
        db_name (str): MySQL database adı
        host (str): MySQL server adresi  
        port (int): MySQL server portu (varsayılan: 3306)
        username (str): Database kullanıcı adı
        password (str): Database şifresi
        
    Returns:
        DatabaseConfig: MySQL için optimize edilmiş konfigrasyon
    """
    return get_database_config(
        db_type=DatabaseType.MYSQL, 
        db_name=db_name, 
        host=host, 
        port=port,
        username=username, 
        password=password
    )

def get_database_config(
    db_name: str, 
    db_type: DatabaseType, 
    host: Optional[str] = None, 
    port: Optional[int] = None,  
    username: Optional[str] = None,  
    password: Optional[str] = None, 
    custom_engine_config: Optional[EngineConfig] = None
) -> DatabaseConfig:
    """
    Generic database konfigrasyon oluşturucu fonksiyon
    
    Bu fonksiyon tüm database türleri için merkezi konfigrasyon oluşturma
    noktasıdır. Diğer get_*_config fonksiyonları bu fonksiyonu kullanır.
    
    ALGORITHM:
    1. Engine konfigrasyonunu belirle (custom veya predefined)
    2. Database türüne uygun default değerleri validate et
    3. DatabaseConfig instance oluştur ve döndür
    
    Args:
        db_name (str): Database adı (gerekli)
        db_type (DatabaseType): Database türü (gerekli)
        host (Optional[str]): Server adresi (MySQL/PostgreSQL için gerekli)
        port (Optional[int]): Server portu (MySQL/PostgreSQL için gerekli)
        username (Optional[str]): Kullanıcı adı (MySQL/PostgreSQL için gerekli)
        password (Optional[str]): Şifre (MySQL/PostgreSQL için gerekli)
        custom_engine_config (Optional[EngineConfig]): Özel engine konfigrasyonu
        
    Returns:
        DatabaseConfig: Belirtilen parametrelerle oluşturulmuş konfigrasyon
        
    Raises:
        KeyError: Bilinmeyen database türü için
    """
    
    # Step 1: Engine konfigrasyonunu belirle
    # Öncelik: custom_engine_config > predefined config
    if custom_engine_config:
        # Kullanıcı özel konfigrasyon vermiş, onu kullan
        engine_config = custom_engine_config
    else:
        # Predefined konfigrasyon kullan (database türüne göre optimize edilmiş)
        engine_config = DB_ENGINE_CONFIGS.get(db_type)
        
        # Eğer database türü desteklenmiyorsa hata fırlat
        if engine_config is None:
            raise KeyError(f"No predefined engine config found for database type: {db_type}")

    # Step 2: DatabaseConfig instance oluştur ve döndür
    return DatabaseConfig(
        db_type=db_type,                    # Database türü
        db_name=db_name,                   # Database adı
        host=host,                         # Server adresi (SQLite için None)
        port=port,                         # Server portu (SQLite için None)  
        username=username,                 # Kullanıcı adı (SQLite için None)
        password=password,                 # Şifre (SQLite için None)
        engine_config=engine_config        # Engine konfigrasyonu
    )
        