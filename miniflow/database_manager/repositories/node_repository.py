from typing import List, Optional
from ..models import Node
from .base import BaseRepository


class NodeRepository(BaseRepository):
    """Repository for Node operations"""
    
    def __init__(self):
        super().__init__(Node)
    
    def get_by_workflow(self, workflow_id: str) -> List[Node]:
        """Get nodes by workflow ID"""
        with self.manager.get_session() as session:
            return session.query(Node).filter(Node.workflow_id == workflow_id).all()
    
    def get_by_type(self, node_type: str) -> List[Node]:
        """Get nodes by type"""
        with self.manager.get_session() as session:
            return session.query(Node).filter(Node.type == node_type).all()
    
    def get_by_workflow_and_name(self, workflow_id: str, name: str) -> Optional[Node]:
        """Get node by workflow ID and name"""
        with self.manager.get_session() as session:
            return session.query(Node).filter(
                Node.workflow_id == workflow_id,
                Node.name == name
            ).first()
    
    def delete_by_workflow(self, workflow_id: str) -> int:
        """Delete all nodes in a workflow"""
        with self.manager.get_session() as session:
            deleted = session.query(Node).filter(Node.workflow_id == workflow_id).delete()
            session.commit()
            return deleted 