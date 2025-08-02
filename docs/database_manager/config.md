# Miniflow Database Manager - Config Dokümantasyonu

## Giriş

Miniflow Database Manager modülü farklı veritabanı türleri için config oluşturmayı kolaylaştırır. SQLite, MySQL ve 
PostgreSQL veritabanları desteklenir ve her biri için optimize edilmiş ayarlar mevcuttur. Bu modül SQLAlchemy engine 
konfigrasyonunu basit factory fonksiyonları ile yapmayı sağlar.

## Desteklenen Veritabanı Türleri

Sistem şu veritabanı türlerini destekler:
- **SQLITE**: Dosya tabanlı hafif veritabanı
- **MYSQL**: Web uygulamaları için popüler seçenek  
- **POSTGRESQL**: Kurumsal uygulamalar için güçlü veritabanı

```python
class DatabaseType(Enum):
    SQLITE = "sqlite"
    MYSQL = "mysql" 
    POSTGRESQL = "postgresql"
```

## EngineConfig Sınıfı

EngineConfig sınıfı SQLAlchemy engine oluşturmak için gerekli tüm parametreleri içerir. Kullanıcı bu parametreleri 
tanımlamak zorunda değil, sistem her veritabanı türü için önceden optimize edilmiş ayarları barındırmaktadır. Eğer
herhangi bir parametre girilmez ise varsayılan değerler kullanılır. Eğer sadece bir kısmı girilmiş ise eksik 
parametreler varsayılan değerlerle doldurulur.

```python
@dataclass
class EngineConfig:
    # Connection Pool ayarları
    pool_size: int = 10                                         # Aynı anda açık bağlantı sayısı
    max_overflow: int = 20                                      # Pool dolduğunda ekstra bağlantı sayısı  
    pool_timeout: int = 30                                      # Bağlantı beklemek için max süre
    pool_recycle: int = 3600                                    # Bağlantıları ne kadar sürede yenile
    pool_pre_ping: bool = True                                  # Bağlantı öncesi ping kontrolü

    # Debug ve Logging ayarları
    echo: bool = False                                          # SQL sorgularını konsola yazdır
    echo_pool: bool = False                                     # Pool işlemlerini göster

    # Session yönetimi ayarları  
    autocommit: bool = False                                    # Otomatik commit
    autoflush: bool = True                                      # Otomatik flush
    expire_on_commit: bool = True                               # Commit sonrası objeleri expire et
    isolation_level: Optional[str] = None                       # Transaction isolation seviyesi
    connect_args: Dict[str, Any] = field(default_factory=dict)  # Veritabanına özel parametreler
```

Bu sınıf `to_dict()` metodu ile dictionary formatına çevrilebilir. Bu özellik SQLAlchemy engine oluştururken 
parametreleri geçmek için kullanılır.

### to_dict() Metodu

EngineConfig'i dictionary formatına çevirir ve database türüne göre uygun parametreleri filtreler.

```python
def to_dict(self, db_type: Optional[DatabaseType] = None) -> Dict[str, Any]:
    """
    Engine config'i SQLAlchemy parametrelerine çevirir
    
    Args:
        db_type: Database türü - SQLite için bazı parametreler filtrelenir
    """
```

**SQLite Filtreleme**: SQLite için connection pooling parametreleri desteklenmediğinden filtrelenir.
**Network DB'ler**: MySQL ve PostgreSQL için tüm parametreler dahil edilir.

## DatabaseConfig Sınıfı

DatabaseConfig sınıfı veritabanı bağlantı bilgilerini ve engine konfigrasyonunu bir arada tutar. Bu sınıf üzerinden 
connection string oluşturulur, oluştuurlan connection string ile veritabanı bağlantısı kurulur.

```python
@dataclass
class DatabaseConfig:
    db_name: str = None                                         # Veritabanı adı
    db_type: DatabaseType = None                                # Veritabanı türü
    
    # Network bağlantıları için gerekli (MySQL/PostgreSQL)
    host: Optional[str] = None                                  # Server adresi
    port: Optional[int] = None                                  # Port numarası
    username: Optional[str] = None                              # Kullanıcı adı  
    password: Optional[str] = None                              # Şifre
    
    # Engine konfigrasyonu
    engine_config: EngineConfig = field(default_factory=EngineConfig)
```

### Connection String Oluşturma

DatabaseConfig sınıfı `get_connection_string()` metodu ile veritabanı türüne göre doğru connection string formatını 
otomatik oluşturur:

- **SQLite**: `sqlite:///database_name.db`
- **MySQL**: `mysql+pymysql://username:password@host:port/database_name`  
- **PostgreSQL**: `postgresql+psycopg2://username:password@host:port/database_name`

### to_dict() Metodu

DatabaseConfig'i dictionary formatına çevirir ve hassas bilgileri maskeleyebilir.

