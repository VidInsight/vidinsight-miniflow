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

    # ==================================================================================== HIGH PRIORITY METHODS ==
    
    def get_record_change_history(self, session: Session, table_name: str, record_id: str) -> List[AuditLog]:
        """
        Belirli record'un tüm değişiklik geçmişini getir (kronolojik sıra ile)
        
        Args:
            session: Database session
            table_name: Tablo adı (örn: "workflows")
            record_id: Record ID (örn: "WF-123...")
            
        Returns:
            List[AuditLog]: Kronolojik sıralı audit log'ları (en yeni -> en eski)
            
        Example:
            >>> audit_crud = AuditLogCRUD()
            >>> history = audit_crud.get_record_change_history(session, "workflows", "WF-123")
            >>> for log in history:
            ...     print(f"{log.action}: {log.created_at}")
        """
        stmt = (
            select(self.model)
            .where(
                and_(
                    self.model.table_name == table_name,
                    self.model.record_id == record_id
                )
            )
            .order_by(desc(self.model.created_at))
        )
        
        result = session.execute(stmt)
        return result.scalars().all()
    
    def cleanup_old_logs(self, session: Session, older_than_days: int = 90) -> int:
        """
        Belirtilen günden eski audit log'ları sil (database maintenance)
        
        Args:
            session: Database session
            older_than_days: Kaç günden eski kayıtlar silinecek (default: 90)
            
        Returns:
            int: Silinen kayıt sayısı
            
        Warning:
            Bu işlem geri alınamaz! Production'da dikkatli kullanın.
            
        Example:
            >>> audit_crud = AuditLogCRUD()
            >>> deleted_count = audit_crud.cleanup_old_logs(session, 180)  # 6 aylık
            >>> print(f"Deleted {deleted_count} old audit logs")
        """
        cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
        
        # Count first for return value
        count_stmt = (
            select(func.count(self.model.id))
            .where(self.model.created_at < cutoff_date)
        )
        count_result = session.execute(count_stmt)
        delete_count = count_result.scalar_one()
        
        # Delete old records
        delete_stmt = delete(self.model).where(self.model.created_at < cutoff_date)
        session.execute(delete_stmt)
        session.flush()
        
        return delete_count
    
    def get_activity_summary(self, session: Session, start_date: datetime = None, 
                           end_date: datetime = None) -> Dict[str, Any]:
        """
        Belirli tarih aralığında aktivite özeti (analytics)
        
        Args:
            session: Database session
            start_date: Başlangıç tarihi (default: 30 gün önce)
            end_date: Bitiş tarihi (default: şimdi)
            
        Returns:
            Dict: Aktivite özet raporu
            
        Example:
            >>> audit_crud = AuditLogCRUD()
            >>> summary = audit_crud.get_activity_summary(session)
            >>> print(f"Total operations: {summary['total_operations']}")
        """
        # Default date range: last 30 days
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Base filter
        date_filter = and_(
            self.model.created_at >= start_date,
            self.model.created_at <= end_date
        )
        
        # Total operations
        total_stmt = select(func.count(self.model.id)).where(date_filter)
        total_operations = session.execute(total_stmt).scalar_one()
        
        # Operations by action
        action_stmt = (
            select(self.model.action, func.count(self.model.id))
            .where(date_filter)
            .group_by(self.model.action)
        )
        action_result = session.execute(action_stmt)
        operations_by_action = {action.value: count for action, count in action_result}
        
        # Operations by table
        table_stmt = (
            select(self.model.table_name, func.count(self.model.id))
            .where(date_filter)
            .group_by(self.model.table_name)
            .order_by(desc(func.count(self.model.id)))
        )
        table_result = session.execute(table_stmt)
        operations_by_table = {table: count for table, count in table_result}
        
        # Daily activity (last 7 days for trend)
        recent_start = end_date - timedelta(days=7)
        daily_stmt = (
            select(
                func.date(self.model.created_at).label('date'),
                func.count(self.model.id).label('count')
            )
            .where(
                and_(
                    self.model.created_at >= recent_start,
                    self.model.created_at <= end_date
                )
            )
            .group_by(func.date(self.model.created_at))
            .order_by(func.date(self.model.created_at))
        )
        daily_result = session.execute(daily_stmt)
        daily_activity = {str(date): count for date, count in daily_result}
        
        return {
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days': (end_date - start_date).days
            },
            'total_operations': total_operations,
            'operations_by_action': operations_by_action,
            'operations_by_table': operations_by_table,
            'daily_activity_last_7_days': daily_activity,
            'average_daily_operations': round(total_operations / max((end_date - start_date).days, 1), 2)
        }