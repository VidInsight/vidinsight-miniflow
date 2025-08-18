from sqlalchemy.orm import Session

from .base_crud import BaseCRUD
from ..models import Workflow, WorkflowStatus
from ..decorators.auditlog_decorators import (
    audit_create, 
    audit_update, 
    audit_delete, 
    AuditMixin
)
from ...exceptions import (
    ValidationError, 
    CRUDException
)


class WorkflowCRUD(BaseCRUD[Workflow], AuditMixin):
    """
    Workflow entity CRUD operations.
    Manages workflow lifecycle with priority and status controls.
    """

    def __init__(self):
        """Initialize WorkflowCRUD with Workflow model and audit capabilities."""
        super().__init__(Workflow)

    @audit_create("workflows")
    def create_workflow(self, session: Session, **workflow_data) -> Workflow:
        """Create new workflow with name uniqueness validation and audit logging."""
        return super().create(session, **workflow_data)

    @audit_update("workflows")
    def update_workflow(self, session: Session, workflow_id: str, **workflow_data) -> Workflow:
        """Update workflow with name uniqueness validation and audit logging."""
        return super().update(session, workflow_id, **workflow_data)

    @audit_delete("workflows")
    def delete_workflow(self, session: Session, workflow_id: str) -> Workflow:
        """Delete workflow with audit logging."""
        return super().delete(session, workflow_id)

    def set_status(self, session: Session, workflow_id: str, new_status: WorkflowStatus) -> Workflow:
        """Update workflow status (ACTIVE/DRAFT) for execution control."""
        # Input validation
        if not isinstance(new_status, WorkflowStatus):
            raise ValidationError(f"Invalid status type: {type(new_status).__name__}")
        
        # BaseCRUD will handle the database operations and error handling
        workflow = self.find_by_id(session, workflow_id)
        if not workflow:
            raise CRUDException(f"Workflow not found (set_status): {workflow_id}")
        
        workflow.status = new_status
        session.flush()
        return workflow

    def set_priority(self, session: Session, workflow_id: str, priority: int) -> Workflow:
        """Set workflow execution priority (0-10) for scheduling optimization."""
        # Input validation
        if not isinstance(priority, int) or not 0 <= priority <= 10:
            raise ValidationError("Priority must be an integer between 0 and 10")

        # BaseCRUD will handle the database operations and error handling
        workflow = self.find_by_id(session, workflow_id)
        if not workflow:
            raise CRUDException(f"Workflow not found (set_priority): {workflow_id}")
            
        workflow.priority = priority
        session.flush()
        return workflow