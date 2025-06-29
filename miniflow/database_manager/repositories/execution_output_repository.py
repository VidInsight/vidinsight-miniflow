from typing import List, Optional
from ..models import ExecutionOutput
from .base import BaseRepository


class ExecutionOutputRepository(BaseRepository):
    """Repository for ExecutionOutput operations"""
    
    def __init__(self):
        super().__init__(ExecutionOutput)
    
    def get_by_execution(self, execution_id: str) -> List[ExecutionOutput]:
        """Get outputs by execution ID"""
        with self.manager.get_session() as session:
            return session.query(ExecutionOutput).filter(ExecutionOutput.execution_id == execution_id).all()
    
    def get_by_node(self, node_id: str) -> List[ExecutionOutput]:
        """Get outputs by node ID"""
        with self.manager.get_session() as session:
            return session.query(ExecutionOutput).filter(ExecutionOutput.node_id == node_id).all()
    
    def get_by_status(self, status: str) -> List[ExecutionOutput]:
        """Get outputs by status"""
        with self.manager.get_session() as session:
            return session.query(ExecutionOutput).filter(ExecutionOutput.status == status).all()
    
    def get_successful_outputs(self, execution_id: str) -> List[ExecutionOutput]:
        """Get successful outputs for an execution"""
        with self.manager.get_session() as session:
            return session.query(ExecutionOutput).filter(
                ExecutionOutput.execution_id == execution_id,
                ExecutionOutput.status == 'success'
            ).all() 