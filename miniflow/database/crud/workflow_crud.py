from sqlalchemy.orm import Session

from .base_crud import BaseCRUD
from ..models import Workflow, WorkflowStatus
from ...exceptions import ValidationError
from ..decorators.auditlog_decorators import audit_create, audit_update, audit_delete, AuditMixin


class WorkflowCRUD(BaseCRUD[Workflow], AuditMixin):

    def __init__(self):
        # BaseCRUD initiliaze et - bağla
        super().__init__(Workflow)

# ================================================================================================== BUSINESS METHODS ==
    @audit_create("workflows")
    def create_workflow(self, session: Session, **workflow_data) -> Workflow:
        """Create new workflow with name uniqueness validation and audit logging."""
        if self.check_name_exists(session, workflow_data['name']):
            raise ValidationError(f"Workflow with name '{workflow_data.get('name')}' already exists")

        return super().create(session, **workflow_data)

    @audit_update("workflows")
    def update_workflow(self, session: Session, workflow_id: str, **workflow_data) -> Workflow:
        """Update workflow with name uniqueness validation and audit logging."""
        if workflow_data.get('name'):
            old_workflow = self.find_by_id(session, workflow_id)
            if workflow_data['name'] != old_workflow.name:
                if self.check_name_exists(session, workflow_data['name']):
                    raise ValidationError(f"Workflow with name '{workflow_data['name']}' already exists")

        return super().update(session, workflow_id, **workflow_data)

    @audit_delete("workflows")
    def delete_workflow(self, session: Session, workflow_id: str) -> Workflow:
        """Delete workflow with audit logging."""
        return super().delete(session, workflow_id)

    # ================================================================================================== CORE METHODS ==

    def set_priority(self, session: Session, workflow_id: str, priority: int) -> Workflow:
        if not 0 <= priority <= 100:
            raise ValueError("Priority must be between 0 and 100")
        
        workflow = self.find_by_id(session, workflow_id)
        workflow.priority = priority
        session.flush()
        return workflow
    
    def __change_status(self, session: Session, workflow_id: str, new_status: WorkflowStatus) -> Workflow:
        workflow = self.find_by_id(session, workflow_id)
        workflow.status = new_status
        if new_status == WorkflowStatus.ACTIVE:
            workflow.is_active = True
        else:
            workflow.is_active = False
        session.flush()
        return workflow

    def set_status_active(self, session: Session, workflow_id: str) -> Workflow:
        return self.__change_status(session, workflow_id, WorkflowStatus.ACTIVE)

    def set_status_inactive(self, session: Session, workflow_id: str) -> Workflow:
        return self.__change_status(session, workflow_id, WorkflowStatus.INACTIVE)

    def set_status_draft(self, session: Session, workflow_id: str) -> Workflow:
        return self.__change_status(session, workflow_id, WorkflowStatus.DRAFT)