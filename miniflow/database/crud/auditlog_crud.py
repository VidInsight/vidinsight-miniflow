from typing import List, Optional, Dict, Any, Union
from sqlalchemy import select, and_, or_, func, desc, delete
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from .base_crud import BaseCRUD
from ..models import AuditLog, AuditAction
from ...exceptions import ValidationError, CRUDException


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
        """Create audit log entry for system change tracking and compliance."""
        # Input validation
        if not table_name or not table_name.strip():
            raise ValidationError("table_name cannot be empty")
        if not isinstance(action, AuditAction):
            raise ValidationError(f"Invalid action type: {type(action).__name__}")
        
        log_data = {
            'table_name': table_name,
            'record_id': record_id,
            'action': action,
            'old_values': old_values,
            'new_values': new_values
        }

        # Extra kwargs (user_id, ip_address, user_agent) ignore edilir çünkü model'de yok
        # Gelecekte model güncellenirse burası da güncellenir

        # Direct database operation to avoid recursive logging
        try:
            audit_log = AuditLog(**log_data)
            session.add(audit_log)
            session.flush()
            return audit_log
        except Exception as e:
            session.rollback()
            raise CRUDException(f"Failed to create audit log: {str(e)}")

    def cleanup_old_logs(self, session: Session, days_old: int = 90) -> int:
        """
        Eski audit log'ları temizle
        
        Args:
            session (Session): Database session
            days_old (int): Kaç günden eski log'lar silinecek (default: 90)
            
        Returns:
            int: Silinen log sayısı
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            # Eski log'ları bul ve sil
            stmt = delete(AuditLog).where(AuditLog.created_at < cutoff_date)
            result = session.execute(stmt)
            deleted_count = result.rowcount
            
            session.commit()
            return deleted_count
            
        except Exception as e:
            session.rollback()
            raise CRUDException(f"Failed to cleanup old audit logs: {str(e)}")

    def get_log_statistics(self, session: Session) -> Dict[str, Any]:
        """
        Audit log istatistiklerini getir
        
        Returns:
            Dict[str, Any]: Log istatistikleri
        """
        try:
            # Toplam log sayısı
            total_count = self.count_all(session)
            
            # Son 30 günlük log sayısı
            thirty_days_ago = datetime.now() - timedelta(days=30)
            recent_count = self.count_filtered(session, {
                'created_at__gte': thirty_days_ago
            })
            
            # Action bazında sayılar
            action_counts = {}
            for action in AuditAction:
                count = self.count_filtered(session, {'action': action})
                action_counts[action.value] = count
            
            return {
                'total_logs': total_count,
                'recent_logs_30_days': recent_count,
                'action_breakdown': action_counts
            }
            
        except Exception as e:
            raise CRUDException(f"Failed to get audit log statistics: {str(e)}")