from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import Session

from .base_crud import BaseCRUD
from ..models import ExecutionInput, Execution, Node


class ExecutionInputCRUD(BaseCRUD[ExecutionInput]):

    def __init__(self):
        super().__init__(ExecutionInput)
    

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

    def get_execution_inputs_by_execution(self, session: Session, execution_id: str) -> List[ExecutionInput]:
        """Get all execution inputs for a specific execution"""
        stmt = select(self.model).where(self.model.execution_id == execution_id)
        return list(session.execute(stmt).scalars().all())