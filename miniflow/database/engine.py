import time
import threading
import logging
from contextlib import contextmanager
from typing import Optional, Dict, Any, Set, Callable
from dataclasses import dataclass, field
from functools import wraps
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine, Engine, text
from sqlalchemy.exc import DisconnectionError, OperationalError, SQLAlchemyError
from sqlalchemy.pool import QueuePool

from .config import DatabaseConfig
from .models import Base

# =========================================================================================== LOGGER SETUP ==
logger = logging.getLogger(__name__)


# =========================================================================================== CUSTOM EXCEPTIONS ==
class DatabaseEngineError(Exception):
    """Base exception for DatabaseEngine"""
    pass


class DatabaseConnectionError(DatabaseEngineError):
    """Connection related errors"""
    pass


class SessionError(DatabaseEngineError):
    """Session management errors"""
    pass


class ConfigurationError(DatabaseEngineError):
    """Configuration validation errors"""
    pass


# =========================================================================================== ENHANCED METRICS ==
@dataclass
class EngineMetrics:
    """Enhanced database engine performance ve health metrikleri"""

    # Session Metrics
    active_sessions: int = 0
    total_sessions_created: int = 0
    total_sessions_closed: int = 0

    # Performance Metrics
    connection_errors: int = 0
    query_count: int = 0
    retry_attempts: int = 0
    last_health_check: Optional[float] = None
    health_check_failures: int = 0

    # New metrics
    avg_session_duration: float = 0.0
    connection_timeouts: int = 0
    pool_exhaustion_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Metrikleri dictionary olarak döner"""
        return {
            'active_sessions': self.active_sessions,
            'total_sessions_created': self.total_sessions_created,
            'total_sessions_closed': self.total_sessions_closed,
            'connection_errors': self.connection_errors,
            'query_count': self.query_count,
            'retry_attempts': self.retry_attempts,
            'last_health_check': self.last_health_check,
            'health_check_failures': self.health_check_failures,
            'avg_session_duration': self.avg_session_duration,
            'connection_timeouts': self.connection_timeouts,
            'pool_exhaustion_count': self.pool_exhaustion_count,
        }


# =========================================================================================== DECORATORS ==
def require_alive_engine(func):
    """Engine'in çalışır durumda olmasını gerektiren methodlar için decorator"""

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self.is_alive:
            raise DatabaseEngineError("Engine not initialized. Call start() method first.")
        return func(self, *args, **kwargs)

    return wrapper


def auto_start_engine(func):
    """Engine'i otomatik başlatan decorator"""

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self.is_alive:
            logger.info("Auto-starting engine for operation")
            self.start()
        return func(self, *args, **kwargs)

    return wrapper


def retry_on_db_error(max_retries: int = 3, delay: float = 1.0, backoff_factor: float = 2.0):
    """Database hatalarında retry yapan decorator"""

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            last_exception = None

            for attempt in range(max_retries):
                try:
                    return func(self, *args, **kwargs)
                except (DisconnectionError, OperationalError) as e:
                    last_exception = e

                    # Safely update metrics if available
                    if hasattr(self, '_metrics'):
                        self._metrics.retry_attempts += 1

                    if attempt == max_retries - 1:
                        logger.error(f"Max retries ({max_retries}) exceeded for {func.__name__}")
                        break

                    wait_time = delay * (backoff_factor ** attempt)
                    logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}, retrying in {wait_time}s")
                    time.sleep(wait_time)
                except Exception as e:
                    # Non-retryable exceptions
                    logger.error(f"Non-retryable error in {func.__name__}: {e}")
                    raise

            raise DatabaseConnectionError(f"Failed after {max_retries} retries: {last_exception}")

        return wrapper

    return decorator


