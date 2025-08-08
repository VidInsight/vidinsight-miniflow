from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from .base_crud import BaseCRUD
from ..models import EnvironmentVariable
from ..decorators import audit_create, audit_update, audit_delete, AuditMixin
from ...exceptions import ValidationError, BusinessLogicError


class EnvironmentVariableCRUD(BaseCRUD[EnvironmentVariable], AuditMixin):
    """
    Edge entity CRUD operations.
    Handles workflow connection and dependency management.
    """

    def __init__(self):
        super().__init__(EnvironmentVariable)
        self._init_audit()

    # ============================================================================================== BUSINESS METHODS ==

    @audit_create("edges")
    def create_environment_variable(self, session: Session, **edge_data) -> EnvironmentVariable:
        """Create new edge with audit logging."""
        return super().create(session, **edge_data)

    @audit_update("edges")
    def update_environment_variable(self, session: Session, edge_id: str, **edge_data) -> EnvironmentVariable:
        """Update edge with audit logging."""
        return super().update(session, edge_id, **edge_data)

    @audit_delete("edges")
    def delete_environment_variable(self, session: Session, edge_id: str) -> EnvironmentVariable:
        """Delete edge with audit logging."""
        return super().delete(session, edge_id)