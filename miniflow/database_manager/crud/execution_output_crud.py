from typing import List, Optional, Dict, Any, Union
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import Session
from datetime import datetime

from .base_crud import BaseCRUD
from ..models import ExecutionOutput, ExecutionOutputStatus, Execution, Node


class ExecutionOutputCRUD(BaseCRUD[ExecutionOutput]):
    
    def __init__(self):
        super().__init__(ExecutionOutput)

    
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

    def get_execution_outputs_by_execution(self, session: Session, execution_id: str) -> List[ExecutionOutput]:
        """Get all execution outputs for a specific execution"""
        stmt = select(self.model).where(self.model.execution_id == execution_id)
        return list(session.execute(stmt).scalars().all())