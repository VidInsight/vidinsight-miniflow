from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from .base_crud import BaseCRUD
from ..models import ExecutionInput
from ..decorators.auditlog_decorators import audit_create, audit_update, audit_delete, AuditMixin


class ExecutionInputCRUD(BaseCRUD[ExecutionInput], AuditMixin):
    """
    ExecutionInput entity CRUD operations.
    Handles task queue management and ready task optimization.
    """

    def __init__(self):
        super().__init__(ExecutionInput)
        self._init_audit()

    # ==================================================================================== BUSINESS METHODS ==

    @audit_create("execution_inputs")
    def create_execution_input(self, session: Session, **kwargs) -> ExecutionInput:
        """Create new execution input with audit logging."""
        return super().create(session, **kwargs)

    @audit_update("execution_inputs")
    def update_execution_input(self, session: Session, execution_input_id: str, **kwargs) -> ExecutionInput:
        """Update execution input with audit logging."""
        return super().update(session, execution_input_id, **kwargs)

    @audit_delete("execution_inputs")
    def delete_execution_input(self, session: Session, execution_input_id: str) -> ExecutionInput:
        """Delete execution input with audit logging."""
        return super().delete(session, execution_input_id)

    def count_ready_tasks(self, session: Session) -> int:
        """Count ready tasks (dependency_count = 0)."""
        return session.query(ExecutionInput).filter(ExecutionInput.dependency_count == 0).count()