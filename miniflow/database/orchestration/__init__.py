from .workflow_orchestration import WorkflowOrchestrator
from .script_orchestration import ScriptOrchestrator
from .envar_orchestration import EnvarOrchestrator
from .node_orchestrator import NodeOrchestrator
from .edge_orchestrator import EdgeOrchestrator
from .execution_orchestration import ExecutionOrchestrator
from .execution_input_orchestration import ExecutionInputOrchestrator
from .execution_output_orchestration import ExecutionOutputOrchestrator
from .scheduler_orchestration import SchedulerOrchestrator


class DatabaseOrchestrator:
    """
    Central orchestrator providing unified access to all database orchestration operations.
    
    This class serves as the main entry point for all database operations in the miniflow
    system. It provides access to specialized orchestrators for different entities and
    includes bridge methods for scheduler integration.
    """
    
    workflow_orchestrator = WorkflowOrchestrator()
    script_orchestrator = ScriptOrchestrator()
    envar_orchestrator = EnvarOrchestrator()
    node_orchestrator = NodeOrchestrator()
    edge_orchestrator = EdgeOrchestrator()
    execution_orchestrator = ExecutionOrchestrator()
    execution_input_orchestrator = ExecutionInputOrchestrator()
    execution_output_orchestrator = ExecutionOutputOrchestrator()
    scheduler_orchestrator = SchedulerOrchestrator()
    
    # ============================== SCHEDULER BRIDGE METHODS ==============================
    # These methods bridge Input/Output monitors to SchedulerOrchestrator
    
    def get_ready_tasks(self, session, limit: int = 50):
        """
        Bridge method to get ready tasks for Input Monitor.
        
        Args:
            session: Database session for transaction management
            limit (int): Maximum number of tasks to retrieve (default: 50)
            
        Returns:
            List of ready tasks from scheduler orchestrator
            
        Raises:
            DatabaseError: If database operation fails
        """
        return self.scheduler_orchestrator.get_ready_tasks(session, limit)
    
    def create_task_payload(self, session, task):
        """
        Bridge method to create task payload for Input Monitor.
        
        Args:
            session: Database session for transaction management
            task: Task object to create payload for
            
        Returns:
            Dict containing task payload data
            
        Raises:
            ValidationError: If task data is invalid
            DatabaseError: If database operation fails
        """
        return self.scheduler_orchestrator.create_task_payload(task)
    
    def remove_completed_tasks(self, session, task_ids):
        """
        Bridge method to remove completed tasks for Input Monitor.
        
        Args:
            session: Database session for transaction management
            task_ids: List of task IDs to remove
            
        Returns:
            Number of tasks successfully removed
            
        Raises:
            DatabaseError: If database operation fails
        """
        return self.scheduler_orchestrator.delete_completed_tasks(session, task_ids)
    
    def process_execution_result(self, session, result):
        """
        Bridge method to process execution result for Output Monitor.
        
        Args:
            session: Database session for transaction management
            result: Execution result data to process
            
        Returns:
            Processed result data
            
        Raises:
            ValidationError: If result data is invalid
            DatabaseError: If database operation fails
        """
        return self.scheduler_orchestrator.process_execution_result(session, result)