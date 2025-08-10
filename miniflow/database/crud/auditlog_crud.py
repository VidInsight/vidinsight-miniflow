from typing import List, Optional, Dict, Any, Union
from sqlalchemy import select, and_, or_, func, desc, delete
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from .base_crud import BaseCRUD
from ..models import AuditLog, AuditAction


class AuditLogCRUD(BaseCRUD[AuditLog]):
    """
    AuditLog entity CRUD operations.
    Handles system change tracking and compliance logging.
    Note: AuditLog does not use AuditMixin to prevent recursive logging.
    """

    def __init__(self):
        super().__init__(AuditLog)

    def log_action(self, session: Session, table_name: str, record_id: Union[str, int], action: AuditAction,
                   old_values: Dict[str, Any] = None, new_values: Dict[str, Any] = None,
                   **extra_kwargs) -> AuditLog:
        """Genel audit log kaydı oluştur - TEK GÖREV"""
        log_data = {
            'table_name': table_name,
            'record_id': record_id,
            'action': action,
            'old_values': old_values,
            'new_values': new_values
        }

        # Extra kwargs (user_id, ip_address, user_agent) ignore edilir çünkü model'de yok
        # Gelecekte model güncellenirse burası da güncellenir

        audit_log = self.create(session, **log_data)
        return audit_log