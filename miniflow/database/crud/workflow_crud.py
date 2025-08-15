from sqlalchemy.orm import Session

from .base_crud import BaseCRUD
from ..models import Workflow, WorkflowStatus
from ..decorators.auditlog_decorators import audit_create, audit_update, audit_delete, AuditMixin


class WorkflowCRUD(BaseCRUD[Workflow], AuditMixin):

    def __init__(self):
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
        workflow = self.find_by_id(session, workflow_id)
        workflow.status = new_status
        session.flush()
        return workflow

    def set_priority(self, session: Session, workflow_id: str, priority: int):
        if not 0 <= priority <= 10:
            raise ValueError("Priority must be between 0 and 10")

        workflow = self.find_by_id(session, workflow_id)
        workflow.priority = priority
        session.flush()
        return workflow