from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import Session

from .base_crud import BaseCRUD
from ..models import Edge, Node
from ..decorators.auditlog_decorators import audit_create, audit_update, audit_delete, AuditMixin


class EdgeCRUD(BaseCRUD[Edge]):
    
    def __init__(self):
        super().__init__(Edge)

        # ==================================================================================== BUSINESS METHODS ==

    @audit_create("edges")
    def create_edge(self, session: Session, **edge_data) -> Edge:
        """Create new edge with audit logging."""
        return super().create(session, **edge_data)

    @audit_update("edges")
    def update_edge(self, session: Session, edge_id: str, **edge_data) -> Edge:
        """Update edge with audit logging."""
        return super().update(session, edge_id, **edge_data)

    @audit_delete("edges")
    def delete_edge(self, session: Session, edge_id: str) -> Edge:
        """Delete edge with audit logging."""
        return super().delete(session, edge_id)

    def get_edges_by_workflow(self, session, workflow_id):
        from ..models import Node
        from sqlalchemy import select
        node_ids = [node.id for node in session.query(Node).filter_by(workflow_id=workflow_id).all()]
        stmt = select(self.model).where(
            (self.model.from_node_id.in_(node_ids)) | (self.model.to_node_id.in_(node_ids))
        )
        return list(session.execute(stmt).scalars().all())

    def get_dependency_count(self, session: Session, node_id: str) -> int:
        """
        Bir node'un kaç başka node'a bağımlı olduğunu hesapla
        (kaç edge'in to_node_id'si bu node'a eşit)
        """
        stmt = select(func.count(self.model.id)).where(self.model.to_node_id == node_id)
        return session.execute(stmt).scalar_one() or 0