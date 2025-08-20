import os
from functools import wraps
from typing import Any, Callable, Optional, Dict, Union

from ..models import AuditAction


AUDIT_ENABLED = os.getenv("AUDIT_ENABLED", 'true').lower() == "true"


def audit_create(table_name: str):
    """
    CREATE operasyonları için audit log decorator'u - Optimized version
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

            # Optimized: Audit log oluştur (with error handling)
            if hasattr(result, 'id') and hasattr(self, '_create_audit_log'):
                try:
                    # Optimized: Only extract data if audit is enabled
                    new_values = _extract_model_data(result)
                    self._create_audit_log(
                        session=session,
                        table_name=table_name,
                        record_id=result.id,
                        action=AuditAction.CREATE,
                        old_values=None,
                        new_values=new_values
                    )
                except Exception as e:
                    # Optimized: Use lazy logging to avoid import overhead
                    try:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f"Failed to create audit log for create operation: {str(e)}")
                    except:
                        pass  # Fallback: silent failure

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
            old_values = None
            
            if hasattr(self, 'find_by_id'):
                try:
                    old_record = self.find_by_id(session, record_id)
                    if old_record:
                        old_values = _extract_model_data(old_record)
                except Exception as e:
                    # Log the error but don't fail the update operation
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Failed to get old record for audit log: {str(e)}")

            # Update işlemini yap
            result = func(self, session, record_id, *args, **kwargs)

            # Audit log oluştur (with error handling)
            if hasattr(result, 'id') and hasattr(self, '_create_audit_log'):
                try:
                    new_values = _extract_model_data(result)
                    self._create_audit_log(
                        session=session,
                        table_name=table_name,
                        record_id=result.id,
                        action=AuditAction.UPDATE,
                        old_values=old_values,
                        new_values=new_values
                    )
                except Exception as e:
                    # Log the error but don't fail the update operation
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Failed to create audit log for update operation: {str(e)}")

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
            old_values = None
            
            if hasattr(self, 'find_by_id'):
                try:
                    old_record = self.find_by_id(session, record_id)
                    if old_record:
                        old_values = _extract_model_data(old_record)
                except Exception as e:
                    # Log the error but don't fail the delete operation
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Failed to get old record for audit log: {str(e)}")

            # Delete işlemini yap
            result = func(self, session, record_id, *args, **kwargs)

            # Audit log oluştur (with error handling)
            if old_record and hasattr(self, '_create_audit_log'):
                try:
                    self._create_audit_log(
                        session=session,
                        table_name=table_name,
                        record_id=record_id,
                        action=AuditAction.DELETE,
                        old_values=old_values,
                        new_values=None
                    )
                except Exception as e:
                    # Log the error but don't fail the delete operation
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Failed to create audit log for delete operation: {str(e)}")

            return result

        return wrapper

    return decorator


# ==================================================================================== HELPER FUNCTIONS ==

def _extract_model_data(model_instance) -> Optional[Dict[str, Any]]:
    """
    Model instance'dan audit için gerekli data'yı çıkar - Optimized version
    """
    if not model_instance:
        return None

    try:
        # Optimized: Eğer model'de to_dict method'u varsa kullan
        if hasattr(model_instance, 'to_dict'):
            return model_instance.to_dict()

        # Optimized: Basic attributes'leri manuel çıkar
        data = {}
        # Optimized: Use __table__.columns directly for better performance
        columns = model_instance.__table__.columns
        
        for column in columns:
            column_name = column.name
            value = getattr(model_instance, column_name, None)
            
            # Optimized: Efficient type checking
            if value is not None:
                if hasattr(value, 'isoformat'):  # Datetime types
                    data[column_name] = value.isoformat()
                elif hasattr(value, 'value'):  # Enum types
                    data[column_name] = value.value
                else:
                    data[column_name] = value

        return data

    except Exception:
        # Optimized: Fallback with minimal attribute access
        fallback_data = {}
        for attr in ['id', 'created_at', 'updated_at']:
            try:
                value = getattr(model_instance, attr, None)
                if value is not None:
                    fallback_data[attr] = value
            except:
                continue
        return fallback_data


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
            from ..crud.auditlog_crud import AuditLogCRUD
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
                import logging
                logger = logging.getLogger("miniflow.database.audit")
                logger.error("Audit log error", extra={
                    "component": "AuditMixin",
                    "error": str(e),
                    "table_name": table_name,
                    "record_id": record_id,
                    "action": action.value if hasattr(action, 'value') else str(action)
                })
                pass