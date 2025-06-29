import threading
from typing import Optional, Dict, Any
from contextlib import contextmanager
from sqlalchemy.orm import sessionmaker, Session

from ..core.config import DatabaseConfig, DatabaseType
from ..exceptions import DatabaseConnectionError, DatabaseConfigError
from ..adapters import SqliteAdapter, MySQLAdapter, PostgreSQLAdapter


class DatabaseManager:
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.engine = None
        self.local_session = None
        self.__is_healthy = False
        self.__health_check_thread = None
        self.__shutdown_event = threading.Event()
        self.adapter = self.__get_adapter()

    def __get_adapter(self):
        adapters = {
            DatabaseType.SQLITE: SqliteAdapter,
            DatabaseType.MYSQL: MySQLAdapter,
            DatabaseType.MARIADB: MySQLAdapter,
            DatabaseType.POSTGRESQL: PostgreSQLAdapter
        }

        adapter_class = adapters.get(self.config.db_type)

        if not adapter_class:
            raise DatabaseConfigError(f"Desteklenmeyen veritabanı: {self.config.db_type}")
        
        return adapter_class(self.config)

    def __apply_database_optimizations(self):
        try:
            if hasattr(self.adapter, 'enable_wal_mode'):
                self.adapter.enable_wal_mode()
            elif hasattr(self.adapter, 'optimize_mysql_settings'):
                self.adapter.optimize_mysql_settings()
            elif hasattr(self.adapter, 'optimize_postgresql_settings'):
                self.adapter.optimize_postgresql_settings()
        except Exception as e:
            print(f"⚠️ Optimizasyon uygulanamadı: {e}")

    def __start_health_check(self):
        if self.config.health_check_interval > 0:
            self.__health_check_thread = threading.Thread(
                target=self.__health_check_loop,
                name="DatabaseHealthCheck",
                daemon=True
            )
            self.__health_check_thread.start()

    def __health_check_loop(self):
        while not self.__shutdown_event.is_set():
            try:
                self.__is_healthy = self.adapter.validate_connection()
                if not self.__is_healthy:
                    print("Veritabanı bağlantısı sağlıksız!")
            except Exception as e:
                print(f"Health check hatası: {e}")
                self.__is_healthy = False

            self.__shutdown_event.wait(self.config.health_check_interval)

    def is_healthy(self):
        return self.__is_healthy

    def shutdown(self):
        print("Database manager kapatılıyor...")

        self.__shutdown_event.set()
        if self.__health_check_thread:
            self.__health_check_thread.join(timeout=5)

        if self.engine:
            self.engine.dispose()

        self.__is_healthy = False
        print("Database manager kapatıldı")

    @contextmanager
    def get_session(self):
        if not self.local_session:
            raise DatabaseConnectionError("Database manager başlatılmamış")

        session = self.local_session()

        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def get_session_raw(self):
        if not self.local_session:
            raise DatabaseConnectionError("Database manager başlatılmamış")
        return self.local_session()
    
    def initialize(self):
        try: 
            self.engine = self.adapter.create_engine()

            self.local_session = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )

            if not self.adapter.validate_connection():
                raise DatabaseConnectionError("Veritabanı bağlantısı başarısız")
           
            self.__apply_database_optimizations()
            self.__start_health_check()
            self.__is_healthy = True
            return True
        except Exception as e:
            print(f"Veritabanı başlatma hatası: {e}")
            return False


_db_manager = None

def get_database_manager():
    global _db_manager
    if _db_manager is None:
        raise DatabaseConnectionError("Database manager başlatılmamış")
    return _db_manager

def set_database_manager(config):
    global _db_manager
    _db_manager = DatabaseManager(config)
    if not _db_manager.initialize():
        raise DatabaseConnectionError("Database manager başlatılamadı")
    return _db_manager