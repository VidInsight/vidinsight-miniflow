from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import Session

from .base_crud import BaseCRUD
from ..models import Workflow, WorkflowStatus


class WorkflowCRUD(BaseCRUD[Workflow]):

    def __init__(self):
        # BaseCRUD initiliaze et - bağla
        super().__init__(Workflow)

    """
    BaseCRUD'dan miras alınan fonksiyonlar:
    ============================================================
    - create()
    - find_by_id()
    - find_by_name() 
    - update()
    - delete()
    - get_all()
    - count(), 
    - exists()
    - filter() 
    - order_by()
    - select_in_bulk()
    - truncate(),
    - bulk_create()
    - bulk_update()
    - bulk_delete()
    """

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

    def set_status_archived(self, session: Session, workflow_id: str) -> Workflow:
        return self.__change_status(session, workflow_id, WorkflowStatus.ARCHIVED)

    def set_status_draft(self, session: Session, workflow_id: str) -> Workflow:
        return self.__change_status(session, workflow_id, WorkflowStatus.DRAFT)
    
    def check_name_exists(self, session: Session, name: str) -> bool:
        stmt = select(func.count(self.model.id)).where(self.model.name == name)
        count = session.execute(stmt).scalar_one()
        return count > 0