```python
def to_dict(self, mask_password: bool = True) -> Dict[str, Any]:
    """
    DatabaseConfig'i dictionary'ye çevirir
    
    Args:
        mask_password: True ise password alanı ***masked*** olarak gösterilir
        
    Returns:
        Dict[str, Any]: Config dictionary'si
    """
```

**Güvenlik Özelliği**: `mask_password=True` (varsayılan) ile password alanı `***masked***` olarak gösterilir.

**Kullanım Örnekleri:**
```python
config = get_postgresql_config(
    db_name="prod_db",
    username="admin", 
    password="secret123"
)

# Güvenli görüntüleme (password masked)
safe_dict = config.to_dict()
# Çıktı: {'password': '***masked***', ...}

# Tam görüntüleme (dikkatli kullanın!)
full_dict = config.to_dict(mask_password=False) 
# Çıktı: {'password': 'secret123', ...}
```

## Önceden Tanımlanmış Engine Konfigrasyonları

Sistem her veritabanı türü için optimize edilmiş engine konfigrasyonları içerir. Bu konfigrasyonlar `DB_ENGINE_CONFIGS` 
dictionary'sinde saklanır ve ihtiyaç duyulduğunda otomatik olarak kullanılır.

### SQLite Konfigrasyonu
SQLite single-threaded embedded database olduğu için özel ayarlara ihtiyaç duyar. Pool size 1 olarak ayarlanır çünkü 
SQLite tek connection destekler. Network kontrollerine gerek olmadığı için pre_ping kapatılır.

```python
DatabaseType.SQLITE: EngineConfig(
    pool_size=1,                          # SQLite tek connection destekler
    max_overflow=0,                       # Overflow connection yok  
    pool_timeout=20,                      # Kısa timeout
    pool_recycle=-1,                      # Connection recycle devre dışı
    pool_pre_ping=False,                  # File-based DB için gereksiz
    connect_args={
        'check_same_thread': False,       # Multi-thread erişime izin ver
        'timeout': 20                     # Database lock timeout
    },
    isolation_level=None,                 # SQLite default isolation
)
```

### PostgreSQL Konfigrasyonu  
PostgreSQL production-ready enterprise database olarak yüksek concurrency için optimize edilmiştir. Büyük pool size ve 
uzun timeout değerleri kullanır.

```python
DatabaseType.POSTGRESQL: EngineConfig(
    pool_size=20,                         # Yüksek concurrency için büyük pool
    max_overflow=30,                      # Peak load için extra connections
    pool_timeout=60,                      # Network gecikmesi için uzun timeout  
    pool_recycle=3600,                    # 1 saatte bir connection yenile
    pool_pre_ping=True,                   # Network bağlantı kontrolü
    connect_args={
        'connect_timeout': 30,            # Initial connection timeout
        'application_name': 'miniflow_app' # Connection identification
    },
    isolation_level='READ_COMMITTED',     # Safe isolation level
)
```

### MySQL Konfigrasyonu
MySQL web application için optimize edilmiştir. Orta seviye pool boyutu ve esnek overflow ayarları kullanır. UTF-8 
desteği için özel charset ayarı yapılır.

```python
DatabaseType.MYSQL: EngineConfig(
    pool_size=15,                         # Orta seviye pool boyutu
    max_overflow=25,                      # Esnek overflow
    pool_timeout=45,                      # Orta seviye timeout
    pool_recycle=7200,                    # 2 saatte bir connection yenile
    pool_pre_ping=True,                   # MySQL server durumu kontrolü
    connect_args={
        'connect_timeout': 30,            # Connection establishment timeout
        'charset': 'utf8mb4',             # Full UTF-8 support  
        'autocommit': False               # Manual transaction control
    },
    isolation_level='READ_COMMITTED',     # Web app için uygun isolation
)
```

## Factory Fonksiyonları

Desteklenen veritabanı tipleri için config oluşturmak amacıyla factory fonksiyonları tanımlanmıştır. Factory 
fonksiyonlarının amacı uzun şekilde konfigrasyon nesnesi oluşturma yerine tek bir fonksiyon ile konfigrasyon nesnesi 
oluşturmaktır. 

Factory fonksiyonları `**database_kwargs` parametresi alır. Bu kwargs keyword argümanları kısaltması olup veritabanı 
konfigrasyonu oluşturmak için gerekli parametreleri içermelidir. Bu parametreler DatabaseConfig sınıfındaki fieldlara 
karşılık gelir.

### get_sqlite_config()

SQLite veritabanı konfigrasyonu oluşturur. SQLite dosya tabanlı olduğu için sadece database adına ihtiyaç duyar.

```python
def get_sqlite_config(**database_kwargs) -> DatabaseConfig:
    return get_database_config(
        db_type=DatabaseType.SQLITE,
        db_name=database_kwargs.get('db_name', 'database.db')
    )
```

**Kullanım örnekleri:**
```python
# Default ayarlarla
config = get_sqlite_config()

# Özel database adı ile
config = get_sqlite_config(db_name='my_app')
```

