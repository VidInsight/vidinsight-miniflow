from typing import List, Optional, Dict, Any, Union
from sqlalchemy import select, and_, or_, func, desc, delete
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from .base_crud import BaseCRUD
from ..models import AuditLog, AuditAction


class AuditLogCRUD(BaseCRUD[AuditLog]):

    def __init__(self):
        super().__init__(AuditLog)
    
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

    def log_action(self, session: Session, table_name: str, record_id: Union[str, int], action: AuditAction,
                   old_values: Dict[str, Any] = None, new_values: Dict[str, Any] = None,
                   user_id: str = None, ip_address: str = None, user_agent: str = None) -> AuditLog:
        """Genel audit log kaydı oluştur - TEK GÖREV"""
        log_data = {
            'table_name': table_name,
            'record_id': record_id,
            'action': action,
            'old_values': old_values,
            'new_values': new_values,
            'user_id': user_id,
            'ip_address': ip_address,
            'user_agent': user_agent
        }
        
        audit_log = self.create(session, **log_data)
        return audit_log