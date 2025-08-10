import logging
from sqlalchemy import create_engine, Engine, text
from sqlalchemy.orm import sessionmaker, Session
from typing import Optional, Dict, Any
from contextlib import contextmanager

from .config import DatabaseConfig

# Logger setup
logger = logging.getLogger('miniflow.database.engine')

# =========================================================================================== CONNECTION VERIFICATION ==
def verify_database_connection(engine: Engine, db_type: str = "sqlite") -> bool:
    """Database bağlantısını test eder ve sonuç döner"""
    logger.info("Database connection test starting")

    try:
        with engine.connect() as conn:
            logger.debug(f"Creating test query for {db_type}")

            if db_type.lower() == 'postgresql':
                logger.debug("Executing PostgreSQL version query")
                conn.execute(text("SELECT version()"))

            elif db_type.lower() == 'mysql':
                logger.debug("Executing MySQL version query")
                conn.execute(text("SELECT VERSION()"))

            else:
                logger.debug("Executing SQLite simple query")
                conn.execute(text("SELECT 1"))

        logger.info("Database connection test successful")
        return True

    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
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
        self.__engine_config: dict = config.engine_config.to_dict(config.db_type)

        self.is_alive: bool = False

        # Log engine creation
        logger.debug(f"DatabaseEngine initialized for {config.db_type.value} database: {config.db_name}")

    def start(self) -> None:
        """Database engine'i başlatır ve kullanıma hazır hale getirir"""
        logger.info("Starting database engine")

        try:
            self.__create_engine()

            self.__create_session_factory()

            self.is_alive = True
            logger.info("Database engine started successfully")

        except Exception as e:
            logger.error(f"Engine startup failed: {e}")
            self.is_alive = False
            raise

    def stop(self) -> None:
        """Database engine'i durdurur ve kaynakları temizler"""
        logger.info("Stopping database engine")

        if self.__engine:
            self.__engine.dispose()

        self.__engine = None
        self.__session_factory = None

        self.is_alive = False
        logger.info("Database engine stopped")

    def __create_engine(self) -> None:
        """SQLAlchemy Engine oluşturur"""
        self.__engine = create_engine(
            self.__connection_string,
            **self.__engine_config
        )

    def __create_session_factory(self) -> None:
        """Session factory oluşturur"""
        session_config = self.__config.engine_config.get_session_config()

        self.__session_factory = sessionmaker(
            bind=self.__engine,
            autocommit=session_config['autocommit'],
            autoflush=session_config['autoflush'],
            expire_on_commit=session_config['expire_on_commit']
        )

    @property
    def get_engine(self) -> Engine:
        """SQLAlchemy Engine instance'ını döner"""
        if not self.__engine:
            raise RuntimeError("Engine not initialized. Call start() method first.")
        return self.__engine

    @property
    def get_session(self) -> Session:
        """Yeni Session instance oluşturur ve döner"""
        if not self.__session_factory:
            raise RuntimeError("Session factory not initialized. Call start() method first.")
        return self.__session_factory()

    @contextmanager
    def get_session_context(self):
        """Otomatik commit/rollback ile session context manager sağlar"""
        session = self.__session_factory()
        logger.debug("Database session created")

        try:
            yield session

            session.commit()
            logger.debug("Database session committed")

        except Exception as e:
            session.rollback()
            logger.warning(f"Database session rolled back due to exception: {e}")
            raise

        finally:
            session.close()
            logger.debug("Database session closed")

    def create_tables(self, base_metadata) -> None:
        """Database'de tüm tabloları oluşturur"""
        if not self.is_alive:
            logger.info("Engine not started, starting now")
            self.start()

        try:
            base_metadata.create_all(bind=self.__engine)
            logger.info("Database tables created successfully")

        except Exception as e:
            logger.error(f"Table creation failed: {e}")
            raise

    def drop_tables(self, base_metadata) -> None:
        """Database'den tüm tabloları siler"""
        if not self.is_alive:
            logger.info("Engine not started, starting now")
            self.start()

        try:
            base_metadata.drop_all(bind=self.__engine)
            logger.info("Database tables dropped successfully")

        except Exception as e:
            logger.error(f"Table dropping failed: {e}")
            raise

    def test_connection(self) -> bool:
        """Database bağlantısını test eder"""
        if not self.is_alive:
            logger.info("Engine not started, starting now")
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
            logger.error(f"Raw SQL execution failed: {e}")
            raise

    def get_connection_info(self) -> Dict[str, Any]:
        """Engine ve database bilgilerini döner"""
        return {
            'connection_string': self.__connection_string,
            'database_type': self.__config.db_type.value,
            'database_name': self.__config.db_name,
            'is_alive': self.is_alive,
            'engine_config': self.__engine_config
        }

    def __repr__(self) -> str:
        """DatabaseEngine string gösterimini döner"""
        return (f"DatabaseEngine("
                f"db_type={self.__config.db_type.value}, "
                f"db_name={self.__config.db_name}, "
                f"is_alive={self.is_alive})")


# ================================================================================================== FACTORY FUNCTION ==
def create_database_engine(config: DatabaseConfig) -> DatabaseEngine:
    """DatabaseEngine factory fonksiyonu - hazır engine döner"""
    db_engine = DatabaseEngine(config)
    db_engine.start()
    return db_engine