# orchestration/scheduler_orchestration.py
import logging
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from enum import Enum
import time
from functools import wraps

from .base_orchestration import BaseOrchestration
from ...exceptions import ValidationError, BusinessLogicError, CRUDException, DatabaseError
from ..models import ExecutionOutputStatus
from ..utils.scheduler_utils import categorize_variables


# Constants
class TaskStatus:
    SUCCESS = 'success'
    FAILURE = 'failure'
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


class ExecutionStatus:
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


class WorkflowStatus:
    ACTIVE = 'active'
    DRAFT = 'draft'
    INACTIVE = 'inactive'


@dataclass
class SchedulerConfig:
    """Configuration for SchedulerOrchestrator"""
    default_task_limit: int = 10
    cleanup_execution_days: int = 30
    cleanup_audit_days: int = 90
    max_retry_attempts: int = 3
    retry_delay_seconds: int = 5
    batch_size: int = 100
    enable_metrics: bool = True
    log_level: str = "INFO"


@dataclass
class SystemMetrics:
    """System metrics data structure"""
    executions_total: int = 0
    executions_pending: int = 0
    executions_running: int = 0
    executions_completed: int = 0
    executions_failed: int = 0
    workflows_total: int = 0
    workflows_active: int = 0
    workflows_draft: int = 0
    audit_logs_count: int = 0


