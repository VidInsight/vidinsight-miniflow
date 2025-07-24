import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

# Utility
from .utils import setup_logging
from .utils import create_script, delete_script

# Exceptions
from .exceptions import MiniflowException, ErrorManager
from .exceptions import create_error_response, handle_unexpected_error
from .exceptions import (DatabaseError, SchedulerError, EngineError,
                         ValidationError, BusinessLogicError, ResourceError)

# Database
from .database_manager import DatabaseConfig, DatabaseEngine, DatabaseOrchestration, Base
from .database_manager import get_sqlite_config, get_mysql_config, get_postgresql_config
from .database_manager import create_database_engine

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

    # SCRIPT METOTLARI 
    # ===========================================================
    @ErrorManager.operation_context("script_creation")
    def script_create(self, script_data: dict, script_content: str) -> dict:
        # Validate inputs
        ErrorManager.validate_engine_state(self.db_engine)
        ErrorManager.validate_required_fields(script_data, ["name"], "script creation")

        if not script_content or not script_content.strip():
            raise ValidationError(
                "Script content cannot be empty",
                "Provide valid Python script content"
            )
            
        # 2. Dosya oluştur
        absolute_path = create_script(
            scripts_dir=self.scripts_dir,
            script_name=script_data.get("name"),
            script_extension="py",
            script_content=script_content
        )

        # 3. Veritabanı için payload oluştur
        payload = {
            'name': script_data['name'],
            'description': script_data.get('description'),
            'language': 'PYTHON',  # ScriptType.PYTHON enum value
            'input_params': script_data.get('input_params', {}),
            'output_params': script_data.get('output_params', {}),
            'script_path' : absolute_path
        }

        # 5. Veritabanı kaydı oluştur
        with self.db_engine.get_session_context() as session:
            result = self.orchestration.create_script(session, payload)
            session.flush()
            session.commit()
            
        # 6. Çıktıyı Döndür
        logger.info(f"Script created successfully: {script_data['name']}")
        return result
        
    @ErrorManager.operation_context("script_deletion")
    def script_delete(self, script_id: str) -> dict:
        # 0. Temel Kontroller
        ErrorManager.validate_engine_state(self.db_engine)

        if not script_id:
            raise ValidationError("Script ID is required", "Provide valid script ID")
        
        with self.db_engine.get_session_context() as session:
            result = self.orchestration.delete_script(session, script_id)

        return result

    @ErrorManager.operation_context("script_listing")
    def script_list(self) -> dict:
        # 0. Temel Kontroller
        ErrorManager.validate_engine_state(self.db_engine)

        with self.db_engine.get_session_context() as session:
            result =  self.orchestration.get_scripts(session)

        return result

    @ErrorManager.operation_context("script_retrieval")
    def script_get(self, script_id: str, include_content: bool = False) -> dict:
        ErrorManager.validate_engine_state(self.db_engine)
        
        if not script_id:
            raise ValidationError("Script ID is required", "Provide valid script ID")

        with self.db_engine.get_session_context() as session:
            result =  self.orchestration.get_script(session, script_id, include_content)

        return result

    # WORKFLOW METOTLARI 
    # ===========================================================
    @ErrorManager.operation_context("workflow_creation")
    def workflow_create(self, workflow_data: dict) -> dict:
        ErrorManager.validate_engine_state(self.db_engine)
        ErrorManager.validate_required_fields(workflow_data, ["name", "nodes"], "workflow creation")
        # Ensure edges exist even if empty
        if "edges" not in workflow_data:
            workflow_data["edges"] = []
        
        with self.db_engine.get_session_context() as session:
            result = self.orchestration.create_workflow(session, workflow_data)

        logger.info(f"Workflow '{workflow_data['name']}' created successfully")
        return result

    @ErrorManager.operation_context("workflow_deletion")
    def workflow_delete(self, workflow_id: str) -> dict:
        ErrorManager.validate_engine_state(self.db_engine)
        
        if not workflow_id:
            raise ValidationError("Workflow ID is required", "Provide valid workflow ID")

        with self.db_engine.get_session_context() as session:
            result = self.orchestration.delete_workflow(session, workflow_id)

        logger.info(f"Workflow {workflow_id} deleted successfully")
        return result
    
    @ErrorManager.operation_context("workflow_update")
    def workflow_update(self, workflow_id: str, workflow_data: dict) -> dict:
        ErrorManager.validate_engine_state(self.db_engine)
        
        if not workflow_id:
            raise ValidationError("Workflow ID is required", "Provide valid workflow ID")

        with self.db_engine.get_session_context() as session:
            result = self.orchestration.update_workflow(session, workflow_id, workflow_data)

        logger.info(f"Workflow {workflow_id} updated successfully")
        return result

    @ErrorManager.operation_context("workflow_listing")
    def workflow_list(self, page: Optional[int] = None, page_size: Optional[int] = None) -> dict:
        ErrorManager.validate_engine_state(self.db_engine)

        with self.db_engine.get_session_context() as session:
            return self.orchestration.get_workflows(session, page, page_size)

    @ErrorManager.operation_context("workflow_retrieval")
    def workflow_get(self, workflow_id: str) -> dict:
        ErrorManager.validate_engine_state(self.db_engine)
        
        if not workflow_id:
            raise ValidationError("Workflow ID is required", "Provide valid workflow ID")

        with self.db_engine.get_session_context() as session:
            return self.orchestration.get_workflow(session, workflow_id)
    
    # EXECUTION METOTLARI 
    # ===========================================================
    @ErrorManager.operation_context("trigger_workflow")
    def trigger_workflow(self, workflow_id: str) -> dict:
        ErrorManager.validate_engine_state(self.db_engine)
        
        if not workflow_id:
            raise ValidationError("Workflow ID is required", "Provide valid workflow ID")
    
        with self.db_engine.get_session_context() as session:
            result = self.orchestration.trigger_workflow(session, workflow_id)
        
        logger.info(f"Workflow {workflow_id} triggered successfully")
        return result
    
    @ErrorManager.operation_context("execution_cancellation")
    def cancel_execution(self, execution_id: str) -> dict:
        ErrorManager.validate_engine_state(self.db_engine)
        
        if not execution_id:
            raise ValidationError("Execution ID is required", "Provide valid execution ID")
        
        with self.db_engine.get_session_context() as session:
            result = self.orchestration.cancel_execution(session, execution_id)
        
        logger.info(f"Execution {execution_id} cancelled successfully")
        return result
    
    @ErrorManager.operation_context("execution_retrieval")
    def execution_get(self, execution_id: str) -> dict:
        ErrorManager.validate_engine_state(self.db_engine)
        
        if not execution_id:
            raise ValidationError("Execution ID is required", "Provide valid execution ID")
        
        with self.db_engine.get_session_context() as session:
            result = self.orchestration.get_execution(session, execution_id)
        
        logger.info(f"Execution {execution_id} retrieved successfully")
        return result

    @ErrorManager.operation_context("execution_listing")
    def execution_list(self, page: Optional[int] = None, page_size: Optional[int] = None) -> dict:
        ErrorManager.validate_engine_state(self.db_engine)
        
        with self.db_engine.get_session_context() as session:
            result =  self.orchestration.get_executions(session, page, page_size)
        
        logger.info(f"Executions listed successfully")
        return result

    @ErrorManager.operation_context("execution_listing_by_workflow")
    def execution_list_by_workflow(self, workflow_id: str, page: Optional[int] = None, page_size: Optional[int] = None) -> list:
        """Get all executions for a specific workflow"""
        ErrorManager.validate_engine_state(self.db_engine)
        
        if not workflow_id:
            raise ValidationError("Workflow ID is required", "Provide valid workflow ID")
        
        with self.db_engine.get_session_context() as session:
            executions = self.orchestration.execution_crud.get_executions_by_workflow(session, workflow_id)
            
            # Convert to list of dictionaries with consistent field names
            result = []
            for execution in executions:
                exec_dict = {
                    'execution_id': execution.id,  # Use execution_id for consistency
                    'workflow_id': execution.workflow_id,
                    'status': execution.status.value if hasattr(execution.status, 'value') else execution.status,
                    'started_at': execution.started_at.isoformat() if execution.started_at else None,
                    'ended_at': execution.ended_at.isoformat() if execution.ended_at else None,
                    'created_at': execution.created_at.isoformat() if execution.created_at else None,
                    'updated_at': execution.updated_at.isoformat() if execution.updated_at else None
                }
                result.append(exec_dict)
        
        logger.info(f"Retrieved {len(result)} executions for workflow {workflow_id}")
        return result

    # HEALTH CHECK METHOD
    # ===========================================================
    def health_check(self) -> dict:
        """
        System health check - returns status of all components
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
                "ready_tasks": self._get_ready_task_count() if all_healthy else -1
            }
            
        except Exception as e:
            return {
                "status": "error",
                "timestamp": datetime.utcnow().isoformat() + "Z", 
                "error": str(e),
                "components": {}
            }
        
    # API SERVER METHODS
    # ===========================================================
    @ErrorManager.operation_context("api_server_startup")
    def start_api_server(self, host: str = "127.0.0.1", port: int = 8000, reload: bool = False) -> None:
        """Start the Miniflow API server"""
        try:
            import uvicorn
            from .api import app
            
            logger.info(f"Starting Miniflow API Server at {host}:{port}")
            logger.info(f"API Documentation available at: http://{host}:{port}/docs")
            logger.info(f"Health Check available at: http://{host}:{port}/health")
            
            if self.enable_scheduler:
                logger.info("Scheduler is enabled - workflows will be automatically executed")
            else:
                logger.info("Scheduler is disabled - workflows must be executed manually")
            
            uvicorn.run(
                app,
                host=host,
                port=port,
                reload=reload,
                log_level="info"
            )
            
        except ImportError as e:
            raise ResourceError(
                "API dependencies missing",
                "Install required packages: pip install fastapi uvicorn"
            ) from e





    # DEMONSTRATION AND TESTING METHODS
    # ===========================================================
    
    def demo_workflow_execution(self) -> dict:
        """
        Demonstration method showing complete workflow execution with scheduler
        Creates a simple workflow and shows the execution flow
        """
        try:
            ErrorManager.validate_engine_state(self.db_engine)
            
            if not self.enable_scheduler:
                return {
                    "status": "error",
                    "message": "Scheduler must be enabled for automatic workflow execution",
                    "suggestion": "Initialize MiniflowCore with enable_scheduler=True"
                }
            
            logger.info("Starting workflow execution demonstration...")
            
            # Check if required components are running
            health = self.health_check()
            if health["status"] != "healthy":
                return {
                    "status": "error", 
                    "message": "System is not healthy",
                    "health_status": health
                }
            
            return {
                "status": "ready",
                "message": "System is ready for workflow execution",
                "next_steps": [
                    "1. Create a script using script_create()",
                    "2. Create a workflow using workflow_create()",
                    "3. Trigger workflow using trigger_workflow()",
                    "4. Monitor execution with execution_get() or health_check()"
                ],
                "components": {
                    "database": "✓ Connected",
                    "parallelism_engine": "✓ Running",
                    "scheduler": "✓ Active (Input & Output monitors running)",
                    "ready_tasks": self._get_ready_task_count()
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Demo execution failed: {str(e)}"
            }
    
    def _get_ready_task_count(self) -> int:
        """Helper method to get count of ready tasks"""
        try:
            with self.db_engine.get_session_context() as session:
                return self.orchestration.execution_input_crud.count_ready_tasks(session)
        except:
            return -1