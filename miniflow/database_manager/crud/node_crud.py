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
        """Workflow'a ait node'ları getir"""
        stmt = select(self.model).where(self.model.workflow_id == workflow_id)
        return list(session.execute(stmt).scalars().all())

    def get_nodes_by_script(self, session: Session, script_id: str) -> List[Node]:
        """Script'e ait node'ları getir"""
        stmt = select(self.model).where(self.model.script_id == script_id)
        return list(session.execute(stmt).scalars().all())

