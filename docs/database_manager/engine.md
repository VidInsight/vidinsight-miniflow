# Miniflow Database Manager - Engine Dokümantasyonu

## Giriş

Miniflow Database Manager Engine modülü SQLAlchemy engine ve session yönetimi için merkezi bir wrapper sağlar. Bu modül database bağlantılarının kurulması, yönetilmesi ve yaşam döngüsünün kontrolü için kullanılır. Engine modülü connection pooling, session factory, transaction yönetimi ve database operasyonları için tek bir interface sunar. Ayrıca logging entegrasyonu ile tüm database işlemleri izlenebilir ve debug edilebilir.

## Ana Bileşenler

Engine modülü 3 ana bileşenden oluşur:
- **verify_database_connection()**: Database bağlantısını test eden utility fonksiyon
- **DatabaseEngine**: SQLAlchemy engine ve session yönetimi için ana sınıf
- **create_database_engine()**: Engine oluşturmak için factory fonksiyon

## verify_database_connection Fonksiyonu

Database bağlantısının sağlıklı olup olmadığını test eden utility fonksiyon.

```python
def verify_database_connection(engine: Engine, db_type: str = "sqlite") -> bool:
    """Database bağlantısını test eder ve sonuç döner"""
```

### Parametreler
- **engine**: Test edilecek SQLAlchemy Engine instance
- **db_type**: Database türü ("sqlite", "postgresql", "mysql") - default: "sqlite"

### Çalışma Mantığı

Fonksiyon database türüne göre farklı test sorguları çalıştırır:

```python
# PostgreSQL için
if db_type.lower() == 'postgresql':
    conn.execute(text("SELECT version()"))

# MySQL için  
elif db_type.lower() == 'mysql':
    conn.execute(text("SELECT VERSION()"))

# SQLite için (default)
else:
    conn.execute(text("SELECT 1"))
```

### Dönüş Değeri
- **True**: Bağlantı başarılı
- **False**: Bağlantı başarısız (exception yakalandı)

### Logging
- **INFO**: Bağlantı testi başlatılması ve sonucu
- **DEBUG**: Hangi database türü için hangi sorgunun çalıştırıldığı
- **ERROR**: Hata durumunda detaylı hata mesajı

## DatabaseEngine Sınıfı

SQLAlchemy Engine ve Session yönetimi için ana sınıf. Bu sınıf database bağlantılarının tüm yaşam döngüsünü yönetir.

```python
class DatabaseEngine:
    """SQLAlchemy Engine ve Session yönetimi için ana sınıf"""
```

### Constructor

```python
def __init__(self, config: DatabaseConfig) -> None:
    """Engine instance'ı oluşturur ve konfigrasyon ayarlar"""
```

**Parametre:**
- **config**: DatabaseConfig instance - bağlantı ve engine ayarları

**İç Durum:**
- `__config`: DatabaseConfig referansı
- `__engine`: SQLAlchemy Engine instance (None ile başlar)
- `__session_factory`: SessionMaker instance (None ile başlar)
- `__connection_string`: Database connection string
- `__engine_config`: Engine parametreleri dictionary
- `is_alive`: Engine durumu (Boolean)

### Yaşam Döngüsü Metodları

#### start()

Engine'i başlatır ve kullanıma hazır hale getirir.

```python
def start(self) -> None:
    """Database engine'i başlatır ve kullanıma hazır hale getirir"""
```

**İşlem Adımları:**
1. `__create_engine()` - SQLAlchemy Engine oluşturur
2. `__create_session_factory()` - Session factory oluşturur  
3. `is_alive = True` - Durumu aktif yapar

**Hata Yönetimi:**
- Exception durumunda `is_alive = False` yapar
- Hatayı re-raise eder

#### stop()

Engine'i durdurur ve kaynakları temizler.

```python
def stop(self) -> None:
    """Database engine'i durdurur ve kaynakları temizler"""
```

**İşlem Adımları:**
1. Engine dispose (connection pool temizliği)
2. Internal referansları None yapar
3. `is_alive = False` yapar

### Private Metodlar

#### __create_engine()

SQLAlchemy Engine instance oluşturur.

