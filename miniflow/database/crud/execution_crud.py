from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from .base_crud import BaseCRUD
from ..models import Execution, ExecutionStatus
from ..decorators import audit_create, audit_update, audit_delete, AuditMixin


class ExecutionCRUD(BaseCRUD[Execution], AuditMixin):
    """
    Execution entity CRUD operations.
    Handles workflow execution lifecycle management.
    """

    def __init__(self):
        super().__init__(Execution)
        self._init_audit()

    # ============================================================================================== BUSINESS METHODS ==

    @audit_create("executions")
    def create_execution(self, session: Session, **kwargs) -> Execution:
        """Create new execution with audit logging."""
        return super().create(session, **kwargs)

    @audit_update("executions")
    def update_execution(self, session: Session, execution_id: str, **kwargs) -> Execution:
        """Update execution with audit logging."""
        return super().update(session, execution_id, **kwargs)

    @audit_delete("executions")
    def delete_execution(self, session: Session, execution_id: str) -> Execution:
        """Delete execution with audit logging."""
        return super().delete(session, execution_id)

    # ============================================================================================== BUSINESS METHODS ==
    def get_result(self, session: Session, execution_id: str):
        execution = self.find_by_id(session, execution_id)
        return execution.results

    def get_status(self, session: Session, execution_id: str) -> ExecutionStatus:
        execution = self.find_by_id(session, execution_id)
        return execution.status