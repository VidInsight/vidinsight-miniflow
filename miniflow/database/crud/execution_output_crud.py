from typing import List, Optional, Dict, Any, Union
from sqlalchemy.orm import Session

from .base_crud import BaseCRUD
from ..models import ExecutionOutput, ExecutionOutputStatus, Execution, Node
from ..decorators.auditlog_decorators import audit_create, audit_update, audit_delete, AuditMixin


class ExecutionOutputCRUD(BaseCRUD[ExecutionOutput], AuditMixin):
    """
    ExecutionOutput entity CRUD operations.
    Handles result collection and dynamic parameter resolution.
    """

    def __init__(self):
        super().__init__(ExecutionOutput)
        self._init_audit()

    # ==================================================================================== BUSINESS METHODS ==

    @audit_create("execution_outputs")
    def create_execution_output(self, session: Session, **kwargs) -> ExecutionOutput:
        """Create new execution output with audit logging."""
        return super().create(session, **kwargs)

    @audit_update("execution_outputs")
    def update_execution_output(self, session: Session, execution_output_id: str, **kwargs) -> ExecutionOutput:
        """Update execution output with audit logging."""
        return super().update(session, execution_output_id, **kwargs)

    @audit_delete("execution_outputs")
    def delete_execution_output(self, session: Session, execution_output_id: str) -> ExecutionOutput:
        """Delete execution output with audit logging."""
        return super().delete(session, execution_output_id)