```python
def __create_engine(self) -> None:
    """SQLAlchemy Engine oluşturur"""
    self.__engine = create_engine(
        self.__connection_string,
        **self.__engine_config
    )
```

Engine config'ten gelen parametreler:
- **pool_size**: Connection pool boyutu
- **max_overflow**: Extra connection sayısı
- **pool_timeout**: Connection timeout süresi
- **pool_recycle**: Connection yenileme süresi
- **pool_pre_ping**: Bağlantı öncesi ping kontrolü
- **echo**: SQL sorgularını konsola yazdır
- **echo_pool**: Pool işlemlerini göster
- **isolation_level**: Transaction isolation seviyesi
- **connect_args**: Database-specific parametreler

#### __create_session_factory()

SessionMaker factory oluşturur.

```python
def __create_session_factory(self) -> None:
    """Session factory oluşturur"""
    session_config = self.__config.engine_config.get_session_config()
    
    self.__session_factory = sessionmaker(
        bind=self.__engine,
        autocommit=session_config['autocommit'],
        autoflush=session_config['autoflush'],
        expire_on_commit=session_config['expire_on_commit']
    )
```

Session config parametreleri:
- **autocommit**: Otomatik commit (default: False)
- **autoflush**: Otomatik flush (default: True)
- **expire_on_commit**: Commit sonrası objeleri expire et (default: True)

### Property Metodları

#### get_engine

SQLAlchemy Engine instance'ını döner.

```python
@property
def get_engine(self) -> Engine:
    """SQLAlchemy Engine instance'ını döner"""
```

**Güvenlik Kontrolü:**
```python
if not self.__engine:  
    raise RuntimeError("Engine not initialized. Call start() method first.")
```

#### get_session

Yeni Session instance oluşturur ve döner.

```python
@property  
def get_session(self) -> Session:
    """Yeni Session instance oluşturur ve döner"""
```

**Güvenlik Kontrolü:**
```python
if not self.__session_factory:  
    raise RuntimeError("Session factory not initialized. Call start() method first.")
```

**Not**: Her çağrı için yeni session oluşturur.

### Context Manager

#### get_session_context()

Otomatik commit/rollback ile session context manager sağlar.

```python
@contextmanager
def get_session_context(self):
    """Otomatik commit/rollback ile session context manager sağlar"""
```

**Kullanım:**
```python
with engine.get_session_context() as session:
    # Database işlemleri
    session.add(model_instance)
    # Otomatik commit
```

**İşlem Akışı:**
1. **Session oluştur**: `session = self.__session_factory()`
2. **Yield session**: Context'e session ver
3. **Başarı durumunda**: `session.commit()`
4. **Hata durumunda**: `session.rollback()`
5. **Her durumda**: `session.close()`

**Logging:**
- Session oluşturma: DEBUG level
- Commit: DEBUG level  
- Rollback: WARNING level (exception ile birlikte)
- Close: DEBUG level

### Table Operasyonları

#### create_tables()

Database'de tüm tabloları oluşturur.

```python
def create_tables(self, base_metadata) -> None:
    """Database'de tüm tabloları oluşturur"""
```

**Parametre:**
- **base_metadata**: SQLAlchemy Base.metadata object

**Auto-start**: Engine başlatılmamışsa otomatik başlatır.

**İşlem:**
```python
base_metadata.create_all(bind=self.__engine)
```

#### drop_tables()

Database'den tüm tabloları siler.

```python
def drop_tables(self, base_metadata) -> None:
    """Database'den tüm tabloları siler"""
```

**Parametre:**
- **base_metadata**: SQLAlchemy Base.metadata object

**Auto-start**: Engine başlatılmamışsa otomatik başlatır.

**İşlem:**
```python
base_metadata.drop_all(bind=self.__engine)
```

### Utility Metodları

#### test_connection()

Database bağlantısını test eder.

```python
def test_connection(self) -> bool:
    """Database bağlantısını test eder"""
```

**Auto-start**: Engine başlatılmamışsa otomatik başlatır.

**Dönüş değeri**: `verify_database_connection()` sonucu

#### execute_raw_sql()

Ham SQL sorgusu çalıştırır ve sonucu döner.

```python
def execute_raw_sql(self, sql: str, params: Optional[Dict[str, Any]] = None) -> Any:
    """Ham SQL sorgusu çalıştırır ve sonucu döner"""
```

