from typing import List, Optional
from ..models import Trigger
from .base import BaseRepository


class TriggerRepository(BaseRepository):
    """Repository for Trigger operations"""
    
    def __init__(self):
        super().__init__(Trigger)
    
    def get_by_workflow(self, workflow_id: str) -> List[Trigger]:
        """Get triggers by workflow ID"""
        with self.manager.get_session() as session:
            return session.query(Trigger).filter(Trigger.workflow_id == workflow_id).all()
    
    def get_by_type(self, trigger_type: str) -> List[Trigger]:
        """Get triggers by type"""
        with self.manager.get_session() as session:
            return session.query(Trigger).filter(Trigger.trigger_type == trigger_type).all()
    
    def get_active_triggers(self) -> List[Trigger]:
        """Get all active triggers"""
        with self.manager.get_session() as session:
            return session.query(Trigger).filter(Trigger.is_active == 1).all()
    
    def activate(self, id: str) -> Optional[Trigger]:
        """Activate trigger"""
        return self.update(id, is_active=1)
    
    def deactivate(self, id: str) -> Optional[Trigger]:
        """Deactivate trigger"""
        return self.update(id, is_active=0) 