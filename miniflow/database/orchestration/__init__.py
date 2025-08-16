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
        """Bridge method: Get ready tasks for Input Monitor"""
        return self.scheduler_orchestrator.get_ready_tasks(session, limit)
    
    def create_task_payload(self, session, task):
        """Bridge method: Create task payload for Input Monitor"""
        return self.scheduler_orchestrator.create_task_payload(task)
    
    def remove_completed_tasks(self, session, task_ids):
        """Bridge method: Remove completed tasks for Input Monitor"""
        return self.scheduler_orchestrator.delete_completed_tasks(session, task_ids)
    
    def process_execution_result(self, session, result):
        """Bridge method: Process execution result for Output Monitor"""
        return self.scheduler_orchestrator.process_execution_result(session, result)