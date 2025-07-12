"""
DatabaseManager tarafında kullanılacak olan SqlAlchemy motor modülü
"""

from sqlalchemy import create_engine, Engine, text
from sqlalchemy.orm import sessionmaker, Session
from typing import Optional, Dict, Any
from contextlib import contextmanager

from .config import DatabaseConfig  


# VERITABANI BAĞLANTI TEST FONKSIYONU
# ==============================================================
# Her veritabanı için dinamik olarak SQL sorgusu oluşturan bir
# fonksyon. İlerinde motor tarafında kullanılacak. 

def test_database_connection(engine: Engine, db_type: str = "sqlite") -> bool:
    """
    Verilen engine ile veritabanı bağlantısını test eder.
    
    Args:
        engine: Test edilecek SQLAlchemy engine
        db_type: Veritabanı tipi ("sqlite", "postgresql", "mysql")
    
    Returns:
        bool: Bağlantı başarılı ise True, aksi takdirde False
    """
    print("[DB MANAGER] - Bağlantı sorgusuna başlanılıyor")
    try:
        with engine.connect() as conn:
            print("[DB MANAGER] - Dinamik sorgu oluşturuluyor")
            if db_type.lower() == 'postgresql':
                print("[DB MANAGER] - POSTGRE için oluşturuluyor")
                conn.execute(text("SELECT version()"))
            elif db_type.lower() == 'mysql':
                print("[DB MANAGER] - MYSQL için oluşturuluyor")
                conn.execute(text("SELECT VERSION()"))
            else: 
                print("[DB MANAGER] - SQLITE için oluşturuluyor")
                conn.execute(text("SELECT 1"))
        print("[DB MANAGER] - Bağlantı başarılı")
        return True
    except Exception as e:
        print(f"[DB MANAGER] - Bağlantı hatası: {e}")
        return False
    

# DATABASE MANAGER TARAFINDA KULLANILACAK ENGINE MODÜLÜ
# ==============================================================

class DatabaseEngine:
    """
    SQLAlchemy Engine ve Session yönetimi için ana sınıf.
    """

    def __init__(self, config: DatabaseConfig) -> None:
        # Temel instance parametreleri
        self.__config: DatabaseConfig = config  
        self.__engine: Optional[Engine] = None
        self.__session_factory: Optional[sessionmaker] = None  
        self.__connection_string: str = config.get_connection_string()
        self.__engine_config: dict = config.engine_config.to_dict()

        # Engine durumu
        self.is_alive: bool = False
    
    def start(self) -> None:
        """Engine'i başlatır ve session factory'sini oluşturur."""
        print("[DB MANAGER] - Engine başlatılıyor")
        try:
            self.__create_engine()
            self.__create_session_factory()
            self.is_alive = True
            print("[DB MANAGER] - Engine başarıyla başlatıldı")
        except Exception as e:
            print(f"[DB MANAGER] - Engine başlatma hatası: {e}")
            self.is_alive = False
            raise

    def stop(self) -> None:
        """Engine'i durdurur ve kaynaklarını temizler."""
        print("[DB MANAGER] - Engine durduruluyor")
        if self.__engine:
            self.__engine.dispose()
        
        self.__engine = None
        self.__session_factory = None
        self.is_alive = False
        print("[DB MANAGER] - Engine durduruldu")

    def __create_engine(self) -> None:
        """SQLAlchemy Engine'ini oluşturur."""
        self.__engine = create_engine(self.__connection_string, **self.__engine_config)

    def __create_session_factory(self) -> None:
        """Session factory'sini oluşturur."""
        self.__session_factory = sessionmaker(
            bind=self.__engine, 
            autocommit=self.__engine_config.get('autocommit', False),
            autoflush=self.__engine_config.get('autoflush', True),
            expire_on_commit=self.__engine_config.get('expire_on_commit', True)
        )

    @property
    def get_engine(self) -> Engine:
        """Engine nesnesini döndürür."""
        if not self.__engine:  
            raise RuntimeError("Engine henüz oluşturulmamış. Önce start() metodunu çağırın.")
        return self.__engine
    
    @property
    def get_session(self) -> Session: 
        """Yeni bir Session nesnesi döndürür."""
        if not self.__session_factory:  
            raise RuntimeError("Session factory henüz oluşturulmamış. Önce start() metodunu çağırın.")
        return self.__session_factory()

    @contextmanager
    def get_session_context(self):
        """
        Context manager ile session yönetimi.
        Otomatik olarak session'ı kapatır ve hata durumunda rollback yapar.
        """
        session = self.get_session
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def create_tables(self, base_metadata) -> None:
        """Tüm tabloları oluşturur."""
        if not self.is_alive:
            print("[DB MANAGER] - Engine henüz başlatılmamış.")
            print("[DB MANAGER] - Engine başlatılıyor.")
            self.start()

        try:
            base_metadata.create_all(bind=self.__engine)
            print("[DB MANAGER] - Tablolar başarıyla oluşturuldu")
        except Exception as e:
            print(f"[DB MANAGER] - Tablo oluşturma hatası: {e}")
            raise
        
    def drop_tables(self, base_metadata) -> None:
        """Tüm tabloları siler."""
        if not self.is_alive:
            print("[DB MANAGER] - Engine henüz başlatılmamış.")
            print("[DB MANAGER] - Engine başlatılıyor.")
            self.start()
            
        try:
            base_metadata.drop_all(bind=self.__engine)
            print("[DB MANAGER] - Tablolar başarıyla silindi")
        except Exception as e:
            print(f"[DB MANAGER] - Tablo silme hatası: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Veritabanı bağlantısını test eder."""
        if not self.is_alive:
            print("[DB MANAGER] - Engine henüz başlatılmamış.")
            print("[DB MANAGER] - Engine başlatılıyor.")
            self.start()

        success = test_database_connection(self.__engine, self.__config.db_type.value)
        return success

    def execute_raw_sql(self, sql: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Ham SQL sorgusu çalıştırır.
        
        Args:
            sql: Çalıştırılacak SQL sorgusu
            params: SQL parametreleri
        
        Returns:
            Sorgu sonucu
        """
        if not self.is_alive:
            raise RuntimeError("Engine henüz başlatılmamış.")
        
        try:
            with self.__engine.connect() as conn:
                result = conn.execute(text(sql), params or {})
                return result.fetchall()
        except Exception as e:
            print(f"[DB MANAGER] - SQL çalıştırma hatası: {e}")
            raise

    def get_connection_info(self) -> Dict[str, Any]:
        """Engine ve bağlantı bilgilerini döndürür."""
        return {
            'connection_string': self.__connection_string,
            'database_type': self.__config.db_type.value,
            'database_name': self.__config.db_name,
            'is_alive': self.is_alive,
            'engine_config': self.__engine_config
        }

    def __repr__(self) -> str:
        return f"DatabaseEngine(db_type={self.__config.db_type.value}, db_name={self.__config.db_name}, is_alive={self.is_alive})"
    

# ENGINE OLUŞTURMAK IÇIN UTILTY FONKSIYONLARI
# ==============================================================

def create_database_engine(config: DatabaseConfig) -> DatabaseEngine:
    """
    DatabaseEngine instance'ını oluşturur ve başlatır.
    
    Args:
        config: DatabaseConfig nesnesi
    
    Returns:
        DatabaseEngine: Başlatılmış engine nesnesi
    """
    db_engine = DatabaseEngine(config)
    db_engine.start()
    return db_engine