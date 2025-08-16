from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from .base_crud import BaseCRUD
from ..models import ExecutionInput
from ..decorators.auditlog_decorators import audit_create, audit_update, audit_delete, AuditMixin


class ExecutionInputCRUD(BaseCRUD[ExecutionInput], AuditMixin):
    """
    ExecutionInput entity CRUD operations.
    Handles task queue management and ready task optimization.
    """

    def __init__(self):
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
        """Count tasks that are ready to execute (dependency_count = 0)."""
        filters = {'dependency_count': 0}
        if execution_id:
            filters['execution_id'] = execution_id
        return self.count_filtered(session, filters)

    def count_by_execution(self, session: Session, execution_id: str) -> int:
        """Count execution inputs for a specific execution."""
        return self.count_filtered(session, {'execution_id': execution_id})

    def get_by_execution(self, session: Session, execution_id: str) -> List[ExecutionInput]:
        """Get all execution inputs for a specific execution."""
        return self.filter(session, {'execution_id': execution_id}, order_by_field='priority')

    def get_by_execution_and_node(self, session: Session, execution_id: str, node_id: str) -> Optional[ExecutionInput]:
        """Get execution input for a specific execution and node."""
        execution_inputs = self.filter(session, {
            'execution_id': execution_id,
            'node_id': node_id
        })
        return execution_inputs[0] if execution_inputs else None

    def get_ready_tasks(self, session: Session, execution_id: str = None, limit: int = 50) -> List[ExecutionInput]:
        """Get tasks that are ready to execute, ordered by priority (desc)."""
        filters = {'dependency_count': 0}
        if execution_id:
            filters['execution_id'] = execution_id
        
        # Base CRUD filter kullan, sonra manuel sırala
        tasks = self.filter(session, filters, limit=1000, order_by_field='priority')
        # Yüksek priority önce gelsin
        tasks_sorted = sorted(tasks, key=lambda x: x.priority, reverse=True)
        return tasks_sorted[:limit]

    def get_node_params(self, session: Session, execution_input_id: str) -> Dict[str, Any]:
        """Get node parameters for a specific execution input."""
        execution_input = self.find_by_id(session, execution_input_id)
        return execution_input.node_params

    # ==================================================================================== SIMPLE BUSINESS LOGIC ==

    def get_tasks_and_increase_others_priority(self, session: Session, 
                                             execution_id: str = None,
                                             batch_size: int = 10,
                                             priority_increment: int = 1) -> List[ExecutionInput]:
        """
        Basit: Hazır taskları çek, geri kalanın priority'sini artır.
        """
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
        """
        Verilen node_id ve execution_id'ye sahip kaydın dependency_count'ını 1 azalt.
        """
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