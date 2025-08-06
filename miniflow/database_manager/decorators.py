import os
from functools import wraps
from typing import Any, Callable, Optional, Dict, Union
from .models import AuditAction

# Global audit setting - environment based
AUDIT_ENABLED = os.getenv('MINIFLOW_ENABLE_AUDIT', 'true').lower() == 'true'


def audit_create(table_name: str):
    """
    CREATE operasyonları için audit log decorator'u
    Usage: @audit_create("workflows")
    Environment: MINIFLOW_ENABLE_AUDIT=true/false
    """
    def decorator(func: Callable) -> Callable:
        # If audit disabled, return function unchanged
        if not AUDIT_ENABLED:
            return func
            
        @wraps(func)
        def wrapper(self, session, *args, **kwargs):
            result = func(self, session, *args, **kwargs)

            # Audit log oluştur
            if hasattr(result, 'id') and hasattr(self, '_create_audit_log'):
                new_values = _extract_model_data(result)
                self._create_audit_log(
                    session=session,
                    table_name=table_name,
                    record_id=result.id,
                    action=AuditAction.CREATE,
                    old_values=None,
                    new_values=new_values
                )

            return result
        return wrapper
    return decorator


def audit_update(table_name: str):
    """
    UPDATE operasyonları için audit log decorator'u
    Usage: @audit_update("workflows")
    Environment: MINIFLOW_ENABLE_AUDIT=true/false
    """
    def decorator(func: Callable) -> Callable:
        # If audit disabled, return function unchanged
        if not AUDIT_ENABLED:
            return func
            
        @wraps(func)
        def wrapper(self, session, record_id: Union[str, int], *args, **kwargs):
            # Update öncesi eski değerleri al
            old_record = None
            if hasattr(self, 'find_by_id'):
                try:
                    old_record = self.find_by_id(session, record_id)
                except:
                    pass  # Record bulunamadı, devam et
            
            old_values = _extract_model_data(old_record) if old_record else None
            
            # Update işlemini yap
            result = func(self, session, record_id, *args, **kwargs)

            # Audit log oluştur
            if hasattr(result, 'id') and hasattr(self, '_create_audit_log'):
                new_values = _extract_model_data(result)
                self._create_audit_log(
                    session=session,
                    table_name=table_name,
                    record_id=result.id,
                    action=AuditAction.UPDATE,
                    old_values=old_values,
                    new_values=new_values
                )

            return result
        return wrapper
    return decorator


def audit_delete(table_name: str):
    """
    DELETE operasyonları için audit log decorator'u
    Usage: @audit_delete("workflows")
    Environment: MINIFLOW_ENABLE_AUDIT=true/false
    """
    def decorator(func: Callable) -> Callable:
        # If audit disabled, return function unchanged
        if not AUDIT_ENABLED:
            return func
            
        @wraps(func)
        def wrapper(self, session, record_id: Union[str, int], *args, **kwargs):
            # Delete öncesi record'u al
            old_record = None
            if hasattr(self, 'find_by_id'):
                try:
                    old_record = self.find_by_id(session, record_id)
                except:
                    pass  # Record bulunamadı, devam et
            
            old_values = _extract_model_data(old_record) if old_record else None
            
            # Delete işlemini yap
            result = func(self, session, record_id, *args, **kwargs)

            # Audit log oluştur
            if old_record and hasattr(self, '_create_audit_log'):
                self._create_audit_log(
                    session=session,
                    table_name=table_name,
                    record_id=record_id,
                    action=AuditAction.DELETE,
                    old_values=old_values,
                    new_values=None
                )

            return result
        return wrapper
    return decorator



# ==================================================================================== HELPER FUNCTIONS ==

def _extract_model_data(model_instance) -> Optional[Dict[str, Any]]:
    """
    Model instance'dan audit için gerekli data'yı çıkar
    """
    if not model_instance:
        return None
    
    try:
        # Eğer model'de to_dict method'u varsa kullan
        if hasattr(model_instance, 'to_dict'):
            return model_instance.to_dict()
        
        # Yoksa basic attributes'leri manuel çıkar
        data = {}
        for column in model_instance.__table__.columns:
            value = getattr(model_instance, column.name, None)
            # Datetime ve complex types için string representation
            if hasattr(value, 'isoformat'):
                data[column.name] = value.isoformat()
            elif hasattr(value, 'value'):  # Enum types
                data[column.name] = value.value
            else:
                data[column.name] = value
        
        return data
    
    except Exception:
        # Fallback: sadece id ve temel bilgileri al
        return {
            'id': getattr(model_instance, 'id', None),
            'created_at': getattr(model_instance, 'created_at', None),
            'updated_at': getattr(model_instance, 'updated_at', None)
        }


# ==================================================================================== MIXIN CLASS ==

class AuditMixin:
    """
    CRUD sınıflarına audit functionality ekleyen mixin
    
    Usage:
    class WorkflowCRUD(BaseCRUD[Workflow], AuditMixin):
        def __init__(self):
            super().__init__(Workflow)
            self._init_audit()
    
    Environment: MINIFLOW_ENABLE_AUDIT=true/false
    """
    
    def _init_audit(self):
        """Audit log CRUD instance'ını initialize et (sadece audit enabled ise)"""
        if AUDIT_ENABLED:
            # Circular import'u önlemek için lazy import
            from .crud.audit_log_crud import AuditLogCRUD
            self._audit_crud = AuditLogCRUD()
        else:
            self._audit_crud = None
    
    def _create_audit_log(self, session, table_name: str, record_id: Union[str, int], 
                         action: AuditAction, old_values: Optional[Dict[str, Any]] = None,
                         new_values: Optional[Dict[str, Any]] = None,
                         user_id: Optional[str] = None, ip_address: Optional[str] = None,
                         user_agent: Optional[str] = None):
        """Audit log oluştur (sadece audit enabled ise)"""
        if AUDIT_ENABLED and hasattr(self, '_audit_crud') and self._audit_crud:
            try:
                self._audit_crud.log_action(
                    session=session,
                    table_name=table_name,
                    record_id=record_id,
                    action=action,
                    old_values=old_values,
                    new_values=new_values,
                    user_id=user_id,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
            except Exception as e:
                # Audit log hatası ana işlemi durdurmamalı
                print(f"Audit log error: {e}")
                pass