# COMMON IMPORTS (OPTIMIZED)
# ===========================================================
from .common import logging, Path, datetime, Optional, Dict, Any

# Miniflow Utility
from .utils import setup_logging
from .utils import create_script, delete_script
from .utils import format_timestamp_fields

# Miniflow Exceptions
from .exceptions import MiniflowException, ErrorManager
# Removed unused imports: create_error_response, handle_unexpected_error
from .exceptions import (DatabaseError, SchedulerError, EngineError,
                         ValidationError, BusinessLogicError, ResourceError)

# Miniflow Database
from .database_manager import DatabaseConfig, DatabaseEngine, DatabaseOrchestration, Base
from .database_manager import get_sqlite_config, get_mysql_config, get_postgresql_config
from .database_manager import create_database_engine

# Minlfow Parallelism Engine
from .parallelism_engine import Manager

# Miniflow Scheduler
from .scheduler import MiniflowInputMonitor, MiniflowOutputMonitor

# Miniflow Monitoring
from .monitoring import MonitoringManager, MetricsCollector, PerformanceTracker, DatabaseMetrics

# Miniflow Security
# from .security import AuthenticationManager, AuthorizationManager,
# SecurityValidator  # TODO: Implement security module


# LOGGER SETUP (CENTRALIZED)
# ===========================================================
setup_logging()  # Global logger setup - tüm modüller için
logger = logging.getLogger(__name__)
logger.debug("Miniflow core logger initialized - centralized setup complete")


