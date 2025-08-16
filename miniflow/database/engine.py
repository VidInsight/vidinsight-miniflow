import time
import threading
from contextlib import contextmanager
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine, Engine, text
from sqlalchemy.exc import DisconnectionError, OperationalError, SQLAlchemyError
from sqlalchemy.pool import QueuePool

from .config import DatabaseConfig
from .models import Base

# =========================================================================================== ENGINE METRICS ==
@dataclass
class EngineMetrics:
    """Database engine performance ve health metrikleri"""
    
    # Session Metrics
    active_sessions: int = 0
    total_sessions_created: int = 0
    total_sessions_closed: int = 0
    
    # Performance Metrics
    connection_errors: int = 0
    query_count: int = 0
    last_health_check: Optional[float] = None
    health_check_failures: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Metrikleri dictionary olarak döner"""
        return {
            'active_sessions': self.active_sessions,
            'total_sessions_created': self.total_sessions_created,
            'total_sessions_closed': self.total_sessions_closed,
            'connection_errors': self.connection_errors,
            'query_count': self.query_count,
            'last_health_check': self.last_health_check,
            'health_check_failures': self.health_check_failures,
        }


# =========================================================================================== CONNECTION VERIFICATION ==
def verify_database_connection(engine: Engine, db_type: str = "sqlite") -> bool:
    """Database bağlantısını test eder ve sonuç döner"""
    try:
        with engine.connect() as conn:
            if db_type.lower() == 'postgresql':
                conn.execute(text("SELECT version()"))
            elif db_type.lower() == 'mysql':
                conn.execute(text("SELECT VERSION()"))
            else:
                conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        return False


# =================================================================================================== DATABASE ENGINE ==
class DatabaseEngine:
    """SQLAlchemy Engine ve Session yönetimi için ana sınıf"""

    def __init__(self, config: DatabaseConfig) -> None:
        """Engine instance'ı oluşturur ve konfigrasyon ayarlar"""
        self.__config: DatabaseConfig = config
        self.__engine: Optional[Engine] = None
        self.__session_factory: Optional[sessionmaker] = None

        self.__connection_string: str = config.get_connection_string()
        self.__engine_config: dict = config.engine_config.to_dict()

        # State management
        self.is_alive: bool = False
        self._lock = threading.RLock()  # Thread-safe operations için
        
        # Metrics and monitoring
        self.__metrics = EngineMetrics()
        self.__active_sessions: List[Session] = []
        self.__session_lock = threading.Lock()

    def start(self) -> None:
        """Database engine'i başlatır ve kullanıma hazır hale getirir"""
        with self._lock:
            if self.is_alive:
                return
            
            try:
                self.__create_engine()
                self.__create_session_factory()
                self.is_alive = True
                self.__metrics.last_health_check = time.time()
                
            except Exception as e:
                self.is_alive = False
                self.__cleanup_resources()
                raise

    def stop(self) -> None:
        """Database engine'i durdurur ve kaynakları temizler"""
        with self._lock:
            if not self.is_alive:
                return
            
            try:
                # Graceful shutdown of active sessions
                self.__close_active_sessions()
                
                # Dispose engine
                if self.__engine:
                    self.__engine.dispose()
                
                self.__cleanup_resources()
                self.is_alive = False
                
            except Exception as e:
                raise

    def __create_engine(self) -> None:
        """SQLAlchemy Engine oluşturur ve connection pooling ayarlar"""
        try:
            # Connection pool ayarları ile engine oluştur
            self.__engine = create_engine(
                self.__connection_string,
                poolclass=QueuePool,  # Explicit pool class
                **self.__engine_config
            )
            
        except Exception as e:
            raise

    def __create_session_factory(self) -> None:
        """Session factory oluşturur"""
        try:
            session_config = self.__config.engine_config.get_session_config()
            
            # Transaction isolation level'ı config'den al
            session_kwargs = {
                'bind': self.__engine,
                'autocommit': session_config['autocommit'],
                'autoflush': session_config['autoflush'],
                'expire_on_commit': session_config['expire_on_commit']
            }
            
            # Isolation level config'de varsa ekle
            if self.__config.engine_config.isolation_level:
                session_kwargs['bind'] = self.__engine.execution_options(
                    isolation_level=self.__config.engine_config.isolation_level
                )
            
            self.__session_factory = sessionmaker(**session_kwargs)
            
        except Exception as e:
            raise

    def __close_active_sessions(self) -> None:
        """Aktif session'ları graceful olarak kapatır"""
        with self.__session_lock:
            if not self.__active_sessions:
                return
            
            for session in self.__active_sessions.copy():
                try:
                    if session.is_active:
                        session.rollback()
                    session.close()
                except Exception as e:
                    pass  # Session kapatma hatalarını sessizce geç
            
            self.__active_sessions.clear()

    def __cleanup_resources(self) -> None:
        """Tüm kaynakları temizler"""
        self.__engine = None
        self.__session_factory = None
        self.__active_sessions.clear()
        
        # Reset metrics
        self.__metrics = EngineMetrics()

    @property
    def get_engine(self) -> Engine:
        """SQLAlchemy Engine instance'ını döner"""
        if not self.__engine:
            raise RuntimeError("Engine not initialized. Call start() method first.")
        return self.__engine

    @property
    def get_session(self) -> Session:
        """
        Yeni Session instance oluşturur ve döner
        
        Warning: Bu metod session lifecycle'ını caller'a bırakır.
        Production kodda get_session_context() kullanılması önerilir.
        """
        if not self.__session_factory or not self.is_alive:
            raise RuntimeError("Session factory not initialized. Call start() method first.")
        
        session = self.__session_factory()
        
        # Session tracking
        with self.__session_lock:
            self.__active_sessions.append(session)
            self.__metrics.total_sessions_created += 1
            self.__metrics.active_sessions = len(self.__active_sessions)
        
        return session

    @contextmanager
    def get_session_context(self, auto_commit: bool = True):
        """
        Otomatik commit/rollback ile session context manager sağlar
        
        Args:
            auto_commit: True ise otomatik commit, False ise manuel control
        """
        if not self.__session_factory or not self.is_alive:
            raise RuntimeError("Session factory not initialized. Call start() method first.")
        
        session = self.__session_factory()
        
        # Session tracking
        with self.__session_lock:
            self.__active_sessions.append(session)
            self.__metrics.total_sessions_created += 1
            self.__metrics.active_sessions = len(self.__active_sessions)
        
        try:
            yield session
            
            if auto_commit:
                session.commit()
                
        except Exception as e:
            session.rollback()
            raise
            
        finally:
            try:
                session.close()
            except Exception as e:
                pass  # Session kapatma hatalarını sessizce geç
            finally:
                # Session tracking cleanup
                with self.__session_lock:
                    if session in self.__active_sessions:
                        self.__active_sessions.remove(session)
                    self.__metrics.total_sessions_closed += 1
                    self.__metrics.active_sessions = len(self.__active_sessions)

    def create_tables(self, base_metadata) -> None:
        """Database'de tüm tabloları oluşturur"""
        if not self.is_alive:
            self.start()
        try:
            base_metadata.create_all(bind=self.__engine)
        except Exception as e:
            raise

    def drop_tables(self, base_metadata) -> None:
        """Database'den tüm tabloları siler"""
        if not self.is_alive:
            self.start()

        try:
            base_metadata.drop_all(bind=self.__engine)
        except Exception as e:
            raise

    def test_connection(self) -> bool:
        """Database bağlantısını test eder"""
        if not self.is_alive:
            self.start()

        success = verify_database_connection(self.__engine, self.__config.db_type.value)
        return success

    def execute_raw_sql(self, sql: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Ham SQL sorgusu çalıştırır ve sonucu döner"""
        if not self.is_alive:
            raise RuntimeError("Engine not initialized. Call start() method first.")

        try:
            with self.__engine.connect() as conn:
                result = conn.execute(text(sql), params or {})
                return result.fetchall()

        except Exception as e:
            raise

    def get_connection_info(self) -> Dict[str, Any]:
        """Engine ve database bilgilerini döner"""
        return {
            'connection_string': self.__connection_string,
            'database_type': self.__config.db_type.value,
            'database_name': self.__config.db_name,
            'is_alive': self.is_alive,
            'engine_config': self.__engine_config,
            'metrics': self.__metrics.to_dict(),
        }

    def get_metrics(self) -> EngineMetrics:
        """Güncel engine metriklerini döner"""
        return self.__metrics

    def health_check(self) -> Dict[str, Any]:
        """
        Comprehensive health check - connection, pool durumu ve metrics
        
        Returns:
            Dict[str, Any]: Health check sonuçları
        """
        current_time = time.time()
        health_status = {
            'is_alive': self.is_alive,
            'timestamp': current_time,
            'connection_healthy': False,
            'metrics': self.__metrics.to_dict()
        }
        
        if not self.is_alive:
            health_status['error'] = 'Engine not running'
            return health_status
        
        try:
            # Connection test
            health_status['connection_healthy'] = verify_database_connection(
                self.__engine, self.__config.db_type.value
            )
            
            self.__metrics.last_health_check = current_time
            
            if not health_status['connection_healthy']:
                self.__metrics.health_check_failures += 1
            
        except Exception as e:
            health_status['error'] = str(e)
            self.__metrics.health_check_failures += 1
        
        return health_status

    def __repr__(self) -> str:
        """DatabaseEngine string gösterimini döner"""
        return (f"DatabaseEngine("
                f"db_type={self.__config.db_type.value}, "
                f"db_name={self.__config.db_name}, "
                f"is_alive={self.is_alive}, "
                f"active_sessions={self.__metrics.active_sessions})")


# ================================================================================================== FACTORY FUNCTION ==
def create_database_engine(config: DatabaseConfig, auto_start: bool = True) -> DatabaseEngine:
    """
    DatabaseEngine factory fonksiyonu
    
    Args:
        config: Database konfigrasyonu
        auto_start: True ise engine otomatik başlatılır
    
    Returns:
        DatabaseEngine: Konfigüre edilmiş engine instance
    """
    try:
        db_engine = DatabaseEngine(config)
        
        if auto_start:
            db_engine.start()
        
        return db_engine
        
    except Exception as e:
        raise


# ================================================================================================== HEALTH CHECK FUNCTION ==
def perform_engine_health_check(engine: DatabaseEngine) -> Dict[str, Any]:
    """
    Standalone engine health check fonksiyonu
    
    Args:
        engine: DatabaseEngine instance
    
    Returns:
        Dict[str, Any]: Health check sonuçları
    """
    try:
        return engine.health_check()
    except Exception as e:
        return {
            'is_alive': False,
            'error': str(e),
            'timestamp': time.time()
        }