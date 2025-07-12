"""
DatabaseManager için kullanılacak konfigrasyon tanımları.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from enum import Enum


# VERI MODELLERININ TANIMLANMASI
# ==============================================================
# Bu adımda Database Manager'ın çalışırken kullanacağı verilerin 
# daha kolay yönetilebilmesi ve okunabilir olması için önceden 
# tanımlı veri tipleri (sınıfları) oluşturyoruz.

class DatabaseType(Enum):
    """ Kullanılabilir veritabanı tipleri """
    SQLITE = "sqlite"
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"


@dataclass
class EngineConfig:
    """ SqlAlchemy tarafında oluşturulacak motor için konfigrasyonlar"""
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600
    pool_pre_ping: bool = True

    echo: bool = False
    echo_pool: bool = False

    autocommit: bool = False
    autoflush: bool = True
    expire_on_commit: bool = True
    isolation_level: Optional[str] = None
    connect_args: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
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
    

@dataclass
class DatabaseConfig:
    """ Database Manager tarafından kullnılacak konfigrasyonlar """
    db_name: str = None
    db_type: DatabaseType = None
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    engine_config: EngineConfig = field(default_factory=EngineConfig)

    def get_connection_string(self) -> str:
        if self.db_type == DatabaseType.SQLITE:
            return f"sqlite:///{self.db_name}.db" 
        elif self.db_type == DatabaseType.MYSQL:
            return f"mysql+pymysql://{self.username}:{self.password}@{self.host}:{self.port}/{self.db_name}" 
        elif self.db_type == DatabaseType.POSTGRESQL:
            return f"postgresql+psycopg2://{self.username}:{self.password}@{self.host}:{self.port}/{self.db_name}" 
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")
        

# VERITABANINA ÖZEL ENGINE CONFIG TANIMLARI
# ==============================================================
# Farklı veritabanı optimize çalışmak için farklı konfigrasyon
# ayarlarına sahip olmalıdır. Manager'ı hızlıca başlatmak için 
# konfigrasyon tanımları önceden tanımlanır.

DB_ENGINE_CONFIGS = {
    DatabaseType.SQLITE: EngineConfig(
        pool_size=1,
        max_overflow=0,
        pool_timeout=20,
        pool_recycle=-1,
        pool_pre_ping=False,
        connect_args={'check_same_thread': False, 'timeout': 20},
        isolation_level=None,
    ),
    DatabaseType.POSTGRESQL: EngineConfig(
        pool_size=20,
        max_overflow=30,
        pool_timeout=60,
        pool_recycle=3600,
        pool_pre_ping=True,
        connect_args={'connect_timeout': 30, 'application_name': 'sqlalchemy_demo'},
        isolation_level='READ_COMMITTED',
    ),
    DatabaseType.MYSQL: EngineConfig(
        pool_size=15,
        max_overflow=25,
        pool_timeout=45,
        pool_recycle=7200,
        pool_pre_ping=True,
        connect_args={'connect_timeout': 30, 'charset': 'utf8mb4', 'autocommit': False},
        isolation_level='READ_COMMITTED',
    ),
}


# KONFIGRASYONLARI OLUŞTURACAK UTILTY FONKSIYONLARI
# ==============================================================
# Her veritabanı tipi için konfigrasyon oluşturucu fonksiyon ve 
# bu fonksyonları dinamik olarka kullanan 'get_database_config'
# fonksiyonu tanımlanır. 

def get_sqlite_config(db_name: str = "TEST_DATABASE") -> DatabaseConfig:
    return get_database_config(db_type=DatabaseType.SQLITE, db_name=db_name)

def get_postgresql_config(db_name: str = "TEST_DATABASE", host: str = "localhost", port: int = 5432, 
                     username: str = "postgres", password: str = "password") -> DatabaseConfig:
    return get_database_config(db_type=DatabaseType.POSTGRESQL, db_name=db_name, host=host, port=port,
                               username=username, password=password)

def get_mysql_config(db_name: str = "TEST_DATABASE", host: str = "localhost", port: int = 3306,
                     username: str = "root", password: str = "password") -> DatabaseConfig:
    return get_database_config(db_type=DatabaseType.MYSQL, db_name=db_name, host=host, port=port,
                               username=username, password=password)

def get_database_config(db_name: str, db_type: DatabaseType, host: Optional[str] = None, port: Optional[int] = None,  username: Optional[str] = None,  
                        password: Optional[str] = None, custom_engine_config: Optional[EngineConfig] = None, ) -> DatabaseConfig:
    """ 
    Verilen parametreler ile DatabaseConfig nesnesi oluşturur ve döndürür.

    Parameters:
    db_name: veritabanı'nın adı
    db_type: veritabanı tipi (DatabaseType)
    host: bağlantı adresi (mysql ve postgresql için)
    port: bağlantı portu (mysql ve postgresql için)
    username: veritabanına giriş için kullanıcıadı (mysql ve postgresql için)
    password: veritabanına giriş için şifre (mysql ve postgresql için)
    custom_engine_config: hazır motor konfigrasyonlarına yerine yeni bir konfigrasyon
    """

    # Motor Konfigrasyonunu Hazırla
    engine_config: dict = None
    # Eğer motor konfigrasyonu varsa onu kullan
    if custom_engine_config:
        engine_config = custom_engine_config
    else:
    # Eğer motor konfigrasyonu yok ise hazır tanımlardan ilgili olanı kullan
        engine_config = DB_ENGINE_CONFIGS.get(db_type)

    # DatabaseConfig nesnesini döndür    
    return DatabaseConfig(
        db_type=db_type,
        db_name=db_name,  
        host=host,
        port=port,
        username=username,
        password=password,
        engine_config=engine_config
    )
        