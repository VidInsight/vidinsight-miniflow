from typing import List, Optional
from ..models import Workflow
from .base import BaseRepository


class WorkflowRepository(BaseRepository):
    """Repository for Workflow operations"""
    
    def __init__(self):
        super().__init__(Workflow)
    
    def get_by_name(self, name: str) -> Optional[Workflow]:
        """Get workflow by name"""
        with self.manager.get_session() as session:
            return session.query(Workflow).filter(Workflow.name == name).first()
    
    def get_by_status(self, status: str) -> List[Workflow]:
        """Get workflows by status"""
        with self.manager.get_session() as session:
            return session.query(Workflow).filter(Workflow.status == status).all()
    
    def get_active_workflows(self) -> List[Workflow]:
        """Get all active workflows"""
        return self.get_by_status('active')
    
    def activate(self, id: str) -> Optional[Workflow]:
        """Activate workflow"""
        return self.update(id, status='active')
    
    def deactivate(self, id: str) -> Optional[Workflow]:
        """Deactivate workflow"""
        return self.update(id, status='inactive')
    
    def get_with_nodes(self, id: str) -> Optional[Workflow]:
        """Get workflow with its nodes"""
        with self.manager.get_session() as session:
            return session.query(Workflow).filter(Workflow.id == id).first() 