from typing import List, Dict, Any, Optional
from datetime import datetime
from ..repositories import (
    ExecutionRepository, ExecutionInputRepository, 
    ExecutionOutputRepository, WorkflowRepository
)
from ..models import Execution


class ExecutionService:
    """Service for execution business logic"""
    
    def __init__(self):
        self.execution_repo = ExecutionRepository()
        self.input_repo = ExecutionInputRepository()
        self.output_repo = ExecutionOutputRepository()
        self.workflow_repo = WorkflowRepository()
    
    def create_execution(self, workflow_id: str, context: Dict[str, Any] = None) -> Execution:
        """Create new execution for workflow"""
        workflow = self.workflow_repo.get_by_id(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        return self.execution_repo.create(
            workflow_id=workflow_id,
            status='pending',
            context=str(context or {}),
            started_at=datetime.utcnow()
        )
    
    def start_execution(self, execution_id: str) -> Optional[Execution]:
        """Start execution and initialize input queue"""
        execution = self.execution_repo.get_by_id(execution_id)
        if not execution:
            return None
        
        # Initialize execution inputs (queue items)
        self._initialize_execution_inputs(execution_id)
        
        # Update execution status
        return self.execution_repo.start_execution(execution_id)
    
    def get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """Get detailed execution status"""
        execution = self.execution_repo.get_by_id(execution_id)
        if not execution:
            return None
        
        inputs = self.input_repo.get_by_execution(execution_id)
        outputs = self.output_repo.get_by_execution(execution_id)
        
        return {
            'execution': execution,
            'inputs': inputs,
            'outputs': outputs,
            'stats': {
                'total_inputs': len(inputs),
                'ready_inputs': len([i for i in inputs if i.status == 'ready']),
                'completed_outputs': len([o for o in outputs if o.status == 'success']),
                'failed_outputs': len([o for o in outputs if o.status == 'failed'])
            }
        }
    
    def _initialize_execution_inputs(self, execution_id: str):
        """Initialize execution input queue from workflow structure"""
        execution = self.execution_repo.get_by_id(execution_id)
        if not execution:
            return
        
        # Get workflow nodes to create queue items
        from .workflow_service import WorkflowService
        workflow_service = WorkflowService()
        structure = workflow_service.get_workflow_structure(execution.workflow_id)
        
        if not structure:
            return
        
        # Create input queue items for each node
        for node in structure['nodes']:
            # Calculate dependencies for this node
            dependencies = len([
                edge for edge in structure['edges'] 
                if edge.to_node_id == node.id
            ])
            
            self.input_repo.create(
                execution_id=execution_id,
                node_id=node.id,
                dependency_count=dependencies,
                status='pending' if dependencies > 0 else 'ready',
                inputs='{}'
            ) 