**Parametreler:**
- **sql**: Çalıştırılacak SQL sorgusu (text() ile wrap edilir)
- **params**: SQL parametreleri (optional)

**Güvenlik**: Engine başlatılmamışsa RuntimeError fırlatır.

**Kullanım:**
```python
result = engine.execute_raw_sql(
    "SELECT * FROM users WHERE age > :min_age", 
    {"min_age": 18}
)
```

#### get_connection_info()

Engine ve database bilgilerini döner.

```python
def get_connection_info(self) -> Dict[str, Any]:
    """Engine ve database bilgilerini döner"""
```

**Dönüş değeri:**
```python
{
    'connection_string': self.__connection_string,
    'database_type': self.__config.db_type.value,
    'database_name': self.__config.db_name,
    'is_alive': self.is_alive,
    'engine_config': self.__engine_config
}
```

#### __repr__()

DatabaseEngine string gösterimini döner.

```python
def __repr__(self) -> str:
    """DatabaseEngine string gösterimini döner"""
```

**Format:**
```python
"DatabaseEngine(db_type=sqlite, db_name=test.db, is_alive=True)"
```

## create_database_engine Factory Fonksiyonu

DatabaseEngine oluşturmak ve başlatmak için factory fonksiyon.

```python
def create_database_engine(config: DatabaseConfig) -> DatabaseEngine:
    """DatabaseEngine factory fonksiyonu - hazır engine döner"""
```

**İşlem Adımları:**
1. `DatabaseEngine(config)` - Instance oluştur
2. `db_engine.start()` - Engine'i başlat
3. Hazır engine'i döner

**Avantaj**: Tek adımda engine oluşturma ve başlatma.

## Logging Entegrasyonu

Engine modülü `miniflow.database.engine` logger'ını kullanır:

```python
logger = logging.getLogger('miniflow.database.engine')
```

### Log Seviyeleri

#### DEBUG Level
- Engine initialization
- Database türüne göre test sorguları
- Session create/commit/close işlemleri

#### INFO Level  
- Engine start/stop işlemleri
- Connection test başlatma/sonuç
- Table create/drop işlemleri
- Auto-start durumları

#### WARNING Level
- Session rollback (exception ile birlikte)

#### ERROR Level
- Engine startup hataları
- Connection test hataları
- Table işlem hataları
- Raw SQL execution hataları

### Log Konfigrasyonu

`miniflow_logger.py` içinde tanımlı:

```python
"miniflow.database.engine": {
    "handlers": ["console", "file_main"], 
    "level": "DEBUG",
    "propagate": False,
}
```

## Kullanım Senaryoları

### Temel Engine Kullanımı

```python
from miniflow.database_manager.config import get_sqlite_config
from miniflow.database_manager.engine import DatabaseEngine

# Config oluştur
config = get_sqlite_config(db_name='my_app')

# Engine oluştur ve başlat
engine = DatabaseEngine(config)
engine.start()

# Bağlantı testi
if engine.test_connection():
    print("Database bağlantısı başarılı")

# Engine durdur
engine.stop()
```

### Factory Fonksiyon ile

```python
from miniflow.database_manager.engine import create_database_engine

# Tek adımda engine oluştur ve başlat
engine = create_database_engine(config)

# Hazır kullanım
info = engine.get_connection_info()
print(f"Database: {info['database_name']}")
```

### Session Context Manager

```python
# Transaction güvenli session kullanımı
with engine.get_session_context() as session:
    # Model oluştur
    user = User(name="John", age=30)
    session.add(user)
    
    # Başka işlemler...
    session.query(User).filter(User.age > 25).all()
    
    # Otomatik commit (exception yoksa)
    # Exception durumunda otomatik rollback
```

### Manual Session Yönetimi

```python
# Manuel session kontrolü
session = engine.get_session

try:
    # Database işlemleri
    users = session.query(User).all()
    
    # Manuel commit
    session.commit()
    
except Exception as e:
    # Manuel rollback
    session.rollback()
    raise
    
finally:
    # Manuel close
    session.close()
```

### Table Operasyonları

```python
from miniflow.database_manager.models import Base

# Tabloları oluştur
engine.create_tables(Base.metadata)

# Tabloları sil
engine.drop_tables(Base.metadata)
```

