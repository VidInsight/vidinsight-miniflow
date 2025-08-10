from typing import List, Optional, Dict, Any, Union
from sqlalchemy.orm import Session

from .base_crud import BaseCRUD
from ..models import ArchivedExecution, Execution, ExecutionStatus, ArchiveReason
from ..decorators import audit_create, audit_update, audit_delete, AuditMixin


class ArchivedExecutionCRUD(BaseCRUD[ArchivedExecution], AuditMixin):
    """
    ArchivedExecution entity CRUD operations.
    Handles historical execution data management and cleanup.
    """

    def __init__(self):
        super().__init__(ArchivedExecution)
        self._init_audit()

    # ==================================================================================== BUSINESS METHODS ==

    @audit_create("archived_executions")
    def create_archived_execution(self, session: Session, **kwargs) -> ArchivedExecution:
        """Create new archived execution with audit logging."""
        return super().create(session, **kwargs)

    @audit_update("archived_executions")
    def update_archived_execution(self, session: Session, archived_execution_id: str, **kwargs) -> ArchivedExecution:
        """Update archived execution with audit logging."""
        return super().update(session, archived_execution_id, **kwargs)

    @audit_delete("archived_executions")
    def delete_archived_execution(self, session: Session, archived_execution_id: str) -> ArchivedExecution:
        """Delete archived execution with audit logging."""
        return super().delete(session, archived_execution_id)