### get_postgresql_config()

PostgreSQL veritabanı konfigrasyonu oluşturur. Network bağlantısı gerektirdiği için host, port, username ve password 
bilgileri alır.

```python  
def get_postgresql_config(**database_kwargs) -> DatabaseConfig:
    return get_database_config(
        db_type=DatabaseType.POSTGRESQL,
        db_name=database_kwargs.get('db_name', 'postgres'),
        host=database_kwargs.get('host', 'localhost'),
        port=database_kwargs.get('port', 5432),
        username=database_kwargs.get('username', 'postgres'),
        password=database_kwargs.get('password', '')
    )
```

**Kullanım örnekleri:**
```python
# Default ayarlarla localhost bağlantısı
config = get_postgresql_config()

# Production server için
config = get_postgresql_config(
    db_name='production_db',
    host='db.company.com', 
    username='app_user',
    password='secure_pass'
)
```

### get_mysql_config()

MySQL veritabanı konfigrasyonu oluşturur. PostgreSQL'e benzer şekilde network bağlantı bilgileri gerektirir.

```python
def get_mysql_config(**database_kwargs) -> DatabaseConfig:
    return get_database_config(
        db_type=DatabaseType.MYSQL,
        db_name=database_kwargs.get('db_name', 'mysql'),
        host=database_kwargs.get('host', 'localhost'),
        port=database_kwargs.get('port', 3306),
        username=database_kwargs.get('username', 'root'),
        password=database_kwargs.get('password', '')
    )
```

**Kullanım örnekleri:**
```python
# Local development için
config = get_mysql_config()

# Web hosting provider için  
config = get_mysql_config(
    db_name='web_app_db',
    host='mysql.hosting.com',
    username='webapp_user', 
    password='hosting_pass'
)
```

## Ana get_database_config Fonksiyonu

Tüm factory fonksiyonları arka planda `get_database_config` fonksiyonunu kullanır. Bu fonksiyon iki adımda çalışır:

**Adım 1**: Engine konfigrasyonunu belirle. Eğer kullanıcı `custom_engine_config` parametresi vermişse onu kullan, aksi 
halde veritabanı türüne göre önceden tanımlanmış konfigrasyonu al.

**Adım 2**: DatabaseConfig instance oluştur ve tüm parametreleri ata.

```python
def get_database_config(
    db_name: str,
    db_type: DatabaseType,
    host: Optional[str] = None,
    port: Optional[int] = None, 
    username: Optional[str] = None,
    password: Optional[str] = None,
    custom_engine_config: Optional[EngineConfig] = None
) -> DatabaseConfig
```

Eğer desteklenmeyen database türü verilirse `KeyError` hatası fırlatılır.

## Kullanım Senaryoları

### Development Environment
Geliştirme ortamında SQLite kullanmak en pratik seçenektir. Kurulum gerektirmez ve hızlı çalışır.

```python
from miniflow.database_manager.configs import get_sqlite_config

# Development için basit config
dev_config = get_sqlite_config(db_name='development')
connection_string = dev_config.get_connection_string()
# Çıktı: sqlite:///development.db
```

### Production Environment  
Production ortamında PostgreSQL veya MySQL kullanılması önerilir. Güçlü transaction desteği ve yüksek performans sağlar.

```python
from miniflow.database_manager.configs import get_postgresql_config

# Production PostgreSQL config
prod_config = get_postgresql_config(
    db_name='production_app',
    host='db.production.com',
    port=5432,
    username='prod_user', 
    password='very_secure_password'
)
```

### Custom Engine Config
Özel ihtiyaçlar için custom engine konfigrasyonu oluşturulabilir.

```python
from miniflow.database_manager.configs import EngineConfig, get_database_config, DatabaseType

# Debug için özel config
debug_engine = EngineConfig(
    pool_size=5,
    echo=True,              # SQL sorgularını göster
    echo_pool=True          # Pool işlemlerini göster
)

# Custom config ile database config oluştur
debug_config = get_database_config(
    db_name='debug_db',
    db_type=DatabaseType.POSTGRESQL,
    host='localhost',
    username='debug_user',
    password='debug_pass',
    custom_engine_config=debug_engine
)
```

## Kısacası

Kullanıcı miniflow'un database manager modülü için config oluşturmak istediğinde yukarıda belirtilen 3 factory 
fonksiyonundan birini kullanması önerilir. Bu factory fonksiyonları kullanıcıdan gelen kwargs sözlüklerini uygun 
atamalar ile yerleştirerek config nesnesi oluşturur. Bunu arka planda tanımlanmış olan `get_database_config` fonksiyonu 
ile yapar.

Factory fonksiyonları kullanmak uzun parametreli config oluşturma işlemini basitleştirir ve her veritabanı türü için 
optimize edilmiş ayarları otomatik sağlar. Özel ihtiyaçlar için custom engine config de verilebilir ama çoğu durumda 
varsayılan ayarlar yeterlidir.