from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import Session

from .base_crud import BaseCRUD
from ..models import Edge, Node, Workflow
from ..decorators.auditlog_decorators import audit_create, audit_update, audit_delete, AuditMixin


class EdgeCRUD(BaseCRUD[Edge], AuditMixin):
    
    def __init__(self):
        super().__init__(Edge)

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

    def get_by_workflow(self, session: Session, workflow_id: str) -> List[Workflow]:
        return self.filter(session, {'workflow_id': workflow_id})

    def count_dependencies(self, session: Session, node_id: str) -> int:
        """
        Bir node'un kaç başka node'a bağımlı olduğunu hesapla
        (kaç edge'in to_node_id'si bu node'a eşit)
        """
        return self.count_filtered(session, {"to_node_id": node_id})

    def count_dependants(self, session: Session, node_id: str) -> int:
        """
        Bir node'a kaç başka node'un bağımlı olduğunu hesapla
        (kaç edge'in from_node_id'si bu node'a eşit)
        """
        return self.count_filtered(session, {"from_node_id": node_id})

    def count_by_workflow(self, session: Session, workflow_id: str) -> int:
        return self.count_filtered(session, {"workflow_id": workflow_id})

    def get_dependencies(self, session: Session, node_id: str) -> List[Node]:
        return self.filter(session, {'to_node_id': node_id})

    def get_dependants(self, session: Session, node_id: str) -> List[Node]:
        return self.filter(session, {'from_node_id': node_id})

    def check_edge_exists(self, session: Session, workflow_id: str, from_node_id: str, to_node_id: str) -> bool:
        """Check if an edge already exists between two nodes in a workflow"""
        return self.count_filtered(session, {
            'workflow_id': workflow_id,
            'from_node_id': from_node_id,
            'to_node_id': to_node_id
        }) > 0