# =========================================================================================== CONNECTION VERIFICATION ==
def validate_database_connection(engine: Engine, db_type: str = "sqlite") -> bool:
    """Enhanced database bağlantı testi"""
    try:
        with engine.connect() as conn:
            # Database-specific health queries
            if db_type.lower() == 'postgresql':
                result = conn.execute(text("SELECT version(), current_timestamp"))
            elif db_type.lower() == 'mysql':
                result = conn.execute(text("SELECT VERSION(), NOW()"))
            else:
                result = conn.execute(text("SELECT 1, datetime('now')"))

            # Verify we can fetch results
            result.fetchone()
            return True

    except SQLAlchemyError as e:
        logger.warning(f"Database connection validation failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during connection validation: {e}")
        return False


# =================================================================================================== DATABASE ENGINE ==
class DatabaseEngine:
    """Enhanced SQLAlchemy Engine ve Session yönetimi için ana sınıf"""

    def __init__(self, config: DatabaseConfig) -> None:
        """Engine instance'ı oluşturur ve konfigrasyon ayarlar"""
        self._config = self._validate_config(config)
        self._engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None
        self._connection_string = config.get_connection_string()

        # Thread-safe state management
        self.is_alive = False
        self._lock = threading.RLock()
        self._session_lock = threading.Lock()

        # Enhanced metrics and monitoring
        self._metrics = EngineMetrics()
        self._active_sessions: Set[Session] = set()  # O(1) operations
        self._session_start_times: Dict[Session, float] = {}

        logger.info(f"DatabaseEngine initialized for {config.db_type.value}:{config.db_name}")

    def _validate_config(self, config: DatabaseConfig) -> DatabaseConfig:
        """Configuration validation"""
        if not config:
            raise ConfigurationError("Configuration cannot be None")

        if not config.db_name:
            raise ConfigurationError("Database name is required")

        if hasattr(config, 'engine_config') and config.engine_config:
            if hasattr(config.engine_config, 'pool_size') and config.engine_config.pool_size <= 0:
                raise ConfigurationError("Pool size must be positive")

        return config

    @contextmanager
    def _database_operation(self, operation_name: str):
        """Merkezi database operation handling"""
        start_time = time.time()
        try:
            logger.debug(f"Starting {operation_name}")
            yield
            logger.debug(f"Completed {operation_name} in {time.time() - start_time:.3f}s")

        except SQLAlchemyError as e:
            self._metrics.connection_errors += 1
            logger.error(f"Database error in {operation_name}: {e}")
            raise DatabaseConnectionError(f"{operation_name} failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in {operation_name}: {e}")
            raise DatabaseEngineError(f"{operation_name} failed: {e}")

    def _track_session(self, session: Session, action: str) -> None:
        """Merkezi session tracking"""
        with self._session_lock:
            current_time = time.time()

            if action == "create":
                self._active_sessions.add(session)
                self._session_start_times[session] = current_time
                self._metrics.total_sessions_created += 1
                logger.debug(f"Session created, total active: {len(self._active_sessions)}")

            elif action == "close":
                self._active_sessions.discard(session)  # Safe removal

                # Calculate session duration
                if session in self._session_start_times:
                    duration = current_time - self._session_start_times.pop(session)

                    # Update average session duration (before incrementing total_closed)
                    current_total = self._metrics.total_sessions_closed
                    if current_total == 0:
                        self._metrics.avg_session_duration = duration
                    else:
                        self._metrics.avg_session_duration = (
                                (self._metrics.avg_session_duration * current_total + duration) / (current_total + 1)
                        )

                self._metrics.total_sessions_closed += 1
                logger.debug(f"Session closed, total active: {len(self._active_sessions)}")

            self._metrics.active_sessions = len(self._active_sessions)

    def start(self) -> None:
        """Database engine'i başlatır ve kullanıma hazır hale getirir"""
        with self._lock:
            if self.is_alive:
                logger.warning("Engine is already running")
                return

            try:
                with self._database_operation("engine_start"):
                    self._create_engine()
                    self._create_session_factory()
                    self.is_alive = True
                    self._metrics.last_health_check = time.time()

                logger.info(f"Database engine started successfully: {self._config.db_type.value}")

            except Exception as e:
                logger.error(f"Failed to start engine: {e}")
                self.is_alive = False
                self._cleanup_resources()
                raise

    def stop(self) -> None:
        """Database engine'i durdurur ve kaynakları temizler"""
        with self._lock:
            if not self.is_alive:
                logger.warning("Engine is already stopped")
                return

            try:
                with self._database_operation("engine_stop"):
                    self._close_active_sessions()

                    if self._engine:
                        self._engine.dispose()

                    self._cleanup_resources()
                    self.is_alive = False

                logger.info("Database engine stopped successfully")

            except Exception as e:
                logger.error(f"Error during engine shutdown: {e}")
                raise

    def _create_engine(self) -> None:
        """SQLAlchemy Engine oluşturur"""
        engine_config = self._config.engine_config.to_dict()

        self._engine = create_engine(
            self._connection_string,
            poolclass=QueuePool,
            **engine_config
        )

        logger.debug(f"Engine created with config: {engine_config}")

    def _create_session_factory(self) -> None:
        """Session factory oluşturur"""
        session_config = self._config.engine_config.get_session_config()

        session_kwargs = {
            'bind': self._engine,
            'autocommit': session_config['autocommit'],
            'autoflush': session_config['autoflush'],
            'expire_on_commit': session_config['expire_on_commit']
        }

        # Isolation level handling
        if self._config.engine_config.isolation_level:
            session_kwargs['bind'] = self._engine.execution_options(
                isolation_level=self._config.engine_config.isolation_level
            )

        self._session_factory = sessionmaker(**session_kwargs)
        logger.debug("Session factory created")

    def _close_active_sessions(self) -> None:
        """Aktif session'ları graceful olarak kapatır"""
        if not self._active_sessions:
            return

        logger.info(f"Closing {len(self._active_sessions)} active sessions")

        for session in self._active_sessions.copy():
            self._close_session_safely(session)

    def _close_session_safely(self, session: Session) -> None:
        """Session'ı güvenli şekilde kapatır"""
        try:
            if session.is_active:
                session.rollback()
            session.close()
        except Exception as e:
            logger.warning(f"Error closing session: {e}")
        finally:
            self._track_session(session, "close")

    def _cleanup_resources(self) -> None:
        """Tüm kaynakları temizler"""
        self._engine = None
        self._session_factory = None
        self._active_sessions.clear()
        self._session_start_times.clear()

        # Reset metrics (keep historical data)
        self._metrics.active_sessions = 0

    @property
    @require_alive_engine
    def engine(self) -> Engine:
        """SQLAlchemy Engine instance'ını döner"""
        return self._engine

    @require_alive_engine
    def get_session(self) -> Session:
        """Yeni Session instance oluşturur ve döner"""
        with self._database_operation("create_session"):
            session = self._session_factory()
            self._track_session(session, "create")
            return session

    @contextmanager
    @require_alive_engine
    def session_context(self, auto_commit: bool = True):
        """Enhanced session context manager"""
        session = None
        try:
            # Create session
            with self._database_operation("create_session"):
                session = self._session_factory()
                self._track_session(session, "create")

            # Yield session for use
            yield session

            # Handle commit if needed
            if auto_commit and session.is_active:
                # Check if session has any pending changes
                if session.dirty or session.new or session.deleted:
                    session.commit()
                    logger.debug("Session auto-committed")

        except Exception as e:
            if session and session.is_active:
                try:
                    session.rollback()
                    logger.debug("Session rolled back due to error")
                except Exception as rollback_error:
                    logger.warning(f"Rollback failed: {rollback_error}")
            raise

        finally:
            if session:
                self._close_session_safely(session)

    @auto_start_engine
    def create_tables(self, base_metadata) -> None:
        """Database'de tüm tabloları oluşturur"""
        with self._database_operation("create_tables"):
            base_metadata.create_all(bind=self._engine)
            logger.info("Database tables created successfully")

    @auto_start_engine
    def drop_tables(self, base_metadata) -> None:
        """Database'den tüm tabloları siler"""
        with self._database_operation("drop_tables"):
            base_metadata.drop_all(bind=self._engine)
            logger.info("Database tables dropped successfully")

    @require_alive_engine
    @retry_on_db_error(max_retries=3)
    def test_connection(self) -> bool:
        """Enhanced database bağlantı testi"""
        success = validate_database_connection(self._engine, self._config.db_type.value)

        if success:
            logger.debug("Database connection test passed")
        else:
            logger.warning("Database connection test failed")

        return success

    @require_alive_engine
    @retry_on_db_error(max_retries=2)
    def execute_raw_sql(self, sql: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Enhanced raw SQL execution"""
        with self._database_operation("execute_raw_sql"):
            with self._engine.connect() as conn:
                result = conn.execute(text(sql), params or {})
                self._metrics.query_count += 1
                return result.fetchall()

    def get_connection_info(self) -> Dict[str, Any]:
        """Enhanced engine ve database bilgilerini döner"""
        pool_info = {}
        if self._engine and hasattr(self._engine, 'pool'):
            try:
                pool_info = {
                    'pool_size': self._engine.pool.size(),
                    'checked_in': self._engine.pool.checkedin(),
                    'checked_out': self._engine.pool.checkedout(),
                    'overflow': self._engine.pool.overflow(),
                }
            except Exception:
                pool_info = {'error': 'Pool info unavailable'}

        return {
            'database_type': self._config.db_type.value,
            'database_name': self._config.db_name,
            'is_alive': self.is_alive,
            'metrics': self._metrics.to_dict(),
            'pool_info': pool_info,
            'active_sessions_count': len(self._active_sessions),
        }

    def get_metrics(self) -> EngineMetrics:
        """Güncel engine metriklerini döner"""
        return self._metrics

    @require_alive_engine
    def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check"""
        current_time = time.time()
        health_status = {
            'is_alive': self.is_alive,
            'timestamp': current_time,
            'connection_healthy': False,
            'metrics': self._metrics.to_dict()
        }

        try:
            # Connection test with timeout
            health_status['connection_healthy'] = self.test_connection()
            self._metrics.last_health_check = current_time

            if not health_status['connection_healthy']:
                self._metrics.health_check_failures += 1

            logger.debug(f"Health check completed: {health_status['connection_healthy']}")

        except Exception as e:
            health_status['error'] = str(e)
            self._metrics.health_check_failures += 1
            logger.error(f"Health check failed: {e}")

        return health_status

    def __repr__(self) -> str:
        """Enhanced string representation"""
        return (f"DatabaseEngine("
                f"db_type={self._config.db_type.value}, "
                f"db_name={self._config.db_name}, "
                f"is_alive={self.is_alive}, "
                f"active_sessions={len(self._active_sessions)}, "
                f"total_created={self._metrics.total_sessions_created})")

    def __enter__(self):
        """Context manager entry"""
        if not self.is_alive:
            self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop()


# ================================================================================================== FACTORY FUNCTION ==
def create_database_engine(config: DatabaseConfig, auto_start: bool = True) -> DatabaseEngine:
    """Enhanced DatabaseEngine factory fonksiyonu"""
    try:
        logger.info(f"Creating database engine for {config.db_type.value}:{config.db_name}")
        db_engine = DatabaseEngine(config)

        if auto_start:
            db_engine.start()

        return db_engine

    except Exception as e:
        logger.error(f"Failed to create database engine: {e}")
        raise


# ================================================================================================== HEALTH CHECK FUNCTION ==
def perform_engine_health_check(engine: DatabaseEngine) -> Dict[str, Any]:
    """Enhanced standalone engine health check"""
    try:
        return engine.health_check()
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            'is_alive': False,
            'error': str(e),
            'timestamp': time.time()
        }