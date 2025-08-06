from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from .base_crud import BaseCRUD
from ..models import Workflow, WorkflowStatus
from ..decorators import audit_create, audit_update, audit_delete, AuditMixin
from ...exceptions import ValidationError, BusinessLogicError


class WorkflowCRUD(BaseCRUD[Workflow], AuditMixin):
    """
    Workflow entity CRUD operations.
    Handles workflow definition and lifecycle management with validation.
    """

    def __init__(self):
        super().__init__(Workflow)
        self._init_audit()

    # ==================================================================================== BUSINESS METHODS ==

    @audit_create("workflows")
    def create_workflow(self, session: Session, **workflow_data) -> Workflow:
        """Create new workflow with name uniqueness validation and audit logging."""
        if self.check_name_exists(session, workflow_data['name']):
            raise ValidationError(f"Workflow with name '{workflow_data.get('name')}' already exists")

        return super().create(session, **workflow_data)

    @audit_update("workflows")
    def delete_workflow(self, session: Session, workflow_id: str, **workflow_data) -> Workflow:
        """Update workflow with name uniqueness validation and audit logging."""
        if workflow_data.get('name'):
            old_workflow = self.find_by_id(session, workflow_id)
            if workflow_data['name'] != old_workflow.name:
                if self.check_name_exists(session, workflow_data['name']):
                    raise ValidationError(f"Workflow with name '{workflow_data['name']}' already exists")
        
        return super().update(session, workflow_id, **workflow_data)

    @audit_delete("workflows")
    def update_workflow(self, session: Session, workflow_id: str) -> Workflow:
        """Delete workflow with audit logging."""
        return super().delete(session, workflow_id)
