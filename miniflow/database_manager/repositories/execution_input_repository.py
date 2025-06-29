from typing import List, Optional
from ..models import ExecutionInput
from .base import BaseRepository


class ExecutionInputRepository(BaseRepository):
    """Repository for ExecutionInput operations"""
    
    def __init__(self):
        super().__init__(ExecutionInput)
    
    def get_by_execution(self, execution_id: str) -> List[ExecutionInput]:
        """Get inputs by execution ID"""
        with self.manager.get_session() as session:
            return session.query(ExecutionInput).filter(ExecutionInput.execution_id == execution_id).all()
    
    def get_by_status(self, status: str) -> List[ExecutionInput]:
        """Get inputs by status"""
        with self.manager.get_session() as session:
            return session.query(ExecutionInput).filter(ExecutionInput.status == status).all()
    
    def get_ready_inputs(self) -> List[ExecutionInput]:
        """Get ready inputs (dependency_count = 0)"""
        with self.manager.get_session() as session:
            return session.query(ExecutionInput).filter(
                ExecutionInput.status == 'pending',
                ExecutionInput.dependency_count == 0
            ).all()
    
    def decrease_dependency(self, id: str) -> Optional[ExecutionInput]:
        """Decrease dependency count by 1"""
        input_item = self.get_by_id(id)
        if input_item and input_item.dependency_count > 0:
            new_count = input_item.dependency_count - 1
            status = 'ready' if new_count == 0 else 'pending'
            return self.update(id, dependency_count=new_count, status=status)
        return input_item 