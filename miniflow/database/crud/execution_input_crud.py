from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from .base_crud import BaseCRUD
from ..models import ExecutionInput
from ..decorators.auditlog_decorators import (
    audit_create, 
    audit_update, 
    audit_delete, 
    AuditMixin
)
from ...exceptions import (
    ValidationError, 
    CRUDException
)


class ExecutionInputCRUD(BaseCRUD[ExecutionInput], AuditMixin):
    """
    ExecutionInput entity CRUD operations.
    Handles task queue management and ready task optimization.
    """

    def __init__(self):
        """Initialize ExecutionInputCRUD with ExecutionInput model and audit capabilities."""
        super().__init__(ExecutionInput)
        self._init_audit()

    # ==================================================================================== BUSINESS METHODS ==

    @audit_create("execution_inputs")
    def create_execution_input(self, session: Session, **kwargs) -> ExecutionInput:
        """Create new execution input with audit logging."""
        return super().create(session, **kwargs)

    @audit_update("execution_inputs")
    def update_execution_input(self, session: Session, execution_input_id: str, **kwargs) -> ExecutionInput:
        """Update execution input with audit logging."""
        return super().update(session, execution_input_id, **kwargs)

    @audit_delete("execution_inputs")
    def delete_execution_input(self, session: Session, execution_input_id: str) -> ExecutionInput:
        """Delete execution input with audit logging."""
        return super().delete(session, execution_input_id)

    def count_ready_tasks(self, session: Session, execution_id: str = None) -> int:
        """Count tasks ready for execution (zero dependencies)."""
        filters = {'dependency_count': 0}
        if execution_id:
            filters['execution_id'] = execution_id
        return self.count_filtered(session, filters)

    def count_by_execution(self, session: Session, execution_id: str) -> int:
        """Count total execution inputs for a specific execution."""
        return self.count_filtered(session, {'execution_id': execution_id})

    def get_by_execution(self, session: Session, execution_id: str) -> List[ExecutionInput]:
        """Get all execution inputs for a specific execution, ordered by priority."""
        return self.filter(session, {'execution_id': execution_id}, order_by_field='priority')

    def get_by_execution_and_node(self, session: Session, execution_id: str, node_id: str) -> Optional[ExecutionInput]:
        """Get execution input for a specific execution and node combination."""
        execution_inputs = self.filter(session, {
            'execution_id': execution_id,
            'node_id': node_id
        })
        return execution_inputs[0] if execution_inputs else None

    def get_ready_tasks(self, session: Session, execution_id: str = None, limit: int = 50) -> List[ExecutionInput]:
        """Get tasks ready for execution, sorted by priority (highest first)."""
        # Input validation
        if limit <= 0:
            raise ValidationError("limit must be a positive integer")
        
        filters = {'dependency_count': 0}
        if execution_id:
            filters['execution_id'] = execution_id
        
        # SQL'de direkt sıralama yap, memory efficient
        return self.filter(session, filters, limit=limit, order_by_field='priority')

    def get_node_params(self, session: Session, execution_input_id: str) -> Dict[str, Any]:
        """Get cached node parameters for a specific execution input."""
        # BaseCRUD handles validation and error handling
        execution_input = self.find_by_id(session, execution_input_id)
        if not execution_input:
            raise CRUDException(f"ExecutionInput not found (get_node_params): {execution_input_id}")
        return execution_input.node_params

    # ==================================================================================== SIMPLE BUSINESS LOGIC ==

    def get_tasks_and_increase_others_priority(self, session: Session, 
                                             execution_id: str = None,
                                             batch_size: int = 10,
                                             priority_increment: int = 1) -> List[ExecutionInput]:
        """Get ready tasks for execution and increase priority of remaining tasks."""
        # 1. Hazır taskları çek
        ready_tasks = self.get_ready_tasks(session, execution_id, limit=1000)
        
        if not ready_tasks:
            return []
        
        # 2. Seçilen ve kalan taskları ayır
        selected_tasks = ready_tasks[:batch_size]
        remaining_tasks = ready_tasks[batch_size:]
        
        # 3. Kalan taskların priority'sini artır
        if remaining_tasks and priority_increment > 0:
            for task in remaining_tasks:
                self.update_execution_input(session, task.id, priority=task.priority + priority_increment)
        
        return selected_tasks

    def decrease_dependency_count(self, session: Session, node_id: str, execution_id: str) -> int:
        """Decrease dependency count for a specific node in an execution."""
        # Bu node ve execution için execution input'ı bul
        execution_inputs = self.filter(session, {
            'execution_id': execution_id, 
            'node_id': node_id
        })
        
        if not execution_inputs:
            return 0
        
        # İlk (ve tek olması gereken) kaydı güncelle
        execution_input = execution_inputs[0]
        
        if execution_input.dependency_count > 0:
            new_count = execution_input.dependency_count - 1
            self.update_execution_input(session, execution_input.id, dependency_count=new_count)
            return 1
        
        return 0