# MINIFLOW CORE CLASS
# ===========================================================
class MiniflowCore:
    """
    MiniflowCore sınıfı, Miniflow'un temel işlevlerini yöneten ana sınıftır.
    Bu sınıf, veritabanı, execution engine ve scheduler gibi bileşenleri başlatır ve durdurur.
    """

    def __init__(
            self,
            db_type: str,
            enable_scheduler: bool = True,
            **db_params):
        # Database Manager Parametreleri
        self.db_type: str = db_type or "sqlite"
        self.db_engine: DatabaseEngine = None
        self.orchestration: DatabaseOrchestration = None
        self.db_params: dict = db_params or {"db_name": "test_database"}
        self.db_config: DatabaseConfig = self.__create_config(
            db_type, **self.db_params)

        # Scripts
        self.scripts_dir: Path = Path("scripts")

        # Parallelism Engine
        self.execution_engine: Manager = None

        # Scheduler
        self.enable_scheduler: bool = enable_scheduler
        self.input_monitor: MiniflowInputMonitor = None
        self.output_monitor: MiniflowOutputMonitor = None

        # Monitoring components
        self.enable_monitoring = True  # Enable by default
        self.monitoring: Optional[MonitoringManager] = None
        self.metrics_collector: Optional[MetricsCollector] = None
        self.performance_tracker: Optional[PerformanceTracker] = None
        self.database_metrics: Optional[DatabaseMetrics] = None

        # Security components (placeholder)
        self.enable_security = True  # Enable by default
        # TODO: Implement security system in Phase 4
        # self.auth_manager: Optional[AuthenticationManager] = None
        # self.authz_manager: Optional[AuthorizationManager] = None
        # self.security_validator: Optional[SecurityValidator] = None

        logger.debug(f"MiniflowCore initialized")

    # DATABASE MANAGER METOTLARI
    # ===========================================================
    @staticmethod
    def __create_config(db_type: str, **db_params):
        config_map = {
            "sqlite": lambda: get_sqlite_config(db_params.get("db_name", "test_database")
                                                ),
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

    # PARALLELISM ENGINE METOTLARI
    # ===========================================================
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
                except BaseException:
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

    # SCHEDULER METOTLARI
    # ===========================================================
    def __start_scheduler(self):
        """Start the input and output monitors"""
        try:
            # Validate dependencies
            if not self.db_engine or not self.orchestration:
                raise SchedulerError(
                    "Database engine must be started before scheduler")

            if not self.execution_engine:
                raise SchedulerError(
                    "Parallelism engine must be started before scheduler")

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

            logger.info(
                "Scheduler started successfully (Input & Output monitors running)")

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

    def __start_monitoring(self):
        try:
            # Initialize monitoring manager
            self.monitoring = MonitoringManager(
                collection_interval=1.0,  # Collect every second
                history_duration_minutes=60,  # Keep 1 hour of history
                enable_detailed_metrics=True
            )

            # Start monitoring with database engine
            if self.monitoring.start(database_engine=self.db_engine):
                logger.info("Monitoring system initialized successfully")
                
                # Set individual component references for backward compatibility
                self.metrics_collector = self.monitoring.metrics_collector
                self.performance_tracker = self.monitoring.performance_tracker
                self.database_metrics = self.monitoring.database_metrics
            else:
                logger.error("Failed to start monitoring system")
                raise EngineError(
                    "Failed to start monitoring system",
                    "MonitoringManager failed to start"
                )

        except Exception as e:
            logger.error(f"Failed to start monitoring: {e}")
            self.monitoring = None
            self.metrics_collector = None
            self.performance_tracker = None
            self.database_metrics = None
            raise EngineError(
                "Failed to start monitoring system",
                f"Monitoring initialization error: {str(e)}"
            ) from e

    def __stop_monitoring(self):
        # Stop monitoring manager
        if self.monitoring:
            try:
                if self.monitoring.stop():
                    logger.info("Monitoring system stopped successfully")
                else:
                    logger.warning("Some monitoring components failed to stop properly")
            except Exception as e:
                logger.warning(f"Error stopping monitoring manager: {e}")
            finally:
                self.monitoring = None
                
        # Clear individual component references
        self.metrics_collector = None
        self.performance_tracker = None
        self.database_metrics = None

    def __start_security(self):
        """Start security components"""
        # TODO: Implement security system
        # Security system will be implemented in Phase 4
        logger.info("Security system: Placeholder (not implemented yet)")
        pass

    def __stop_security(self):
        """Stop security components"""
        # TODO: Implement security system cleanup
        # Security system will be implemented in Phase 4
        logger.info(
            "Security system cleanup: Placeholder (not implemented yet)")
        pass

    # CORE STARTUP AND SHUTDOWN METHODS
    # ===========================================================
    @ErrorManager.operation_context("core_startup")
    def start(self) -> bool:
        try:
            # 0. Set start time for uptime tracking
            self._start_time = datetime.utcnow()

            # 1. Database'i başlat
            self.__start_database_engine()

            # 2. Parallelism Engine'i başlat
            self.__start_parallelism_engine()

            # 3. Scheduler'ı başlat (isteğe bağlı)
            if self.enable_scheduler:
                self.__start_scheduler()

            # 4. Monitoring'i başlat
            if self.enable_monitoring:
                self.__start_monitoring()

            # 5. Security'i başlat
            if self.enable_security:
                self.__start_security()

            logger.info(
                f"MiniflowCore started successfully (scheduler={
                    'enabled' if self.enable_scheduler else 'disabled'}, monitoring={
                    'enabled' if self.enable_monitoring else 'disabled'})")
            return True
        except Exception as e:
            logger.error(f"Failed to start MiniflowCore: {e}")
            return False

    @ErrorManager.operation_context("core_shutdown")
    def stop(self) -> bool:
        # 1. Security'i durdur
        if self.enable_security:
            self.__stop_security()

        # 2. Monitoring'i durdur
        if self.enable_monitoring:
            self.__stop_monitoring()

        # 3. Scheduler'ı durdur
        if self.enable_scheduler:
            self.__stop_scheduler()

        # 4. Parallelism Engine'i durdur
        self.__stop_parallelism_engine()

        # 5. Database'i durdur
        self.__stop_database_engine()

        logger.info("MiniflowCore stopped successfully")
        return True

    # API METOTOLARI
    # ===========================================================
    # SCRIPT METOTLARI
    # NEW: Optimized decorator
    @ErrorManager.with_database_session("script_creation")
    def script_create(
            self,
            session,
            script_data: dict,
            script_content: str) -> dict:
        # Validate inputs
        ErrorManager.validate_required_fields(
            script_data, ["name"], "script creation")

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
            'script_path': absolute_path
        }

        # 4. Veritabanı kaydı oluştur (session otomatik yönetiliyor)
        result = self.orchestration.create_script(session, payload)
        session.flush()
        session.commit()

        # 5. Çıktıyı Döndür
        logger.info(f"Script created successfully: {script_data['name']}")
        return result

    # NEW: Optimized decorator
    @ErrorManager.with_database_session("script_deletion")
    def script_delete(self, session, script_id: str) -> dict:
        if not script_id:
            raise ValidationError(
                "Script ID is required",
                "Provide valid script ID")
        result = self.orchestration.delete_script(session, script_id)
        return result

    # NEW: Optimized decorator
    @ErrorManager.with_database_session("script_listing")
    def script_list(self, session) -> dict:
        result = self.orchestration.get_scripts(session)
        return result

    @ErrorManager.with_database_session("script_retrieval")  # OPTIMIZED
    def script_get(
            self,
            session,
            script_id: str,
            include_content: bool = False) -> dict:
        if not script_id:
            raise ValidationError(
                "Script ID is required",
                "Provide valid script ID")

        result = self.orchestration.get_script(
            session, script_id, include_content)
        return result

    # ENVIRONMENT VARIABLE METOTLARI
    # ==============================================================
    # OPTIMIZED
    @ErrorManager.with_database_session("environment_variable_creation")
    def environment_variable_create(self, session, env_var_data: dict) -> dict:
        """Create a new environment variable"""
        # Validate inputs
        ErrorManager.validate_required_fields(
            env_var_data, ["name", "value"], "environment variable creation")

        # Prepare payload
        payload = {
            'name': env_var_data['name'],
            'value': env_var_data['value'],
            'description': env_var_data.get('description'),
            'is_active': env_var_data.get('is_active', True)
        }

        # Create database record
        result = self.orchestration.create_environment_variable(
            session, payload)
        session.flush()
        session.commit()

        logger.info(
            f"Environment variable created successfully: {
                env_var_data['name']}")
        return result

    # OPTIMIZED
    @ErrorManager.with_database_session("environment_variable_deletion")
    def environment_variable_delete(self, session, env_var_id: str) -> dict:
        """Delete an environment variable"""
        if not env_var_id:
            raise ValidationError(
                "Environment variable ID is required",
                "Provide valid environment variable ID")

        result = self.orchestration.delete_environment_variable(
            session, env_var_id)

        logger.info(f"Environment variable deleted successfully: {env_var_id}")
        return result

    # OPTIMIZED
    @ErrorManager.with_database_session("environment_variable_update")
    def environment_variable_update(
            self,
            session,
            env_var_id: str,
            env_var_data: dict) -> dict:
        """Update an environment variable"""
        if not env_var_id:
            raise ValidationError(
                "Environment variable ID is required",
                "Provide valid environment variable ID")

        result = self.orchestration.update_environment_variable(
            session, env_var_id, **env_var_data)
        logger.info(f"Environment variable updated successfully: {env_var_id}")
        return result

    # OPTIMIZED
    @ErrorManager.with_database_session("environment_variable_listing")
    def environment_variable_list(
            self,
            session,
            active_only: bool = False) -> dict:
        """List all environment variables"""
        result = self.orchestration.get_environment_variables(
            session, active_only)
        return result

    # OPTIMIZED
    @ErrorManager.with_database_session("environment_variable_retrieval")
    def environment_variable_get(self, session, env_var_id: str) -> dict:
        """Get environment variable details"""
        if not env_var_id:
            raise ValidationError(
                "Environment variable ID is required",
                "Provide valid environment variable ID")

        result = self.orchestration.get_environment_variable(
            session, env_var_id)
        return result

    # OPTIMIZED
    @ErrorManager.with_database_session(
        "environment_variable_retrieval_by_name")
    def environment_variable_get_by_name(self, session, name: str) -> dict:
        """Get environment variable by name"""
        if not name:
            raise ValidationError(
                "Environment variable name is required",
                "Provide valid environment variable name")

        result = self.orchestration.get_environment_variable_by_name(
            session, name)
        return result

    # OPTIMIZED
    @ErrorManager.with_database_session("environment_variable_activation")
    def environment_variable_activate(self, session, env_var_id: str) -> dict:
        """Activate an environment variable"""
        if not env_var_id:
            raise ValidationError(
                "Environment variable ID is required",
                "Provide valid environment variable ID")

        result = self.orchestration.activate_environment_variable(
            session, env_var_id)

        logger.info(
            f"Environment variable activated successfully: {env_var_id}")
        return result

    # OPTIMIZED
    @ErrorManager.with_database_session("environment_variable_deactivation")
    def environment_variable_deactivate(
            self, session, env_var_id: str) -> dict:
        """Deactivate an environment variable"""
        if not env_var_id:
            raise ValidationError(
                "Environment variable ID is required",
                "Provide valid environment variable ID")

        result = self.orchestration.deactivate_environment_variable(
            session, env_var_id)
        logger.info(
            f"Environment variable deactivated successfully: {env_var_id}")
        return result

    # WORKFLOW METOTLARI
    @ErrorManager.with_database_session("workflow_creation")  # OPTIMIZED
    def workflow_create(self, session, workflow_data: dict) -> dict:
        ErrorManager.validate_required_fields(
            workflow_data, ["name", "nodes"], "workflow creation")
        # Ensure edges exist even if empty
        if "edges" not in workflow_data:
            workflow_data["edges"] = []

        result = self.orchestration.create_workflow(session, workflow_data)
        logger.info(f"Workflow '{workflow_data['name']}' created successfully")
        return result

    @ErrorManager.with_database_session("workflow_deletion")  # OPTIMIZED
    def workflow_delete(self, session, workflow_id: str) -> dict:
        if not workflow_id:
            raise ValidationError(
                "Workflow ID is required",
                "Provide valid workflow ID")

        result = self.orchestration.delete_workflow(session, workflow_id)
        logger.info(f"Workflow {workflow_id} deleted successfully")
        return result

    @ErrorManager.with_database_session("workflow_update")  # OPTIMIZED
    def workflow_update(
            self,
            session,
            workflow_id: str,
            workflow_data: dict) -> dict:
        if not workflow_id:
            raise ValidationError(
                "Workflow ID is required",
                "Provide valid workflow ID")

        result = self.orchestration.update_workflow(
            session, workflow_id, workflow_data)
        logger.info(f"Workflow {workflow_id} updated successfully")
        return result

    @ErrorManager.with_database_session("workflow_listing")  # OPTIMIZED
    def workflow_list(
            self,
            session,
            page: Optional[int] = None,
            page_size: Optional[int] = None) -> dict:
        return self.orchestration.get_workflows(session, page, page_size)

    @ErrorManager.with_database_session("workflow_retrieval")  # OPTIMIZED
    def workflow_get(self, session, workflow_id: str) -> dict:
        if not workflow_id:
            raise ValidationError(
                "Workflow ID is required",
                "Provide valid workflow ID")

        return self.orchestration.get_workflow(session, workflow_id)

    # EXECUTION METOTLARI
    @ErrorManager.with_database_session("trigger_workflow")  # OPTIMIZED
    def trigger_workflow(self, session, workflow_id: str) -> dict:
        if not workflow_id:
            raise ValidationError(
                "Workflow ID is required",
                "Provide valid workflow ID")

        result = self.orchestration.trigger_workflow(session, workflow_id)
        logger.info(f"Workflow {workflow_id} triggered successfully")
        return result

    @ErrorManager.with_database_session("execution_cancellation")  # OPTIMIZED
    def cancel_execution(self, session, execution_id: str) -> dict:
        if not execution_id:
            raise ValidationError(
                "Execution ID is required",
                "Provide valid execution ID")

        result = self.orchestration.cancel_execution(session, execution_id)
        logger.info(f"Execution {execution_id} cancelled successfully")
        return result

    @ErrorManager.with_database_session("execution_retrieval")  # OPTIMIZED
    def execution_get(self, session, execution_id: str) -> dict:
        if not execution_id:
            raise ValidationError(
                "Execution ID is required",
                "Provide valid execution ID")

        result = self.orchestration.get_execution(session, execution_id)
        logger.info(f"Execution {execution_id} retrieved successfully")
        return result

    @ErrorManager.with_database_session("execution_listing")  # OPTIMIZED
    def execution_list(
            self,
            session,
            page: Optional[int] = None,
            page_size: Optional[int] = None) -> dict:
        result = self.orchestration.get_executions(session, page, page_size)
        logger.info(f"Executions listed successfully")
        return result

    # OPTIMIZED
    @ErrorManager.with_database_session("execution_listing_by_workflow")
    def execution_list_by_workflow(
            self,
            session,
            workflow_id: str,
            page: Optional[int] = None,
            page_size: Optional[int] = None) -> list:
        """Get all executions for a specific workflow"""
        if not workflow_id:
            raise ValidationError(
                "Workflow ID is required",
                "Provide valid workflow ID")

        executions = self.orchestration.execution_crud.get_executions_by_workflow(
            session, workflow_id)

        # Convert to list of dictionaries with consistent field names -
        # OPTIMIZED
        result = []
        for execution in executions:
            exec_dict = {
                'execution_id': execution.id,  # Use execution_id for consistency
                'workflow_id': execution.workflow_id,
                'status': execution.status.value if hasattr(execution.status, 'value') else execution.status,
            }
            # OPTIMIZED: use centralized datetime formatting (eliminates 4
            # duplicate lines)
            exec_dict.update(format_timestamp_fields(execution))
            result.append(exec_dict)

        logger.info(
            f"Retrieved {
                len(result)} executions for workflow {workflow_id}")
        return result

    # OPTIMIZED
    @ErrorManager.with_database_session("execution_output_listing")
    def execution_output_list_by_execution(
            self, session, execution_id: str) -> list:
        """Get all execution outputs for a specific execution"""
        if not execution_id:
            raise ValidationError(
                "Execution ID is required",
                "Provide valid execution ID")

        execution_outputs = self.orchestration.execution_output_crud.get_execution_outputs_by_execution(
            session, execution_id)

        # Convert to list of dictionaries with consistent field names
        result = []
        for output in execution_outputs:
            output_dict = {
                'output_id': output.id,
                'execution_id': output.execution_id,
                'node_id': output.node_id,
                'node_name': getattr(
                    output.node,
                    'name',
                    'unknown') if output.node else 'unknown',
                'status': output.status.value if hasattr(
                    output.status,
                    'value') else output.status,
                'output_data': output.result_data or {},
            }
            # OPTIMIZED: use centralized datetime formatting (eliminates 4
            # duplicate lines)
            output_dict.update(format_timestamp_fields(output))
            result.append(output_dict)

        logger.info(
            f"Retrieved {
                len(result)} execution outputs for execution {execution_id}")
        return result

    # ENHANCED HEALTH CHECK & MONITORING
    # ===========================================================
    def health_check(self) -> dict:
        """
        Enhanced system health check with detailed metrics
        Returns comprehensive status of all components + system resources
        """
        try:
            import psutil
            import os

            # System Resource Metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            # Process-specific metrics
            current_process = psutil.Process(os.getpid())
            process_memory = current_process.memory_info()
            process_cpu = current_process.cpu_percent()

            # Network I/O (if available)
            try:
                network = psutil.net_io_counters()
                network_metrics = {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "packets_sent": network.packets_sent,
                    "packets_recv": network.packets_recv
                }
            except BaseException:
                network_metrics = {"status": "unavailable"}

            # Enhanced component health with monitoring integration
            components = {
                "database": {
                    "status": "healthy" if self.db_engine and self.db_engine.is_alive else "unhealthy",
                    "details": "Database engine running" if self.db_engine and self.db_engine.is_alive else "Database engine not running",
                    "connection_pool": self._get_database_pool_status() if self.db_engine else {"status": "unavailable"}
                },
                "parallelism_engine": {
                    "status": "healthy" if self.execution_engine and self.execution_engine.started else "unhealthy",
                    "details": "Execution engine running" if self.execution_engine and self.execution_engine.started else "Execution engine not running",
                    "process_count": len(self.execution_engine.active_processes) if self.execution_engine and hasattr(self.execution_engine, 'active_processes') else 0,
                    "queue_size": self._get_queue_metrics() if self.execution_engine else {"status": "unavailable"}
                },
                "scheduler": {
                    "input_monitor": {
                        "status": "healthy" if self.input_monitor and self.input_monitor.is_running() else "unhealthy",
                        "stats": getattr(self.input_monitor, 'stats', {}) if self.input_monitor else {}
                    },
                    "output_monitor": {
                        "status": "healthy" if self.output_monitor and self.output_monitor.is_running() else "unhealthy",
                        "stats": getattr(self.output_monitor, 'stats', {}) if self.output_monitor else {}
                    }
                },
                "monitoring": {
                    "metrics_collector": {
                        "status": "healthy" if self.metrics_collector and self.metrics_collector.is_collecting() else "unhealthy",
                        "stats": self.metrics_collector.get_collection_stats() if self.metrics_collector else {"status": "unavailable"}
                    },
                    "performance_tracker": {
                        "status": "healthy" if self.performance_tracker else "unavailable",
                        "stats": self.performance_tracker.get_tracker_stats() if self.performance_tracker else {"status": "unavailable"}
                    },
                    "database_metrics": {
                        "status": "healthy" if self.database_metrics else "unavailable",
                        "stats": self.database_metrics.get_database_summary() if self.database_metrics else {"status": "unavailable"}
                    }
                },
                "security": {
                    "authentication": {
                        "status": "healthy" if self.auth_manager else "unavailable",
                        "info": self.auth_manager.get_security_info() if self.auth_manager else {"status": "unavailable"}
                    },
                    "authorization": {
                        "status": "healthy" if self.authz_manager else "unavailable",
                        "info": self.authz_manager.get_authorization_info() if self.authz_manager else {"status": "unavailable"}
                    }
                }
            }

            # System Resource Status
            system_resources = {
                "cpu": {
                    "system_percent": cpu_percent,
                    "process_percent": process_cpu,
                    "core_count": psutil.cpu_count(),
                    "status": "healthy" if cpu_percent < 80 else "warning" if cpu_percent < 95 else "critical"
                },
                "memory": {
                    "system_total_gb": round(memory.total / (1024**3), 2),
                    "system_used_gb": round(memory.used / (1024**3), 2),
                    "system_percent": memory.percent,
                    "process_rss_mb": round(process_memory.rss / (1024**2), 2),
                    "process_vms_mb": round(process_memory.vms / (1024**2), 2),
                    "status": "healthy" if memory.percent < 80 else "warning" if memory.percent < 95 else "critical"
                },
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "percent": round((disk.used / disk.total) * 100, 1),
                    "status": "healthy" if (disk.used / disk.total) < 0.8 else "warning" if (disk.used / disk.total) < 0.95 else "critical"
                },
                "network": network_metrics
            }

            # Overall health assessment
            component_healthy = (
                components["database"]["status"] == "healthy" and
                components["parallelism_engine"]["status"] == "healthy" and
                (not self.enable_scheduler or (
                    components["scheduler"]["input_monitor"]["status"] == "healthy" and
                    components["scheduler"]["output_monitor"]["status"] == "healthy"
                )) and
                (not self.enable_monitoring or (
                    components["monitoring"]["metrics_collector"]["status"] in ["healthy", "unavailable"] and
                    components["monitoring"]["performance_tracker"]["status"] in ["healthy", "unavailable"] and
                    components["monitoring"]["database_metrics"]["status"] in ["healthy", "unavailable"]
                )) and
                (not self.enable_security or (
                    components["security"]["authentication"]["status"] in ["healthy", "unavailable"] and
                    components["security"]["authorization"]["status"] in ["healthy", "unavailable"]
                ))
            )

            resource_healthy = (
                system_resources["cpu"]["status"] in [
                    "healthy",
                    "warning"] and system_resources["memory"]["status"] in [
                    "healthy",
                    "warning"] and system_resources["disk"]["status"] in [
                    "healthy",
                    "warning"])

            overall_status = "healthy" if (
                component_healthy and resource_healthy) else "unhealthy"

            return {
                "status": overall_status,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "uptime_seconds": self._get_uptime_seconds(),
                "components": components,
                "system_resources": system_resources,
                "business_metrics": {
                    "ready_tasks": self._get_ready_task_count() if component_healthy else -1,
                    "total_executions": self._get_total_execution_count(),
                    "success_rate_24h": self._get_success_rate_24h()},
                "monitoring_data": self._get_monitoring_summary() if self.enable_monitoring else {
                    "status": "disabled"}}

        except Exception as e:
            return {
                "status": "error",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "error": str(e),
                "components": {},
                "system_resources": {"status": "error", "error": str(e)}
            }
    # MONITORING HELPER METHODS
    # ===========================================================

    def _get_database_pool_status(self) -> dict:
        """Get database connection pool status"""
        try:
            if not self.db_engine or not hasattr(self.db_engine, 'engine'):
                return {"status": "unavailable"}

            pool = self.db_engine.engine.pool
            return {
                "pool_size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "invalid": pool.invalid(),
                "status": "healthy" if pool.checkedout() < pool.size() else "warning"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _get_queue_metrics(self) -> dict:
        """Get execution queue metrics"""
        try:
            if not self.execution_engine:
                return {"status": "unavailable"}

            # Get process controller metrics
            process_controller = getattr(
                self.execution_engine, 'process_controller', None)
            queue_controller = getattr(
                self.execution_engine, 'queue_controller', None)

            input_queue = getattr(self.execution_engine, 'input_queue', None)
            output_queue = getattr(self.execution_engine, 'output_queue', None)

            metrics = {}

            # Input queue size
            if input_queue and hasattr(input_queue, 'q'):
                try:
                    metrics["input_queue_size"] = input_queue.q.qsize()
                    metrics["dropped_items"] = getattr(
                        input_queue, 'dropped_items', 0)
                except BaseException:
                    metrics["input_queue_size"] = "unavailable"

            # Output queue size
            if output_queue and hasattr(output_queue, 'q'):
                try:
                    metrics["output_queue_size"] = output_queue.q.qsize()
                except BaseException:
                    metrics["output_queue_size"] = "unavailable"

            # Process controller stats
            if process_controller:
                metrics["active_processes"] = len(
                    getattr(process_controller, 'active_processes', []))
                metrics["thread_counts"] = getattr(
                    process_controller, 'thread_count_list', [])

            return metrics
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _get_uptime_seconds(self) -> int:
        """Get system uptime in seconds"""
        try:
            if not hasattr(self, '_start_time'):
                self._start_time = datetime.utcnow()
            return int((datetime.utcnow() - self._start_time).total_seconds())
        except Exception as e:
            return 0

    def _get_total_execution_count(self) -> int:
        """Get total execution count"""
        try:
            ErrorManager.validate_engine_state(self.db_engine)
            with self.db_engine.get_session_context() as session:
                return self.orchestration.execution_crud.count(session)
        except Exception as e:
            logger.warning(f"Failed to get execution count: {e}")
        return -1

    def _get_success_rate_24h(self) -> float:
        """Get execution success rate for last 24 hours"""
        try:
            ErrorManager.validate_engine_state(self.db_engine)
            with self.db_engine.get_session_context() as session:
                from datetime import timedelta
                from sqlalchemy import and_

                # 24 saat öncesi
                twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)

                # Son 24 saatteki executions
                total_executions = self.orchestration.execution_crud.filter(
                    session,
                    {"created_at": twenty_four_hours_ago},
                    comparison_operators={"created_at": ">="}
                )

                if not total_executions:
                    return 100.0  # No executions = 100% success rate

                # Successful executions
                successful_executions = [
                    exec for exec in total_executions if hasattr(
                        exec, 'status') and str(
                        exec.status).lower() in [
                        'completed', 'success']]

                success_rate = (len(successful_executions) /
                                len(total_executions)) * 100
                return round(success_rate, 2)

        except Exception as e:
            logger.warning(f"Failed to calculate success rate: {e}")
        return -1.0

    def _get_monitoring_summary(self) -> Dict[str, Any]:
        """Get comprehensive monitoring data summary"""
        try:
            if self.monitoring:
                # Use MonitoringManager for comprehensive summary
                return self.monitoring.get_comprehensive_summary()
            else:
                # Fallback to individual components (backward compatibility)
                summary = {
                    "collection_active": False,
                    "current_metrics": None,
                    "performance_summary": None
                }

                # Metrics collector data
                if self.metrics_collector:
                    summary["collection_active"] = self.metrics_collector.is_collecting()
                    summary["current_metrics"] = self.metrics_collector.get_current_metrics()
                    summary["metrics_summary"] = self.metrics_collector.get_metrics_summary()

                # Performance tracker data
                if self.performance_tracker:
                    summary["performance_summary"] = self.performance_tracker.get_all_operations_summary(
                        minutes=10)
                    summary["tracker_stats"] = self.performance_tracker.get_tracker_stats()

                    # Get slow operations (over 1 second)
                    slow_ops = self.performance_tracker.get_slow_operations(
                        threshold_ms=1000, minutes=10)
                    if slow_ops:
                        # Top 5 slowest
                        summary["slow_operations_10min"] = slow_ops[:5]

                    # Get recent errors
                    error_ops = self.performance_tracker.get_error_operations(
                        minutes=10)
                    if error_ops:
                        # Most recent 5
                        summary["failed_operations_10min"] = error_ops[:5]

                # Database metrics data
                if self.database_metrics:
                    # Update connection pool metrics before getting summary
                    if self.db_engine:
                        self.database_metrics.update_pool_metrics(self.db_engine)

                    summary["database_summary"] = self.database_metrics.get_database_summary()
                    summary["query_stats"] = self.database_metrics.get_query_stats(
                        minutes=10)
                    summary["pool_status"] = self.database_metrics.get_pool_status()

                    # Get problematic queries
                    slow_queries = self.database_metrics.get_slow_queries(
                        minutes=10, threshold_ms=1000)
                    failed_queries = self.database_metrics.get_failed_queries(
                        minutes=10)

                    if slow_queries:
                        # Top 5 slowest
                        summary["slow_queries_10min"] = slow_queries[:5]
                    if failed_queries:
                        # Most recent 5
                        summary["failed_queries_10min"] = failed_queries[:5]

                return summary
        except Exception as e:
            logger.warning(f"Error generating monitoring summary: {e}")
            return {"status": "error", "error": str(e)}

    # API SERVER METHODS
    # ===========================================================

    @ErrorManager.operation_context("api_server_startup")
    def start_api_server(
            self,
            host: str = "127.0.0.1",
            port: int = 8000,
            reload: bool = False) -> None:
        """Start the Miniflow API server"""
        try:
            import uvicorn
            from .api import app

            logger.info(f"Starting Miniflow API Server at {host}:{port}")
            logger.info(
                f"API Documentation available at: http://{host}:{port}/docs")
            logger.info(
                f"Health Check available at: http://{host}:{port}/health")

            if self.enable_scheduler:
                logger.info(
                    "Scheduler is enabled - workflows will be automatically executed")
            else:
                logger.info(
                    "Scheduler is disabled - workflows must be executed manually")

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
                    "suggestion": "Initialize MiniflowCore with enable_scheduler=True"}

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
                    "4. Monitor execution with execution_get() or health_check()"],
                "components": {
                    "database": "✓ Connected",
                    "parallelism_engine": "✓ Running",
                    "scheduler": "✓ Active (Input & Output monitors running)",
                    "ready_tasks": self._get_ready_task_count()}}
        except Exception as e:
            return {
                "status": "error",
                "message": f"Demo execution failed: {str(e)}"
            }

    def _get_ready_task_count(self) -> int:
        """Helper method to get count of ready tasks"""
        try:
            with self.db_engine.get_session_context() as session:
                return self.orchestration.execution_input_crud.count_ready_tasks(
                    session)
        except BaseException:
            return -1
