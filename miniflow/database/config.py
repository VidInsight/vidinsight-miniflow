from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from enum import Enum

# ==================================================================================================== DATABASE TYPES ==
# DatabaseType enum, desteklenen farklı veritabanı türlerini temsil eder.

class DatabaseType(Enum):
    SQLITE = "sqlite"
    MYSQL = "mysql" 
    POSTGRESQL = "postgresql"


# ============================================================================================== ENGINE CONFIGURATION ==
# EngineConfig sınıfı, SQLAlchemy engine için gerekli konfigrasyonları tutar.

@dataclass
class EngineConfig:
    # Connection Pool Settings
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600
    pool_pre_ping: bool = True

    # Debug and Logging Settings
    echo: bool = False
    echo_pool: bool = False

    # Session Management Settings  
    autocommit: bool = False
    autoflush: bool = True
    expire_on_commit: bool = True
    isolation_level: Optional[str] = None
    connect_args: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self, db_type: Optional['DatabaseType'] = None) -> Dict[str, Any]:
        """
        Engine config'i SQLAlchemy parametrelerine çevirir
        
        Args:
            db_type: Database türü - SQLite için bazı parametreler filtrelenir
        """
        config = {
            'connect_args': self.connect_args,
            'echo': self.echo,
            'echo_pool': self.echo_pool,
            'isolation_level': self.isolation_level,
        }
        
        # SQLite için connection pooling parametreleri desteklenmez
        if db_type != DatabaseType.SQLITE:
            config.update({
                'pool_size': self.pool_size,
                'max_overflow': self.max_overflow, 
                'pool_timeout': self.pool_timeout,
                'pool_recycle': self.pool_recycle,
                'pool_pre_ping': self.pool_pre_ping,
            })
        else:
            # SQLite için sadece desteklenen parametreler
            config.update({
                'pool_pre_ping': self.pool_pre_ping,
            })
            
        return config
    
    def get_session_config(self) -> Dict[str, Any]:
        """
        Session-level parametreleri döndürür (sessionmaker için)
        
        Returns:
            Dict[str, Any]: Session configuration parametreleri
        """
        return {
            'autocommit': self.autocommit,
            'autoflush': self.autoflush,
            'expire_on_commit': self.expire_on_commit,
        }


# ============================================================================================ DATABASE CONFIGURATION ==
# DatabaseConfig sınıfı, veritabanı bağlantı bilgilerini ve engine konfigrasyonlarını tutar.

@dataclass
class DatabaseConfig:
    # Database Identity
    db_name: str = None
    db_type: DatabaseType = None
    
    # Connection Information (MySQL/PostgreSQL için gerekli)
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    
    # Engine Configuration
    engine_config: EngineConfig = field(default_factory=EngineConfig)

    def get_connection_string(self) -> str:
        if self.db_type == DatabaseType.SQLITE:
            # SQLite: In-memory veya dosya tabanlı database
            if self.db_name == ":memory:":
                return "sqlite:///:memory:"
            else:
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

    def to_dict(self, mask_password: bool = True) -> Dict[str, Any]:
        return {
            'db_name': self.db_name,
            'db_type': self.db_type.value if self.db_type else None,
            'host': self.host,
            'port': self.port,
            'username': self.username,
            'password': '***masked***' if mask_password and self.password else self.password,
            'engine_config': self.engine_config.to_dict() if self.engine_config else None
        }


# ============================================================================================= ENGINE CONFIGURATIONS ==
# Her database türü için farklı ayarlar içeren önceden tanımlanmış engine konfigrasyonları
# Bu konfigrasyonlar, farklı database türleri için optimize edilmiştir.

