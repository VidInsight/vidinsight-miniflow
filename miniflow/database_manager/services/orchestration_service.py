from typing import List, Dict, Any, Optional
from ..repositories import ExecutionInputRepository, ExecutionOutputRepository
from .execution_service import ExecutionService
from .workflow_service import WorkflowService


class OrchestrationService:
    """Service for workflow orchestration and scheduling"""
    
    def __init__(self):
        self.input_repo = ExecutionInputRepository()
        self.output_repo = ExecutionOutputRepository()
        self.execution_service = ExecutionService()
        self.workflow_service = WorkflowService()
    
    def get_ready_tasks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get tasks that are ready to execute"""
        ready_inputs = self.input_repo.get_ready_inputs()
        
        tasks = []
        for input_item in ready_inputs[:limit]:
            execution_status = self.execution_service.get_execution_status(input_item.execution_id)
            if not execution_status:
                continue
            
            # Get node information
            workflow_structure = self.workflow_service.get_workflow_structure(
                execution_status['execution'].workflow_id
            )
            
            node = next((n for n in workflow_structure['nodes'] if n.id == input_item.node_id), None)
            if not node:
                continue
            
            tasks.append({
                'execution_id': input_item.execution_id,
                'node_id': input_item.node_id,
                'node_name': node.name,
                'node_type': node.type,
                'node_config': node.config,
                'input_data': input_item.inputs,
                'priority': getattr(input_item, 'priority', 0)
            })
        
        return tasks
    
    def execute_workflow(self, workflow_id: str, context: Dict[str, Any] = None) -> str:
        """Start workflow execution"""
        # Validate workflow first
        validation = self.workflow_service.validate_workflow(workflow_id)
        if not validation['valid']:
            raise ValueError(f"Invalid workflow: {validation['errors']}")
        
        # Create execution
        execution = self.execution_service.create_execution(workflow_id, context)
        
        # Start execution
        self.execution_service.start_execution(execution.id)
        
        return execution.id
    
    def get_execution_progress(self, execution_id: str) -> Dict[str, Any]:
        """Get execution progress summary"""
        status = self.execution_service.get_execution_status(execution_id)
        if not status:
            return None
        
        total_nodes = status['stats']['total_inputs']
        completed_nodes = status['stats']['completed_outputs']
        failed_nodes = status['stats']['failed_outputs']
        
        progress_percentage = (completed_nodes / total_nodes * 100) if total_nodes > 0 else 0
        
        return {
            'execution_id': execution_id,
            'status': status['execution'].status,
            'progress_percentage': round(progress_percentage, 2),
            'total_nodes': total_nodes,
            'completed_nodes': completed_nodes,
            'failed_nodes': failed_nodes,
            'is_completed': completed_nodes + failed_nodes == total_nodes,
            'started_at': status['execution'].started_at,
            'ended_at': status['execution'].ended_at
        }
    
    def get_workflow_statistics(self, workflow_id: str) -> Dict[str, Any]:
        """Get workflow execution statistics"""
        from ..repositories import ExecutionRepository
        execution_repo = ExecutionRepository()
        
        executions = execution_repo.get_by_workflow(workflow_id)
        
        stats = {
            'total_executions': len(executions),
            'successful_executions': len([e for e in executions if e.status == 'completed']),
            'failed_executions': len([e for e in executions if e.status == 'failed']),
            'running_executions': len([e for e in executions if e.status == 'running']),
            'pending_executions': len([e for e in executions if e.status == 'pending'])
        }
        
        # Calculate success rate
        if stats['total_executions'] > 0:
            stats['success_rate'] = round(
                stats['successful_executions'] / stats['total_executions'] * 100, 2
            )
        else:
            stats['success_rate'] = 0
        
        return stats 