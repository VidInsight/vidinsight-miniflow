import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

# Utility
from .utils import setup_logging

# Exceptions
from .exceptions import MiniflowException, ErrorManager
from .exceptions import create_error_response, handle_unexpected_error
from .exceptions import (DatabaseError, SchedulerError, EngineError,
                         ValidationError, BusinessLogicError, ResourceError)

# Database
from .database import DatabaseConfig, DatabaseEngine, DatabaseOrchestration, Base
from .database import get_sqlite_config, get_mysql_config, get_postgresql_config
from .database import create_database_engine

# Parallelism Engine
from .parallelism_engine import Manager

# Scheduler
from .scheduler import MiniflowInputMonitor, MiniflowOutputMonitor

setup_logging()
logger = logging.getLogger(__name__)
logger.debug(f"Logger tanımları tanımlandı")


class MiniflowCore:
    def __init__(self, db_type: str, enable_scheduler: bool = True, **db_params):
        # Database
        self.db_type: str = db_type
        self.db_engine: DatabaseEngine = None
        self.orchestration: DatabaseOrchestration = None
        self.scripts_dir: Path = Path("scripts")
        self.db_config: DatabaseConfig = self.__create_config(db_type, **db_params)
        
        # Parallelism Engine
        self.execution_engine: Manager = None
        
        # Scheduler
        self.enable_scheduler: bool = enable_scheduler
        self.input_monitor: MiniflowInputMonitor = None
        self.output_monitor: MiniflowOutputMonitor = None
        
        logger.debug(f"MiniflowCore initialized with scheduler={'enabled' if enable_scheduler else 'disabled'}")

    @ErrorManager.operation_context("core_startup")
    def start(self) -> None:
        # 1. Database'i başlat
        self.__start_database_engine()
        
        # 2. Parallelism Engine'i başlat
        self.__start_parallelism_engine()
        
        # 3. Scheduler'ı başlat (isteğe bağlı)
        if self.enable_scheduler:
            self.__start_scheduler()
        
        logger.info(f"MiniflowCore started successfully (scheduler={'enabled' if self.enable_scheduler else 'disabled'})")

    @ErrorManager.operation_context("core_shutdown")
    def stop(self) -> None:
        # Reverse order shutdown: Scheduler -> Engine -> Database
        
        # 1. Scheduler'ı durdur
        if self.enable_scheduler:
            self.__stop_scheduler()
        
        # 2. Parallelism Engine'i durdur
        self.__stop_parallelism_engine()
        
        # 3. Database'i durdur
        self.__stop_database_engine()
        
        logger.info("MiniflowCore stopped successfully")

    # DATABASE MANAGER METOTLARI
    # ===========================================================

    @staticmethod
    def __create_config(db_type: str, **db_params):
        config_map = {
            "sqlite": lambda: get_sqlite_config(db_params.get("db_name", "test_database")),
            "postgresql": lambda: get_postgresql_config(
                db_name=db_params.get('db_name', 'workflow_db'),
                host=db_params.get('host', 'localhost'),
                port=db_params.get('port', 5432),
                username=db_params.get('username', 'postgres'),
                password=db_params.get('password', 'password')
            ),
            "mysql": lambda: get_mysql_config(
                db_name=db_params.get('db_name', 'workflow_db'),
                host=db_params.get('host', 'localhost'),
                port=db_params.get('port', 3306),
                username=db_params.get('username', 'root'),
                password=db_params.get('password', 'password')
            )
        }

        if db_type not in config_map:
            raise ValidationError(
                f"Unsupported database type: {db_type}",
                f"Supported types: {list(config_map.keys())}"
            )
        
        return config_map[db_type]()
        
    def __start_database_engine(self):
        try: 
            # 1. Engine oluştur
            self.db_engine = create_database_engine(config=self.db_config)

            # 2. Engine başlat
            self.db_engine.start()

            # 3. Tabloları oluştur
            self.db_engine.create_tables(Base.metadata)

            # 4. Orchestration başlat
            self.orchestration = DatabaseOrchestration()

            # 5. Scripts klasörünü oluştur
            self.scripts_dir.mkdir(exist_ok=True)
            logger.info("Database engine started successfully")

        except Exception as e:
            # Ensure cleanup on failure
            if self.db_engine:
                self.db_engine.stop()

            self.db_engine = None
            self.orchestration = None

            raise DatabaseError(
                "Failed to start database engine",
                f"Error during initialization: {str(e)}"
            )

    def __stop_database_engine(self):
        if self.db_engine:
            try:
                self.db_engine.stop()
            except Exception as e:
                logger.warning(f"Error stopping database engine: {e}")
            finally:
                self.db_engine = None
                self.orchestration = None

    def __start_parallelism_engine(self):
        """Start the parallelism engine for task execution"""
        try:
            self.execution_engine = Manager()
            self.execution_engine.start()
            logger.info("Parallelism engine started successfully")
            
        except Exception as e:
            # Cleanup on failure
            if self.execution_engine:
                try:
                    self.execution_engine.shutdown()
                except:
                    pass
                self.execution_engine = None
                
            raise EngineError(
                "Failed to start parallelism engine",
                f"Error during engine initialization: {str(e)}"
            )

    def __stop_parallelism_engine(self):
        """Stop the parallelism engine"""
        if self.execution_engine:
            try:
                self.execution_engine.shutdown()
                logger.info("Parallelism engine stopped successfully")
            except Exception as e:
                logger.warning(f"Error stopping parallelism engine: {e}")
            finally:
                self.execution_engine = None

    def __start_scheduler(self):
        """Start the input and output monitors"""
        try:
            # Validate dependencies
            if not self.db_engine or not self.orchestration:
                raise SchedulerError("Database engine must be started before scheduler")
            
            if not self.execution_engine:
                raise SchedulerError("Parallelism engine must be started before scheduler")
            
            # Start Input Monitor
            self.input_monitor = MiniflowInputMonitor(
                database_engine=self.db_engine,
                database_orchestration=self.orchestration,
                execution_engine=self.execution_engine,
                polling_interval=0.05,  # Faster polling for better responsiveness
                batch_size=100,         # Larger batch size for concurrent workflows
                worker_threads=8        # More worker threads for payload creation
            )
            self.input_monitor.start()
            
            # Start Output Monitor
            self.output_monitor = MiniflowOutputMonitor(
                database_engine=self.db_engine,
                database_orchestration=self.orchestration,
                execution_engine=self.execution_engine,
                polling_interval=0.5,
                batch_size=50,
                worker_threads=4
            )
            self.output_monitor.start()
            
            logger.info("Scheduler started successfully (Input & Output monitors running)")
            
        except Exception as e:
            # Cleanup on failure
            self.__stop_scheduler()
            raise SchedulerError(
                "Failed to start scheduler",
                f"Error during scheduler initialization: {str(e)}"
            )

    def __stop_scheduler(self):
        """Stop the input and output monitors"""
        # Stop monitors
        if self.input_monitor:
            try:
                self.input_monitor.stop()
                logger.info("Input monitor stopped successfully")
            except Exception as e:
                logger.warning(f"Error stopping input monitor: {e}")
            finally:
                self.input_monitor = None
        
        if self.output_monitor:
            try:
                self.output_monitor.stop()
                logger.info("Output monitor stopped successfully")
            except Exception as e:
                logger.warning(f"Error stopping output monitor: {e}")
            finally:
                self.output_monitor = None

    # CORE SYSTEM HEALTH CHECK
    # ===========================================================
    # All database operations now handled through Service layer
    # via app/services/ and orchestration layer

    def health_check(self) -> dict:
        """
        System health check - returns status of all components
        NOTE: For detailed business operations, use Service layer via FastAPI endpoints
        """
        try:
            components = {
                "database": {
                    "status": "healthy" if self.db_engine and self.db_engine.is_alive else "unhealthy",
                    "details": "Database engine running" if self.db_engine and self.db_engine.is_alive else "Database engine not running"
                },
                "parallelism_engine": {
                    "status": "healthy" if self.execution_engine and self.execution_engine.started else "unhealthy", 
                    "details": "Execution engine running" if self.execution_engine and self.execution_engine.started else "Execution engine not running"
                },
                "scheduler": {
                    "input_monitor": "healthy" if self.input_monitor and self.input_monitor.is_running() else "unhealthy",
                    "output_monitor": "healthy" if self.output_monitor and self.output_monitor.is_running() else "unhealthy"
                }
            }
            
            # Overall status
            all_healthy = (
                components["database"]["status"] == "healthy" and
                components["parallelism_engine"]["status"] == "healthy" and
                (not self.enable_scheduler or (
                    components["scheduler"]["input_monitor"] == "healthy" and
                    components["scheduler"]["output_monitor"] == "healthy"
                ))
            )
            
            return {
                "status": "healthy" if all_healthy else "unhealthy",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "components": components,
                "ready_tasks": self._get_ready_task_count() if all_healthy else -1,
                "note": "For business operations (scripts, workflows, executions), use FastAPI endpoints /api/v1/..."
            }
            
        except Exception as e:
            return {
                "status": "error",
                "timestamp": datetime.utcnow().isoformat() + "Z", 
                "error": str(e),
                "components": {}
            }

    def _get_ready_task_count(self) -> int:
        """Helper method to get count of ready tasks"""
        try:
            with self.db_engine.get_session_context() as session:
                return self.orchestration.execution_input_crud.count_ready_tasks(session)
        except:
            return -1

    # API SERVER METHODS
    # ===========================================================
    @ErrorManager.operation_context("api_server_startup")
    def start_api_server(self, host: str = "127.0.0.1", port: int = 8000, reload: bool = False) -> None:
        """
        Start the Miniflow API server
        
        NOTE: This method starts the FastAPI server. All business operations
        (scripts, workflows, nodes, edges, executions) should be done through
        the API endpoints, not through direct MiniflowCore methods.
        """
        try:
            import uvicorn
            from .app.main import app
            
            logger.info(f"Starting Miniflow API server on {host}:{port}")
            logger.info("🌐 API Documentation: http://127.0.0.1:8000/docs")
            logger.info("📊 Health Check: http://127.0.0.1:8000/health")
            logger.info("🔧 All business operations available via /api/v1/ endpoints")
            
            uvicorn.run(
                app=app,
                host=host,
                port=port,
                reload=reload,
                log_level="info"
            )
            
        except ImportError:
            raise EngineError(
                "uvicorn not installed",
                "Install uvicorn to run the API server: pip install uvicorn"
            )
        except Exception as e:
            logger.error(f"Failed to start API server: {e}")
            raise EngineError(f"API server startup failed: {str(e)}") from e