### Raw SQL Execution

```python
# Basit sorgu
result = engine.execute_raw_sql("SELECT COUNT(*) FROM users")
count = result[0][0]

# Parametreli sorgu
users = engine.execute_raw_sql(
    "SELECT * FROM users WHERE created_at > :date",
    {"date": "2024-01-01"}
)

# İstatistik sorgusu
stats = engine.execute_raw_sql("""
    SELECT 
        COUNT(*) as total_users,
        AVG(age) as avg_age,
        MAX(created_at) as last_registration
    FROM users
""")
```

### Production Environment

```python
from miniflow.database_manager.config import get_postgresql_config
from miniflow.utils.miniflow_logger import setup_logging

# Logging'i başlat
setup_logging()

# Production config
config = get_postgresql_config(
    db_name='production_app',
    host='db.company.com',
    username='app_user',
    password='secure_password'
)

# Production engine
engine = create_database_engine(config)

# Health check
if not engine.test_connection():
    raise RuntimeError("Production database connection failed")

# Connection info
info = engine.get_connection_info()
logger.info(f"Connected to {info['database_type']} database: {info['database_name']}")
```

### Error Handling

```python
try:
    # Engine başlatma
    engine = DatabaseEngine(config)
    engine.start()
    
except Exception as e:
    logger.error(f"Engine startup failed: {e}")
    raise

try:
    # Session işlemleri
    with engine.get_session_context() as session:
        # Risky operations
        session.execute(text("DROP TABLE important_data"))
        
except Exception as e:
    # Otomatik rollback yapıldı
    logger.error(f"Database operation failed: {e}")
    
finally:
    # Cleanup
    engine.stop()
```

## Performans Optimizasyonları

### Connection Pooling

Engine config ile connection pool optimizasyonu:

```python
from miniflow.database_manager.config import EngineConfig

# High-traffic application için
high_traffic_config = EngineConfig(
    pool_size=50,          # Büyük pool
    max_overflow=100,      # Yüksek overflow
    pool_timeout=60,       # Uzun timeout
    pool_recycle=7200,     # 2 saatte bir yenile
    pool_pre_ping=True     # Connection validation
)
```

### Session Yönetimi

```python
# Kısa session kullanımı (önerilen)
with engine.get_session_context() as session:
    result = session.query(User).filter(User.active == True).all()
    # Session otomatik kapanır

# Long-running session'dan kaçının
session = engine.get_session  # ❌ Memory leak riski
```

### Batch Operations

```python
# Batch insert optimizasyonu
with engine.get_session_context() as session:
    users = []
    for i in range(1000):
        users.append(User(name=f"User{i}", age=20+i%50))
    
    # Bulk insert
    session.bulk_save_objects(users)
    # Tek commit ile 1000 kayıt
```

## Error Recovery

### Auto-restart Pattern

```python
def safe_database_operation(engine, operation):
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            if not engine.is_alive:
                engine.start()
                
            return operation(engine)
            
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            
            if attempt < max_retries - 1:
                engine.stop()
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                raise
```

### Connection Validation

```python
def validate_and_repair_connection(engine):
    """Engine sağlığını kontrol et ve gerekirse onar"""
    
    # Durum kontrolü
    if not engine.is_alive:
        logger.info("Engine not alive, starting...")
        engine.start()
        return
    
    # Bağlantı testi
    if not engine.test_connection():
        logger.warning("Connection test failed, restarting engine...")
        engine.stop()
        engine.start()
        
        # Son test
        if not engine.test_connection():
            raise RuntimeError("Failed to restore database connection")
```

## Kısacası

Engine modülü miniflow'un database katmanının kalbidir. SQLAlchemy engine ve session'ları güvenli şekilde yönetir, connection pooling optimizasyonu sağlar ve transaction güvenliği için context manager kullanır. Logging entegrasyonu ile tüm database işlemleri izlenebilir, hata durumları takip edilebilir. Factory pattern ile kolay kullanım, property metodlarla güvenli erişim, utility metodlarla ek fonksiyonalite sunar. Auto-start özelliği kullanım kolaylığı sağlarken, comprehensive error handling production ortamında güvenilirlik kazandırır.