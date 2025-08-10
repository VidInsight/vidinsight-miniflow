"""
DATABASE ENGINE MODULE
======================

Bu modül Miniflow sisteminin veritabanı bağlantı yönetimi için SQLAlchemy engine'ini
encapsulate eder ve session management, connection pooling ve transaction handling
için yüksek seviye interface sağlar.

MODÜL SORUMLULUKLARI:
====================
1. SQLAlchemy Engine Management - Engine oluşturma, başlatma, durdurma
2. Session Management - Session factory ve context manager
3. Connection Testing - Database bağlantı sağlık kontrolü
4. Transaction Management - Commit, rollback, context management
5. Raw SQL Execution - Direct SQL query execution

ENGINE LIFECYCLE:
================
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Created   │───▶│   Started   │───▶│   Running   │───▶│   Stopped   │
│             │    │             │    │             │    │             │
│ • Config    │    │ • Engine    │    │ • Sessions  │    │ • Disposed  │
│   loaded    │    │ • Session   │    │ • Queries   │    │ • Cleaned   │
│             │    │   factory   │    │ • Pooling   │    │             │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘

SESSION MANAGEMENT PATTERNS:
===========================
```python
# Pattern 1: Manual session management
engine = create_database_engine(config)
session = engine.get_session
try:
    # database operations
    session.commit()
finally:
    session.close()

# Pattern 2: Context manager (RECOMMENDED)
with engine.get_session_context() as session:
    # database operations
    # auto-commit and cleanup
```

CONNECTION POOLING:
==================
• SQLite: Single connection (pool_size=1)
• MySQL: Medium pool (pool_size=15, max_overflow=25)  
• PostgreSQL: Large pool (pool_size=20, max_overflow=30)

TRANSACTION ISOLATION:
=====================
• SQLite: Default isolation (file-based locks)
• MySQL: READ_COMMITTED (web app optimized)
• PostgreSQL: READ_COMMITTED (enterprise safe)
"""

from sqlalchemy import create_engine, Engine, text
from sqlalchemy.orm import sessionmaker, Session
from typing import Optional, Dict, Any
from contextlib import contextmanager

from .config import DatabaseConfig  

# =============================================================================
# DATABASE CONNECTION TESTING UTILITIES
# Farklı database türleri için bağlantı testi fonksiyonları
# =============================================================================

def test_database_connection(engine: Engine, db_type: str = "sqlite") -> bool:
    """
    SQLAlchemy engine ile database bağlantısını test eder
    
    Her database türü için uygun test query'si çalıştırır:
    - SQLite: SELECT 1 (basit test)
    - PostgreSQL: SELECT version() (server info)
    - MySQL: SELECT VERSION() (server version)
    
    ALGORITHM:
    1. Engine ile connection establish et
    2. Database türüne göre uygun test query seç
    3. Query'yi execute et
    4. Başarı/başarısızlık durumunu döndür
    
    Args:
        engine (Engine): Test edilecek SQLAlchemy engine
        db_type (str): Database türü ("sqlite", "postgresql", "mysql")
    
    Returns:
        bool: Bağlantı başarılı ise True, hata durumunda False
        
    Example:
        >>> engine = create_engine("sqlite:///test.db")
        >>> success = test_database_connection(engine, "sqlite")
        >>> print(f"Connection successful: {success}")
    """
    print("[DB ENGINE] - Database connection test starting")
    
    try:
        # Step 1: Engine ile connection oluştur
        with engine.connect() as conn:
            print(f"[DB ENGINE] - Creating test query for {db_type}")
            
            # Step 2: Database türüne göre test query seç ve çalıştır
            if db_type.lower() == 'postgresql':
                print("[DB ENGINE] - PostgreSQL version query executing")
                conn.execute(text("SELECT version()"))  # PostgreSQL server version
                
            elif db_type.lower() == 'mysql':
                print("[DB ENGINE] - MySQL version query executing")
                conn.execute(text("SELECT VERSION()"))  # MySQL server version
                
            else: 
                print("[DB ENGINE] - SQLite simple query executing")
                conn.execute(text("SELECT 1"))  # Simple SQLite test
                
        print("[DB ENGINE] - Database connection test successful")
        return True
        
    except Exception as e:
        print(f"[DB ENGINE] - Database connection test failed: {e}")
        return False

# =============================================================================
# DATABASE ENGINE CLASS
# Ana database engine yönetim sınıfı
# =============================================================================