def retry_on_database_error(max_attempts: int = 3, delay: float = 1.0):
    """Decorator for retrying database operations"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except (DatabaseError, CRUDException) as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        time.sleep(delay * (2 ** attempt))  # Exponential backoff
                        continue
                    break
            raise last_exception

        return wrapper

    return decorator


class SchedulerOrchestrator(BaseOrchestration):
    """
    Scheduler orchestration operations for task execution management.

    Provides high-level operations for task scheduling, execution monitoring,
    result processing, and dependency management for the workflow execution engine.
    """

    def __init__(self, config: Optional[SchedulerConfig] = None):
        """
        Initialize SchedulerOrchestrator.

        Args:
            config (SchedulerConfig, optional): Configuration object
        """
        super().__init__()
        self.config = config or SchedulerConfig()
        self.logger = self._setup_logger()
        self.metrics = SystemMetrics()

    def _setup_logger(self) -> logging.Logger:
        """Setup logger with appropriate configuration"""
        logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        logger.setLevel(getattr(logging, self.config.log_level))

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    @retry_on_database_error(max_attempts=3)
    def get_ready_tasks(self, session: Session, limit: Optional[int] = None,
                        resolve_params: bool = True) -> List[Dict[str, Any]]:
        """
        Get ready tasks from execution input table for processing.
        Optimized version with batch parameter resolution and error handling.

        Args:
            session (Session): Database session for transaction management
            limit (int, optional): Maximum number of tasks to retrieve
            resolve_params (bool): Whether to resolve dynamic parameters (default: True)

        Returns:
            List[Dict[str, Any]]: List of ready task payloads for execution

        Raises:
            DatabaseError: If database operation fails or task retrieval fails
        """
        if limit is None:
            limit = self.config.default_task_limit

        self.logger.info("Retrieving ready tasks with limit: %d", limit)

        try:
            # Get ready tasks with eager loading to prevent N+1 queries
            ready_tasks = self.execution_input_crud.get_ready_tasks(session, limit=limit)
            self.logger.debug("Found %d ready tasks", len(ready_tasks))

            # Create task payloads
            task_payloads = self._create_task_payloads_batch(ready_tasks)

            # Resolve parameters if requested
            if resolve_params and task_payloads:
                task_payloads = self._resolve_task_parameters_batch(session, task_payloads)

            self.logger.info("Successfully processed %d tasks", len(task_payloads))
            return task_payloads

        except CRUDException as e:
            self.logger.error("Failed to get ready tasks: %s", str(e))
            raise DatabaseError(f"Failed to get ready tasks: {str(e)}")

    def _create_task_payloads_batch(self, tasks: List[Any]) -> List[Dict[str, Any]]:
        """Create task payloads in batch for better performance"""
        task_payloads = []
        failed_count = 0

        for task in tasks:
            try:
                payload = self.create_task_payload(task)
                task_payloads.append(payload)
            except Exception as e:
                failed_count += 1
                task_id = getattr(task, 'id', 'unknown')
                self.logger.warning("Failed to create payload for task %s: %s", task_id, str(e))
                continue

        if failed_count > 0:
            self.logger.warning("Failed to create %d out of %d task payloads",
                                failed_count, len(tasks))

        return task_payloads

    def _resolve_task_parameters_batch(self, session: Session,
                                       task_payloads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Resolve task parameters in batch for better performance"""
        resolved_payloads = []
        failed_count = 0

        for payload in task_payloads:
            try:
                resolved_payload = self.resolve_task_parameters(session, payload)
                resolved_payloads.append(resolved_payload)
            except Exception as e:
                failed_count += 1
                task_id = payload.get('id', 'unknown')
                self.logger.warning("Failed to resolve parameters for task %s: %s", task_id, str(e))
                # Use original payload as fallback
                resolved_payloads.append(payload)

        if failed_count > 0:
            self.logger.warning("Failed to resolve parameters for %d out of %d tasks",
                                failed_count, len(task_payloads))

        return resolved_payloads

    def create_task_payload(self, task: Any) -> Dict[str, Any]:
        """
        Create execution payload for a task object.

        Args:
            task: Task object containing execution input data

        Returns:
            Dict[str, Any]: Task payload ready for execution

        Raises:
            ValidationError: If task data is invalid or incomplete
        """
        if task is None:
            raise ValidationError("Task cannot be None")

        # Handle dict format tasks
        if isinstance(task, dict):
            return self._validate_task_dict(task)

        # Handle ExecutionInput objects
        return self._convert_task_object_to_dict(task)

    def _validate_task_dict(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Validate task dictionary format"""
        required_fields = ['id', 'execution_id', 'node_id', 'workflow_id']
        missing_fields = [field for field in required_fields if field not in task]

        if missing_fields:
            raise ValidationError(f"Task dict missing required fields: {missing_fields}")

        return task

    def _convert_task_object_to_dict(self, task: Any) -> Dict[str, Any]:
        """Convert ExecutionInput object to dictionary"""
        return {
            'id': task.id,
            'execution_id': task.execution_id,
            'node_id': task.node_id,
            'workflow_id': task.workflow_id,
            'input_data': task.node_params,
            'dependency_count': task.dependency_count,
            'created_at': task.created_at
        }

    @retry_on_database_error(max_attempts=3)
    def process_execution_result(self, session: Session, result: Dict[str, Any]) -> bool:
        """
        Process execution result and create execution output

        Args:
            session (Session): Database session
            result (Dict[str, Any]): Execution result data

        Returns:
            bool: True if processing successful

        Raises:
            ValidationError: If result data is invalid
            DatabaseError: If database operation fails
        """
        self.logger.info("Processing execution result for execution_id: %s, node_id: %s",
                         result.get('execution_id'), result.get('node_id'))

        # Validate result data
        self._validate_execution_result(result)

        execution_id = result['execution_id']
        node_id = result['node_id']
        status = result['status']

        try:
            # Create execution output
            self._create_execution_output(session, result)
            self.logger.debug("Created execution output for node %s", node_id)

            # Update dependencies if successful
            if status == TaskStatus.SUCCESS:
                self._update_dependencies(session, node_id, execution_id)
                self.logger.debug("Updated dependencies for node %s", node_id)

            self.logger.info("Successfully processed execution result for node %s", node_id)
            return True

        except ValidationError:
            self.logger.error("Validation error processing result for node %s", node_id)
            raise
        except CRUDException as e:
            self.logger.error("Database error processing result for node %s: %s", node_id, str(e))
            raise DatabaseError(f"Failed to process execution result: {str(e)}")

    def _validate_execution_result(self, result: Dict[str, Any]) -> None:
        """Validate execution result data"""
        if not isinstance(result, dict):
            raise ValidationError("Result must be a dictionary")

        required_fields = ['execution_id', 'node_id', 'status']
        missing_fields = [field for field in required_fields if not result.get(field)]

        if missing_fields:
            raise ValidationError(f"Missing required fields: {missing_fields}")

        valid_statuses = [TaskStatus.SUCCESS, TaskStatus.FAILURE]
        if result['status'] not in valid_statuses:
            raise ValidationError(f"Status must be one of: {valid_statuses}")

    def _create_execution_output(self, session: Session, result: Dict[str, Any]) -> None:
        """Create execution output record"""
        execution_id = result['execution_id']
        node_id = result['node_id']
        status = result['status']
        result_data = result.get('result_data', {})

        # Convert status to enum
        output_status = (
            ExecutionOutputStatus.SUCCESS if status == TaskStatus.SUCCESS
            else ExecutionOutputStatus.FAILURE
        )

        current_time = datetime.now(timezone.utc)
        output_payload = {
            'execution_id': execution_id,
            'node_id': node_id,
            'status': output_status,
            'result_data': result_data,
            'started_at': result.get('started_at', current_time),
            'ended_at': result.get('ended_at', current_time)
        }

        self.execution_output_crud.create_execution_output(session, **output_payload)

    def _update_dependencies(self, session: Session, node_id: str, execution_id: str) -> None:
        """Update dependency counts for dependent nodes"""
        try:
            # Get all outgoing edges in single query
            edges = self.edge_crud.filter(session, {'from_node_id': node_id})

            if not edges:
                self.logger.debug("No outgoing edges found for node %s", node_id)
                return

            # Prepare batch dependency updates
            dependency_updates = [
                {'execution_id': execution_id, 'node_id': edge.to_node_id}
                for edge in edges
            ]

            # Use batch operation if available
            if hasattr(self.execution_input_crud, 'batch_decrease_dependencies'):
                self.execution_input_crud.batch_decrease_dependencies(session, dependency_updates)
                self.logger.debug("Batch updated %d dependencies", len(dependency_updates))
            else:
                # Fallback to individual updates
                updated_count = self._update_dependencies_individually(session, dependency_updates)
                self.logger.debug("Individually updated %d dependencies", updated_count)

        except Exception as e:
            self.logger.error("Failed to update dependencies for node %s: %s", node_id, str(e))
            session.rollback()
            raise

    def _update_dependencies_individually(self, session: Session,
                                          dependency_updates: List[Dict[str, str]]) -> int:
        """Update dependencies individually with optimized session handling"""
        updated_count = 0

        for update_item in dependency_updates:
            try:
                execution_input = self.execution_input_crud.get_by_execution_and_node(
                    session, update_item['execution_id'], update_item['node_id']
                )
                if execution_input and execution_input.dependency_count > 0:
                    execution_input.dependency_count -= 1
                    updated_count += 1
            except CRUDException:
                # Execution input not found, skip
                continue

        # Single flush for all updates
        if updated_count > 0:
            session.flush()

        return updated_count

    @retry_on_database_error(max_attempts=3)
    def collect_final_results(self, session: Session, execution_id: str) -> Dict[str, Any]:
        """
        Collect final results for an execution

        Args:
            session (Session): Database session
            execution_id (str): Execution ID

        Returns:
            Dict[str, Any]: Final execution results

        Raises:
            BusinessLogicError: If execution not found
            DatabaseError: If database operation fails
        """
        self.logger.info("Collecting final results for execution: %s", execution_id)

        try:
            # Get execution and validate
            execution = self.execution_crud.find_by_id(session, execution_id)
            if not execution:
                raise BusinessLogicError(f"Execution not found: {execution_id}")

            # Get all execution outputs with eager loading
            outputs = self.execution_output_crud.get_by_execution(session, execution_id)

            # Build results dictionary
            results = {
                output.node_id: {
                    'status': str(output.status),
                    'result_data': output.result_data,
                    'started_at': output.started_at,
                    'ended_at': output.ended_at
                }
                for output in outputs
            }

            final_results = {
                'execution_id': execution_id,
                'workflow_id': execution.workflow_id,
                'status': str(execution.status),
                'results': results,
                'total_nodes': len(results)
            }

            self.logger.info("Collected results for %d nodes in execution %s",
                             len(results), execution_id)
            return final_results

        except CRUDException as e:
            self.logger.error("Failed to collect final results for execution %s: %s",
                              execution_id, str(e))
            raise DatabaseError(f"Failed to collect final results: {str(e)}")

    def check_if_last_node(self, session: Session, node_id: str, execution_id: str) -> bool:
        """
        Check if this node is the last node in execution

        Args:
            session (Session): Database session
            node_id (str): Node ID to check
            execution_id (str): Execution ID for context

        Returns:
            bool: True if this is the last node (no outgoing edges)

        Raises:
            DatabaseError: If database operation fails
        """
        try:
            # Check for outgoing edges
            outgoing_edges = self.edge_crud.filter(session, {'from_node_id': node_id})
            is_last = len(outgoing_edges) == 0

            self.logger.debug("Node %s is%s the last node in execution %s",
                              node_id, "" if is_last else " not", execution_id)
            return is_last

        except CRUDException as e:
            self.logger.error("Failed to check if last node %s: %s", node_id, str(e))
            raise DatabaseError(f"Failed to check if last node: {str(e)}")

    def resolve_parameter_context(self, session: Session, params: Dict[str, Any],
                                  execution_id: Optional[str] = None,
                                  workflow_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create execution context from parameter dictionary

        Args:
            session (Session): Database session
            params (Dict[str, Any]): Parameter dictionary
            execution_id (str, optional): Execution ID for dynamic values
            workflow_id (str, optional): Workflow ID for node name resolution

        Returns:
            Dict[str, Any]: Variable name to value mapping

        Raises:
            ValidationError: If parameters are invalid
            DatabaseError: If database operation fails
        """
        if not isinstance(params, dict):
            raise ValidationError("Parameters must be a dictionary")

        self.logger.debug("Resolving parameter context with %d parameters", len(params))

        try:
            # Categorize variables
            categorized = categorize_variables(params)
            context = {}

            # Process each variable type
            self._resolve_static_variables(categorized['static_variables'], context)
            self._resolve_environment_variables(session, categorized['environment_variables'], context)
            self._resolve_dynamic_id_variables(session, categorized['dynamic_variable_by_id'], context)
            self._resolve_dynamic_name_variables(session, categorized['dynamic_variable_by_name'],
                                                 context, workflow_id)

            self.logger.debug("Successfully resolved %d parameters", len(context))
            return context

        except ValidationError:
            raise
        except CRUDException as e:
            self.logger.error("Database error resolving parameter context: %s", str(e))
            raise DatabaseError(f"Failed to create execution context: {str(e)}")
        except Exception as e:
            self.logger.error("Unexpected error resolving parameter context: %s", str(e))
            raise DatabaseError(f"Unexpected error creating execution context: {str(e)}")

    def _resolve_static_variables(self, static_vars: List[Dict[str, Any]],
                                  context: Dict[str, Any]) -> None:
        """Resolve static variables"""
        for static_var in static_vars:
            var_name = static_var['variable_name']
            value = static_var['value']
            context[var_name] = value

    def _resolve_environment_variables(self, session: Session, env_vars: List[Dict[str, Any]],
                                       context: Dict[str, Any]) -> None:
        """Resolve environment variables"""
        for env_var in env_vars:
            var_name = env_var['variable_name']
            env_variable = env_var['env_variable']
            try:
                value = self._resolve_environment_variable(session, record_name=env_variable)
                context[var_name] = value
            except Exception as e:
                context[var_name] = None
                self.logger.warning("Environment variable '%s' not found: %s", env_variable, str(e))

    def _resolve_dynamic_id_variables(self, session: Session, dynamic_id_vars: List[Dict[str, Any]],
                                      context: Dict[str, Any]) -> None:
        """Resolve dynamic ID-based variables"""
        for dynamic_id_var in dynamic_id_vars:
            var_name = dynamic_id_var['variable_name']
            node_id = dynamic_id_var['dynamic_id']
            target_variable = dynamic_id_var['target_variable']
            try:
                value = self._resolve_node_output_value(session, node_id, target_variable)
                context[var_name] = value
            except Exception as e:
                context[var_name] = None
                self.logger.warning("Dynamic ID '%s.%s' not found: %s",
                                    node_id, target_variable, str(e))

    def _resolve_dynamic_name_variables(self, session: Session, dynamic_name_vars: List[Dict[str, Any]],
                                        context: Dict[str, Any], workflow_id: Optional[str]) -> None:
        """Resolve dynamic name-based variables"""
        for dynamic_name_var in dynamic_name_vars:
            var_name = dynamic_name_var['variable_name']
            node_name = dynamic_name_var['node_name']
            target_variable = dynamic_name_var['target_variable']
            try:
                # Convert node name to node ID
                if workflow_id:
                    node = self.node_crud.get_by_name_and_workflow(session, node_name, workflow_id)
                else:
                    node = self.node_crud.find_by_name(session, node_name)

                if node:
                    value = self._resolve_node_output_value(session, node.id, target_variable)
                    context[var_name] = value
                else:
                    context[var_name] = None
                    self.logger.warning("Node '%s' not found", node_name)
            except Exception as e:
                context[var_name] = None
                self.logger.warning("Dynamic name '%s.%s' not found: %s",
                                    node_name, target_variable, str(e))

    def _resolve_environment_variable(self, session: Session, record_id: Optional[str] = None,
                                      record_name: Optional[str] = None) -> Any:
        """Resolve environment variable value"""
        if record_id is not None:
            record = self.envar_crud.find_by_id(session, record_id)
            return record.value
        elif record_name is not None:
            record = self.envar_crud.find_by_name(session, record_name)
            return record.value
        else:
            raise ValidationError("Record ID or name is required")

    def _resolve_node_output_value(self, session: Session, node_id: str, output_key: str) -> Any:
        """Resolve node output value"""
        record = self.execution_output_crud.find_by_id(session, node_id)
        value = record.result_data.get('data', {}).get(output_key)
        return value

    def resolve_single_parameter(self, session: Session, param_value: Any,
                                 execution_id: Optional[str] = None,
                                 workflow_id: Optional[str] = None) -> Any:
        """
        Resolve a single parameter value

        Args:
            session (Session): Database session
            param_value (Any): Parameter value to resolve
            execution_id (str, optional): Execution ID
            workflow_id (str, optional): Workflow ID

        Returns:
            Any: Resolved value
        """
        try:
            # Use temporary dictionary for context resolution
            context = self.resolve_parameter_context(
                session,
                {"temp": param_value},
                execution_id=execution_id,
                workflow_id=workflow_id
            )
            return context.get("temp", param_value)

        except Exception as e:
            self.logger.warning("Failed to resolve single parameter: %s", str(e))
            return param_value

    def resolve_task_parameters(self, session: Session, task_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve task payload parameters

        Args:
            session (Session): Database session
            task_payload (Dict[str, Any]): Task payload with input_data

        Returns:
            Dict[str, Any]: Task payload with resolved parameters
        """
        if not isinstance(task_payload, dict):
            raise ValidationError("Task payload must be a dictionary")

        input_data = task_payload.get('input_data', {})
        if not input_data:
            return task_payload

        try:
            # Get context IDs
            execution_id = task_payload.get('execution_id')
            workflow_id = task_payload.get('workflow_id')

            # Resolve parameters
            resolved_context = self.resolve_parameter_context(
                session,
                input_data,
                execution_id=execution_id,
                workflow_id=workflow_id
            )

            # Update task payload
            updated_payload = task_payload.copy()
            updated_payload['input_data'] = resolved_context
            updated_payload['resolved_at'] = datetime.now(timezone.utc)

            return updated_payload

        except Exception as e:
            self.logger.error("Failed to resolve task parameters: %s", str(e))
            raise DatabaseError(f"Failed to resolve task parameters: {str(e)}")

    @retry_on_database_error(max_attempts=3)
    def cleanup_old_executions(self, session: Session, days_old: Optional[int] = None) -> int:
        """
        Clean up old executions

        Args:
            session (Session): Database session
            days_old (int, optional): Age threshold in days

        Returns:
            int: Number of deleted executions
        """
        if days_old is None:
            days_old = self.config.cleanup_execution_days

        self.logger.info("Starting cleanup of executions older than %d days", days_old)

        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)

            # Find old executions
            old_executions = self.execution_crud.filter(session, {
                'created_at__lt': cutoff_date,
                'status__in': [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED]
            })

            deleted_count = 0
            for execution in old_executions:
                try:
                    # Cascade delete will handle dependent records
                    self.execution_crud.delete_execution(session, execution.id)
                    deleted_count += 1
                except Exception as e:
                    self.logger.warning("Failed to delete execution %s: %s", execution.id, str(e))
                    continue

            self.logger.info("Successfully deleted %d old executions", deleted_count)
            return deleted_count

        except Exception as e:
            self.logger.error("Failed to cleanup old executions: %s", str(e))
            raise DatabaseError(f"Failed to cleanup old executions: {str(e)}")

    @retry_on_database_error(max_attempts=3)
    def cleanup_audit_logs(self, session: Session, days_old: Optional[int] = None) -> int:
        """
        Clean up old audit logs

        Args:
            session (Session): Database session
            days_old (int, optional): Age threshold in days

        Returns:
            int: Number of deleted logs
        """
        if days_old is None:
            days_old = self.config.cleanup_audit_days

        self.logger.info("Starting cleanup of audit logs older than %d days", days_old)

        try:
            deleted_count = self.audit_log_crud.cleanup_old_logs(session, days_old)
            self.logger.info("Successfully deleted %d old audit logs", deleted_count)
            return deleted_count
        except Exception as e:
            self.logger.error("Failed to cleanup audit logs: %s", str(e))
            raise DatabaseError(f"Failed to cleanup audit logs: {str(e)}")

    def get_system_statistics(self, session: Session) -> Dict[str, Any]:
        """
        Get system statistics

        Args:
            session (Session): Database session

        Returns:
            Dict[str, Any]: System statistics
        """
        self.logger.debug("Collecting system statistics")

        try:
            # Update metrics if enabled
            if self.config.enable_metrics:
                self._update_system_metrics(session)

            stats = {
                'executions': {
                    'total': self.metrics.executions_total,
                    'pending': self.metrics.executions_pending,
                    'running': self.metrics.executions_running,
                    'completed': self.metrics.executions_completed,
                    'failed': self.metrics.executions_failed
                },
                'workflows': {
                    'total': self.metrics.workflows_total,
                    'active': self.metrics.workflows_active,
                    'draft': self.metrics.workflows_draft
                },
                'audit_logs': {
                    'count': self.metrics.audit_logs_count
                },
                'collected_at': datetime.now(timezone.utc)
            }

            self.logger.debug("Successfully collected system statistics")
            return stats

        except Exception as e:
            self.logger.error("Failed to get system statistics: %s", str(e))
            raise DatabaseError(f"Failed to get system statistics: {str(e)}")

    def _update_system_metrics(self, session: Session) -> None:
        """Update internal system metrics"""
        try:
            # Execution metrics
            self.metrics.executions_total = self.execution_crud.count_all(session)
            self.metrics.executions_pending = self.execution_crud.count_filtered(
                session, {'status': ExecutionStatus.PENDING}
            )
            self.metrics.executions_running = self.execution_crud.count_filtered(
                session, {'status': ExecutionStatus.RUNNING}
            )
            self.metrics.executions_completed = self.execution_crud.count_filtered(
                session, {'status': ExecutionStatus.COMPLETED}
            )
            self.metrics.executions_failed = self.execution_crud.count_filtered(
                session, {'status': ExecutionStatus.FAILED}
            )

            # Workflow metrics
            self.metrics.workflows_total = self.workflow_crud.count_all(session)
            self.metrics.workflows_active = self.workflow_crud.count_filtered(
                session, {'status': WorkflowStatus.ACTIVE}
            )
            self.metrics.workflows_draft = self.workflow_crud.count_filtered(
                session, {'status': WorkflowStatus.DRAFT}
            )

            # Audit log metrics
            audit_stats = self.audit_log_crud.get_log_statistics(session)
            self.metrics.audit_logs_count = audit_stats.get('total', 0)

        except Exception as e:
            self.logger.warning("Failed to update system metrics: %s", str(e))

    def health_check(self, session: Session) -> Dict[str, Any]:
        """
        Perform system health check

        Args:
            session (Session): Database session

        Returns:
            Dict[str, Any]: Health check results
        """
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now(timezone.utc),
            'checks': {}
        }

        try:
            # Database connectivity check
            self.execution_crud.count_all(session)
            health_status['checks']['database'] = {'status': 'healthy', 'message': 'Database accessible'}
        except Exception as e:
            health_status['checks']['database'] = {'status': 'unhealthy', 'message': str(e)}
            health_status['status'] = 'unhealthy'

        # Add more health checks as needed
        try:
            # Check for stuck executions (running too long)
            stuck_threshold = datetime.now(timezone.utc) - timedelta(hours=24)
            stuck_executions = self.execution_crud.count_filtered(session, {
                'status': ExecutionStatus.RUNNING,
                'created_at__lt': stuck_threshold
            })

            if stuck_executions > 0:
                health_status['checks']['stuck_executions'] = {
                    'status': 'warning',
                    'message': f'{stuck_executions} executions running > 24 hours'
                }
            else:
                health_status['checks']['stuck_executions'] = {
                    'status': 'healthy',
                    'message': 'No stuck executions found'
                }

        except Exception as e:
            health_status['checks']['stuck_executions'] = {
                'status': 'error',
                'message': f'Failed to check: {str(e)}'
            }

        self.logger.info("Health check completed with status: %s", health_status['status'])
        return health_status