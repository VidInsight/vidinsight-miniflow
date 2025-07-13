from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from .base_crud import BaseCRUD
from ..models import Execution, ExecutionStatus


class ExecutionCRUD(BaseCRUD[Execution]):

    def __init__(self):
        super().__init__(Execution)

    
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