DB_ENGINE_CONFIGS = {
    # SQLite Configuration - Single-threaded embedded database
    DatabaseType.SQLITE: EngineConfig(
        pool_size=1,                                        # SQLite tek connection destekler
        max_overflow=0,                                     # Overflow connection yok
        pool_timeout=20,                                    # Kısa timeout
        pool_recycle=-1,                                    # Connection recycle devre dışı
        pool_pre_ping=False,                                # File-based DB için gereksiz
        connect_args={                                      # SQLite-specific ayarlar
            'check_same_thread': False,                     # Multi-thread erişime izin ver
            'timeout': 20                                   # Database lock timeout
        },
        isolation_level=None,                               # SQLite default isolation
    ),
    
    # PostgreSQL Configuration - Production-ready enterprise database
    DatabaseType.POSTGRESQL: EngineConfig(
        pool_size=20,                                       # Yüksek concurrency için büyük pool
        max_overflow=30,                                    # Peak load için extra connections
        pool_timeout=60,                                    # Network gecikmesi için uzun timeout
        pool_recycle=3600,                                  # 1 saatte bir connection yenile
        pool_pre_ping=True,                                 # Network bağlantı kontrolü
        connect_args={                                      # PostgreSQL-specific ayarlar
            'connect_timeout': 30,                          # Initial connection timeout
            'application_name': 'miniflow_app'              # Connection identification
        },
        isolation_level='READ_COMMITTED',                   # Safe isolation level
    ),
    
    # MySQL Configuration - Web application optimized
    DatabaseType.MYSQL: EngineConfig(
        pool_size=15,                                       # Orta seviye pool boyutu
        max_overflow=25,                                    # Esnek overflow
        pool_timeout=45,                                    # Orta seviye timeout
        pool_recycle=7200,                                  # 2 saatte bir connection yenile
        pool_pre_ping=True,                                 # MySQL server durumu kontrolü
        connect_args={                                      # MySQL-specific ayarlar
            'connect_timeout': 30,                          # Connection establishment timeout
            'charset': 'utf8mb4',                           # Full UTF-8 support
            'autocommit': False                             # Manual transaction control
        },
        isolation_level='READ_COMMITTED',                   # Web app için uygun isolation
    ),
}


# ========================================================================================== CONFIG CREATION FUNCTION ==
# Aşağıda tanımlanan factory fonksiyonlarının config oluştrmak için kullandığı fonksiyon

def get_database_config(db_name: str,  db_type: DatabaseType, host: Optional[str] = None, port: Optional[int] = None,
                        username: Optional[str] = None, password: Optional[str] = None,
                        custom_engine_config: Optional[EngineConfig] = None) -> DatabaseConfig:

    # ADIM 1: Engine konfigrasyonunu belirle
    # Eğer kullanıcı özel bir engine konfigrasyonu vermişse, onu kullanacağız
    if custom_engine_config:
        # Kullanıcı özel konfigrasyon vermiş, onu kullan
        engine_config = custom_engine_config
    else:
        # Eğer kullanıcı özel bir konfigrasyon vermemişse, önceden tanımlanmış engine konfigrasyonunu kullan
        engine_config = DB_ENGINE_CONFIGS.get(db_type)

        # Eğer database türü desteklenmiyorsa hata fırlat
        if engine_config is None:
            raise KeyError(f"No predefined engine config found for database type: {db_type}")

    # ADIM 2: DatabaseConfig instance oluştur ve döndür
    return DatabaseConfig(
        db_type=db_type,                # Database türü
        db_name=db_name,                # Database adı
        host=host,                      # Server adresi (SQLite için None)
        port=port,                      # Server portu (SQLite için None)
        username=username,              # Kullanıcı adı (SQLite için None)
        password=password,              # Şifre (SQLite için None)
        engine_config=engine_config     # Engine konfigrasyonu
    )


# ================================================================================================= FACTORY FUNCTIONS ==
# Kolay bir şekilde database konfigürasyonu oluşturmak için tanımlanmş olan factory fonksiyonları

def get_sqlite_config(**database_kwargs) -> DatabaseConfig:
    return get_database_config(
        db_type=DatabaseType.SQLITE,
        db_name=database_kwargs.get('db_name', 'database.db')
    )

def get_postgresql_config(**database_kwargs) -> DatabaseConfig:
    return get_database_config(
        db_type=DatabaseType.POSTGRESQL,
        db_name=database_kwargs.get('db_name', 'postgres'),
        host=database_kwargs.get('host', 'localhost'),
        port=database_kwargs.get('port', 5432),
        username=database_kwargs.get('username', 'postgres'),
        password=database_kwargs.get('password', '')
    )

def get_mysql_config(**database_kwargs) -> DatabaseConfig:
    return get_database_config(
        db_type=DatabaseType.MYSQL,
        db_name=database_kwargs.get('db_name', 'mysql'),
        host=database_kwargs.get('host', 'localhost'),
        port=database_kwargs.get('port', 3306),
        username=database_kwargs.get('username', 'root'),
        password=database_kwargs.get('password', '')
    )