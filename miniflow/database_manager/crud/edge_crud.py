from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import Session

from .base_crud import BaseCRUD
from ..models import Edge, Node


class EdgeCRUD(BaseCRUD[Edge]):
    
    def __init__(self):
        super().__init__(Edge)

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