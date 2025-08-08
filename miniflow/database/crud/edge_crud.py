from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from .base_crud import BaseCRUD
from ..models import Edge, Node
from ..decorators import audit_create, audit_update, audit_delete, AuditMixin
from ...exceptions import ValidationError, BusinessLogicError


class EdgeCRUD(BaseCRUD[Edge], AuditMixin):
    """
    Edge entity CRUD operations.
    Handles workflow connection and dependency management.
    """
    
    def __init__(self):
        super().__init__(Edge)
        self._init_audit()

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