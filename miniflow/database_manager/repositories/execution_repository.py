from typing import List, Optional
from datetime import datetime
from ..models import Execution
from .base import BaseRepository


class ExecutionRepository(BaseRepository):
    """Repository for Execution operations"""
    
    def __init__(self):
        super().__init__(Execution)
    
    def get_by_workflow(self, workflow_id: str) -> List[Execution]:
        """Get executions by workflow ID"""
        with self.manager.get_session() as session:
            return session.query(Execution).filter(Execution.workflow_id == workflow_id).all()
    
    def get_by_status(self, status: str) -> List[Execution]:
        """Get executions by status"""
        with self.manager.get_session() as session:
            return session.query(Execution).filter(Execution.status == status).all()
    
    def get_running_executions(self) -> List[Execution]:
        """Get all running executions"""
        return self.get_by_status('running')
    
    def start_execution(self, id: str) -> Optional[Execution]:
        """Start execution"""
        return self.update(id, status='running', started_at=datetime.utcnow())
    
    def complete_execution(self, id: str, results: str = None) -> Optional[Execution]:
        """Complete execution"""
        update_data = {'status': 'completed', 'ended_at': datetime.utcnow()}
        if results:
            update_data['results'] = results
        return self.update(id, **update_data) 