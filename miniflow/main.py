import logging
from pathlib import Path
from typing import Optional, Dict, Any

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

setup_logging()
logger = logging.getLogger(__name__)
logger.debug(f"Logger tanımları tanımlandı")


class MiniflowCore:
    def __init__(self, db_type: str,  **db_params):
        # Database
        self.db_type: str = db_type
        self.db_engine: DatabaseEngine = None
        self.orchestration: DatabaseOrchestration = None
        self.scripts_dir: Path = Path("scripts")
        self.db_config: DatabaseConfig = self.__create_config(db_type, **db_params)
        logger.debug(f"Database tanımları tanımlandı")

    @ErrorManager.operation_context("core_startup")
    def start(self) -> None:
        # 1. Database'i başlat
        self.__start_database_engine()
        logger.info("MiniflowCore started successfully")

    @ErrorManager.operation_context("core_shutdown")
    def stop(self) -> None:
        # n. Database'i durdur
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
        ErrorManager.validate_required_fields(workflow_data, ["name", "nodes", "edges"], "workflow creation")
        
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
        
        
    # API SERVER METHODS
    # ===========================================================
    @ErrorManager.operation_context("api_server_startup")
    def start_api_server(self, host: str = "127.0.0.1", port: int = 8000, reload: bool = False) -> None:
        """Start the Miniflow API server"""
        try:
            import uvicorn
            from .api import app
            
            logger.info(f"Starting Miniflow API Server at {host}:{port}")
            logger.info(f"Documentation available at: http://{host}:{port}/docs")
            
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


        """Check system health status"""
        try:
            ErrorManager.validate_engine_state(self.db_engine)
            
            # Test database connection
            with self.db_engine.get_session_context() as session:
                # Simple query to test connection
                pass
                
            return {
                "status": "healthy",
                "database": "connected",
                "scripts_dir": "accessible" if self.scripts_dir.exists() else "missing"
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "database": "disconnected" if not self.db_engine else "error"
            }