class DatabaseEngine:
    """
    SQLAlchemy Engine ve Session management için merkezi sınıf
    
    Bu sınıf database bağlantı yaşam döngüsünü yönetir ve application
    koduna clean interface sağlar. Connection pooling, session management
    ve transaction handling otomatik olarak handle edilir.
    
    INSTANCE ATTRIBUTES:
    ===================
    • __config: DatabaseConfig instance (private)
    • __engine: SQLAlchemy Engine instance (private)
    • __session_factory: SessionMaker instance (private)
    • __connection_string: Database URL string (private)
    • __engine_config: Engine configuration dict (private)
    • is_alive: Engine durumu (public readonly)
    
    LIFECYCLE METHODS:
    ==================
    • __init__(): Instance oluşturma
    • start(): Engine ve session factory başlatma
    • stop(): Engine durdurma ve cleanup
    
    SESSION METHODS:
    ================
    • get_session: Manual session oluşturma
    • get_session_context(): Context manager ile otomatik session management
    
    UTILITY METHODS:
    ================
    • create_tables(): Schema oluşturma
    • drop_tables(): Schema silme
    • test_connection(): Bağlantı testi
    • execute_raw_sql(): Direct SQL execution
    """

    def __init__(self, config: DatabaseConfig) -> None:
        """
        DatabaseEngine instance oluşturur
        
        Instance oluşturulduğunda sadece konfigrasyon set edilir,
        actual database connection start() methodu çağrılana kadar oluşturulmaz.
        
        ALGORITHM:
        1. Configuration objelerini private attribute'lara ata
        2. Connection string'i generate et
        3. Engine config'i dictionary formatına çevir
        4. Engine durumunu False olarak işaretle
        
        Args:
            config (DatabaseConfig): Database konfigrasyon objesi
        """
        # Step 1: Core configuration assignment
        self.__config: DatabaseConfig = config                              # Database konfigrasyonu
        self.__engine: Optional[Engine] = None                             # SQLAlchemy engine (lazy init)
        self.__session_factory: Optional[sessionmaker] = None             # Session factory (lazy init)
        
        # Step 2: Derived configuration
        self.__connection_string: str = config.get_connection_string()     # Database URL string
        self.__engine_config: dict = config.engine_config.to_dict()       # Engine parameters dict

        # Step 3: Engine state tracking
        self.is_alive: bool = False                                        # Engine durumu flag
    
    def start(self) -> None:
        """
        Database engine'ini başlatır ve session factory oluşturur
        
        Bu method database bağlantısını establish eder ve subsequent
        session oluşturma işlemleri için gerekli infrastructure'ı hazırlar.
        
        ALGORITHM:
        1. SQLAlchemy engine oluştur
        2. Session factory oluştur
        3. Engine durumunu aktif olarak işaretle
        4. Hata durumunda cleanup yap ve exception propagate et
        
        Raises:
            Exception: Engine oluşturma veya session factory oluşturma hatası
        """
        print("[DB ENGINE] - Starting database engine")
        
        try:
            # Step 1: SQLAlchemy engine oluştur
            self.__create_engine()
            
            # Step 2: Session factory oluştur  
            self.__create_session_factory()
            
            # Step 3: Engine durumunu aktif işaretle
            self.is_alive = True
            print("[DB ENGINE] - Database engine started successfully")
            
        except Exception as e:
            # Step 4: Hata durumunda cleanup ve exception propagation
            print(f"[DB ENGINE] - Engine startup failed: {e}")
            self.is_alive = False
            raise

    def stop(self) -> None:
        """
        Database engine'ini gracefully durdurur ve resources'ları temizler
        
        Bu method active connections'ları kapatır, connection pool'u dispose eder
        ve memory'deki references'ları temizler.
        
        ALGORITHM:
        1. Engine'i dispose et (connection pool cleanup)
        2. Instance references'ları None'a set et
        3. Engine durumunu inactive olarak işaretle
        """
        print("[DB ENGINE] - Stopping database engine")
        
        # Step 1: Engine dispose (connection pool cleanup)
        if self.__engine:
            self.__engine.dispose()
        
        # Step 2: Instance references cleanup
        self.__engine = None
        self.__session_factory = None
        
        # Step 3: Engine state reset
        self.is_alive = False
        print("[DB ENGINE] - Database engine stopped")

    def __create_engine(self) -> None:
        """
        SQLAlchemy Engine instance oluşturur
        
        Private method - sadece start() tarafından çağrılır.
        Connection string ve engine config kullanarak SQLAlchemy engine oluşturur.
        """
        self.__engine = create_engine(
            self.__connection_string,     # Database URL
            **self.__engine_config        # Engine configuration (pooling, timeouts, etc.)
        )

    def __create_session_factory(self) -> None:
        """
        SQLAlchemy SessionMaker factory oluşturur
        
        Private method - sadece start() tarafından çağrılır.
        Engine'e bind edilmiş session factory oluşturur ve session-level
        configuration'ları apply eder.
        """
        self.__session_factory = sessionmaker(
            bind=self.__engine,                                                    # Engine binding
            autocommit=self.__engine_config.get('autocommit', False),            # Manual transaction control
            autoflush=self.__engine_config.get('autoflush', True),               # Automatic flush before queries
            expire_on_commit=self.__engine_config.get('expire_on_commit', True)  # Refresh objects after commit
        )

    @property
    def get_engine(self) -> Engine:
        """
        SQLAlchemy Engine instance'ını döndürür
        
        Bu property direct engine access gerektiğinde kullanılır.
        Örnek: custom query execution, metadata operations
        
        Returns:
            Engine: SQLAlchemy engine instance
            
        Raises:
            RuntimeError: Engine henüz start() edilmemiş ise
        """
        if not self.__engine:  
            raise RuntimeError("Engine not initialized. Call start() method first.")
        return self.__engine
    
    @property
    def get_session(self) -> Session: 
        """
        Yeni Session instance oluşturur ve döndürür
        
        Her çağrıda yeni session döndürür. Session lifecycle'ı manually
        manage edilmelidir (commit/rollback/close).
        
        Returns:
            Session: Yeni SQLAlchemy session instance
            
        Raises:
            RuntimeError: Session factory henüz oluşturulmamış ise
            
        Warning:
            Manual session management gerektirir. Context manager kullanımı önerilir.
        """
        if not self.__session_factory:  
            raise RuntimeError("Session factory not initialized. Call start() method first.")
        return self.__session_factory()

    @contextmanager
    def get_session_context(self):
        """
        Context manager ile otomatik session lifecycle management
        
        Bu method RECOMMENDED session usage pattern'idir. Session lifecycle
        otomatik olarak manage edilir:
        - Başarı durumunda: automatic commit
        - Hata durumunda: automatic rollback
        - Her durumda: automatic session close
        
        ALGORITHM:
        1. Yeni session oluştur
        2. Context block'u execute et
        3. Başarı durumunda commit
        4. Exception durumunda rollback
        5. Her durumda session'ı close et
        
        Yields:
            Session: Context içinde kullanılacak session
            
        Example:
            >>> with engine.get_session_context() as session:
            ...     user = session.query(User).first()
            ...     user.name = "Updated"
            ...     # Automatic commit here
        """
        # Step 1: Session oluştur
        session = self.get_session
        
        try:
            # Step 2: Context block'u kullanıcıya yield et
            yield session
            
            # Step 3: Başarı durumunda commit
            session.commit()
            
        except Exception:
            # Step 4: Exception durumunda rollback
            session.rollback()
            raise
            
        finally:
            # Step 5: Her durumda session cleanup
            session.close()
    
    def create_tables(self, base_metadata) -> None:
        """
        Database schema'da tüm tabloları oluşturur
        
        SQLAlchemy metadata kullanarak tüm model class'larının
        tablolarını database'de oluşturur. Existing table'lara
        dokunmaz (CREATE IF NOT EXISTS pattern).
        
        ALGORITHM:
        1. Engine durumunu kontrol et, gerekirse başlat
        2. Metadata.create_all() ile tüm tabloları oluştur
        3. Hata durumunda exception propagate et
        
        Args:
            base_metadata: SQLAlchemy MetaData instance (Base.metadata)
            
        Raises:
            Exception: Tablo oluşturma hatası
        """
        # Step 1: Engine durumu kontrolü
        if not self.is_alive:
            print("[DB ENGINE] - Engine not started, starting now")
            self.start()

        try:
            # Step 2: Tüm tabloları oluştur
            base_metadata.create_all(bind=self.__engine)
            print("[DB ENGINE] - Database tables created successfully")
            
        except Exception as e:
            # Step 3: Hata durumunda exception propagation
            print(f"[DB ENGINE] - Table creation failed: {e}")
            raise
        
    def drop_tables(self, base_metadata) -> None:
        """
        Database schema'dan tüm tabloları siler
        
        SQLAlchemy metadata kullanarak tüm model class'larının
        tablolarını database'den siler. DESTRUCTIVE operation!
        
        ALGORITHM:
        1. Engine durumunu kontrol et, gerekirse başlat
        2. Metadata.drop_all() ile tüm tabloları sil
        3. Hata durumunda exception propagate et
        
        Args:
            base_metadata: SQLAlchemy MetaData instance (Base.metadata)
            
        Raises:
            Exception: Tablo silme hatası
            
        Warning:
            Bu operation tüm data'yı siler! Production'da dikkatli kullan.
        """
        # Step 1: Engine durumu kontrolü
        if not self.is_alive:
            print("[DB ENGINE] - Engine not started, starting now")
            self.start()
            
        try:
            # Step 2: Tüm tabloları sil
            base_metadata.drop_all(bind=self.__engine)
            print("[DB ENGINE] - Database tables dropped successfully")
            
        except Exception as e:
            # Step 3: Hata durumunda exception propagation
            print(f"[DB ENGINE] - Table dropping failed: {e}")
            raise
    
    def test_connection(self) -> bool:
        """
        Database bağlantısını test eder
        
        Engine'in database'e successful connection yapabildiğini
        doğrulamak için test query çalıştırır.
        
        ALGORITHM:
        1. Engine durumunu kontrol et, gerekirse başlat
        2. Database türüne uygun test query çalıştır
        3. Başarı/başarısızlık durumunu döndür
        
        Returns:
            bool: Bağlantı başarılı ise True, aksi takdirde False
        """
        # Step 1: Engine durumu kontrolü
        if not self.is_alive:
            print("[DB ENGINE] - Engine not started, starting now")
            self.start()

        # Step 2: Bağlantı testi
        success = test_database_connection(self.__engine, self.__config.db_type.value)
        return success

    def execute_raw_sql(self, sql: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Ham SQL sorgusu çalıştırır
        
        SQLAlchemy ORM dışında direct SQL execution gerektiğinde
        kullanılır. Migration'lar, custom query'ler veya database-specific
        operation'lar için faydalıdır.
        
        ALGORITHM:
        1. Engine durumunu kontrol et
        2. Connection oluştur
        3. SQL'i text() ile wrap et ve execute et
        4. Sonuçları fetch et ve döndür
        5. Hata durumunda exception propagate et
        
        Args:
            sql (str): Çalıştırılacak SQL sorgusu
            params (Optional[Dict[str, Any]]): SQL parametreleri
        
        Returns:
            Any: Query sonuçları (fetchall() output)
            
        Raises:
            RuntimeError: Engine başlatılmamış ise
            Exception: SQL execution hatası
            
        Example:
            >>> result = engine.execute_raw_sql(
            ...     "SELECT COUNT(*) FROM users WHERE status = :status",
            ...     {"status": "active"}
            ... )
            >>> print(f"Active users: {result[0][0]}")
        """
        # Step 1: Engine durumu kontrolü
        if not self.is_alive:
            raise RuntimeError("Engine not initialized. Call start() method first.")
        
        try:
            # Step 2-4: Connection oluştur, SQL execute et, sonuçları fetch et
            with self.__engine.connect() as conn:
                result = conn.execute(text(sql), params or {})
                return result.fetchall()
                
        except Exception as e:
            # Step 5: Hata durumunda exception propagation
            print(f"[DB ENGINE] - Raw SQL execution failed: {e}")
            raise

    def get_connection_info(self) -> Dict[str, Any]:
        """
        Engine ve database bağlantı bilgilerini döndürür
        
        Debug, monitoring ve troubleshooting amaçlı engine durumu
        ve konfigrasyon bilgilerini structured format'ta döndürür.
        
        Returns:
            Dict[str, Any]: Connection ve engine bilgileri
            
        Example:
            >>> info = engine.get_connection_info()
            >>> print(f"Database: {info['database_type']}")
            >>> print(f"Status: {'Connected' if info['is_alive'] else 'Disconnected'}")
        """
        return {
            'connection_string': self.__connection_string,     # Database URL (şifre maskelenebilir)
            'database_type': self.__config.db_type.value,     # Database türü
            'database_name': self.__config.db_name,           # Database adı
            'is_alive': self.is_alive,                        # Engine durumu
            'engine_config': self.__engine_config             # Engine konfigrasyonu
        }

    def __repr__(self) -> str:
        """
        DatabaseEngine string representation
        
        Debug ve logging amaçlı readable string representation döndürür.
        
        Returns:
            str: DatabaseEngine string representation
        """
        return (f"DatabaseEngine("
                f"db_type={self.__config.db_type.value}, "
                f"db_name={self.__config.db_name}, "
                f"is_alive={self.is_alive})")

# =============================================================================
# ENGINE FACTORY FUNCTIONS
# DatabaseEngine instance oluşturma utility fonksiyonları
# =============================================================================

def create_database_engine(config: DatabaseConfig) -> DatabaseEngine:
    """
    DatabaseEngine factory fonksiyonu
    
    Configuration'dan DatabaseEngine oluşturur ve başlatır.
    Bu convenience function most common use case için one-liner sağlar.
    
    ALGORITHM:
    1. DatabaseEngine instance oluştur
    2. Engine'i start() et
    3. Ready-to-use engine döndür
    
    Args:
        config (DatabaseConfig): Database konfigrasyon objesi
    
    Returns:
        DatabaseEngine: Başlatılmış ve kullanıma hazır engine instance
        
    Raises:
        Exception: Engine başlatma hatası
        
    Example:
        >>> config = get_sqlite_config("myapp.db")
        >>> engine = create_database_engine(config)
        >>> # Engine ready to use
    """
    # Step 1: Engine instance oluştur
    db_engine = DatabaseEngine(config)
    
    # Step 2: Engine'i başlat
    db_engine.start()
    
    # Step 3: Ready-to-use engine döndür
    return db_engine