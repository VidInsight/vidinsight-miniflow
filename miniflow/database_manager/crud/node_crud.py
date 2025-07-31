from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import Session

from .base_crud import BaseCRUD
from ..models import Node


class NodeCRUD(BaseCRUD[Node]):
    
    def __init__(self):
        super().__init__(Node)
    
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

    def get_nodes_by_workflow(self, session: Session, workflow_id: str) -> List[Node]:
        """Workflow'a ait node'ları getir - OPTIMIZED with BaseCRUD"""
        return self.get_by_workflow(session, workflow_id)  # OPTIMIZED: use generic method

    def get_nodes_by_script(self, session: Session, script_id: str) -> List[Node]:
        """Script'e ait node'ları getir - OPTIMIZED with BaseCRUD"""
        return self.get_by_field(session, "script_id", script_id)  # OPTIMIZED: use generic method

    def get_by_name(self, session: Session, name: str, workflow_id: str):
        stmt = select(self.model).where(
            and_(self.model.name == name, self.model.workflow_id == workflow_id)
        )
        return session.execute(stmt).scalars().first()

