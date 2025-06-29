from typing import List, Optional
from ..models import Edge
from .base import BaseRepository


class EdgeRepository(BaseRepository):
    """Repository for Edge operations"""
    
    def __init__(self):
        super().__init__(Edge)
    
    def get_by_workflow(self, workflow_id: str) -> List[Edge]:
        """Get edges by workflow ID"""
        with self.manager.get_session() as session:
            return session.query(Edge).filter(Edge.workflow_id == workflow_id).all()
    
    def get_by_from_node(self, from_node_id: str) -> List[Edge]:
        """Get edges by from_node_id"""
        with self.manager.get_session() as session:
            return session.query(Edge).filter(Edge.from_node_id == from_node_id).all()
    
    def get_by_to_node(self, to_node_id: str) -> List[Edge]:
        """Get edges by to_node_id"""
        with self.manager.get_session() as session:
            return session.query(Edge).filter(Edge.to_node_id == to_node_id).all()
    
    def delete_by_workflow(self, workflow_id: str) -> int:
        """Delete all edges in a workflow"""
        with self.manager.get_session() as session:
            deleted = session.query(Edge).filter(Edge.workflow_id == workflow_id).delete()
            session.commit()
            return deleted 