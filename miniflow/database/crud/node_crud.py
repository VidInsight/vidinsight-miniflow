from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import Session

from .base_crud import BaseCRUD
from ..models import Node
from ..decorators.auditlog_decorators import audit_create, audit_update, audit_delete, AuditMixin

class NodeCRUD(BaseCRUD[Node], AuditMixin):
    
    def __init__(self):
        super().__init__(Node)

    # ==================================================================================== BUSINESS METHODS ==
    @audit_create("nodes")
    def create_node(self, session: Session, **node_data) -> Node:
        """Create new node with audit logging."""
        return super().create(session, **node_data)

    @audit_update("nodes")
    def update_node(self, session: Session, node_id: str, **node_data) -> Node:
        """Update node with audit logging."""
        return super().update(session, node_id, **node_data)

    @audit_delete("nodes")
    def delete_node(self, session: Session, node_id: str) -> Node:
        """Delete node with audit logging."""
        return super().delete(session, node_id)

    def count_by_workflow(self, session: Session, workflow_id: str) -> int:
        """Count nodes in a specific workflow."""
        return session.query(self.model).filter(self.model.workflow_id == workflow_id).count()