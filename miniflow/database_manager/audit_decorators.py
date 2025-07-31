"""Audit logging decorators to eliminate boilerplate code."""

from functools import wraps
from typing import Any, Callable
from .models import AuditAction

def audit_create(table_name: str):
    """
    CREATE operasyonları için audit logging decorator
    
    Eliminates 8+ duplicate audit logging calls for CREATE operations
    
    Args:
        table_name: Database table name for audit log
        
    Usage:
        @audit_create("script")
        def create_script(self, session, **data):
            return self.script_crud.create(session, **data)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, session, *args, **kwargs):
            # Execute the original function
            result = func(self, session, *args, **kwargs)
            
            # Auto-audit logging for CREATE
            if hasattr(result, 'id') and hasattr(result, 'to_dict'):
                self.audit_log_crud.log_action(
                    session=session,
                    table_name=table_name,
                    record_id=result.id,
                    action=AuditAction.CREATE,
                    new_values=result.to_dict()
                )
            
            return result
        return wrapper
    return decorator

def audit_update(table_name: str):
    """
    UPDATE operasyonları için audit logging decorator
    
    Eliminates 8+ duplicate audit logging calls for UPDATE operations
    
    Expected function signature:
    - Function should return (old_entity, new_entity) tuple
    
    Args:
        table_name: Database table name for audit log
        
    Usage:
        @audit_update("script")
        def update_script(self, session, entity_id, **data):
            old_entity = self.script_crud.find_by_id(session, entity_id)
            new_entity = self.script_crud.update(session, entity_id, **data)
            return old_entity, new_entity
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, session, *args, **kwargs):
            # Execute the original function
            result = func(self, session, *args, **kwargs)
            
            # Auto-audit logging for UPDATE
            if isinstance(result, tuple) and len(result) == 2:
                old_entity, new_entity = result
                if (hasattr(new_entity, 'id') and hasattr(new_entity, 'to_dict') and
                    hasattr(old_entity, 'to_dict')):
                    
                    self.audit_log_crud.log_action(
                        session=session,
                        table_name=table_name,
                        record_id=new_entity.id,
                        action=AuditAction.UPDATE,
                        old_values=old_entity.to_dict(),
                        new_values=new_entity.to_dict()
                    )
            
            return result
        return wrapper
    return decorator

def audit_delete(table_name: str):
    """
    DELETE operasyonları için audit logging decorator
    
    Eliminates 8+ duplicate audit logging calls for DELETE operations
    
    Expected function signature:
    - Function should return the deleted entity
    
    Args:
        table_name: Database table name for audit log
        
    Usage:
        @audit_delete("script")
        def delete_script(self, session, entity_id):
            entity = self.script_crud.find_by_id(session, entity_id)
            self.script_crud.delete(session, entity_id)
            return entity
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, session, *args, **kwargs):
            # Execute the original function
            result = func(self, session, *args, **kwargs)
            
            # Auto-audit logging for DELETE
            if hasattr(result, 'id') and hasattr(result, 'to_dict'):
                self.audit_log_crud.log_action(
                    session=session,
                    table_name=table_name,
                    record_id=result.id,
                    action=AuditAction.DELETE,
                    old_values=result.to_dict()
                )
            
            return result
        return wrapper
    return decorator

def validate_name_unique(crud_attr_name: str, entity_name_plural: str):
    """
    Name uniqueness validation decorator
    
    Eliminates 8+ duplicate name validation patterns
    
    Args:
        crud_attr_name: Name of CRUD attribute in self (e.g., "script_crud")
        entity_name_plural: Entity name for error message (e.g., "Script")
        
    Usage:
        @validate_name_unique("script_crud", "Script")
        def create_script(self, session, **data):
            return self.script_crud.create(session, **data)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, session, *args, **kwargs):
            # Extract name from kwargs or first positional arg if it's a dict
            entity_data = kwargs
            if args and isinstance(args[0], dict):
                entity_data = {**args[0], **kwargs}
            
            # Validate name uniqueness
            if 'name' in entity_data:
                crud = getattr(self, crud_attr_name)
                if hasattr(crud, 'check_name_exists') and crud.check_name_exists(session, entity_data['name']):
                    from ..exceptions import ValidationError
                    raise ValidationError(f"{entity_name_plural} with name '{entity_data['name']}' already exists")
            
            # Execute the original function
            return func(self, session, *args, **kwargs)
        return wrapper
    return decorator

# Combined decorators for ultimate efficiency
def audit_and_validate_create(table_name: str, crud_attr_name: str, entity_name_plural: str):
    """
    Combined decorator for CREATE operations with both audit and validation
    
    Replaces entire CREATE method patterns with single decorator
    
    Usage:
        @audit_and_validate_create("script", "script_crud", "Script")
        def __script_create(self, session, **script_data):
            return self.script_crud.create(session, **script_data)
    """
    def decorator(func: Callable) -> Callable:
        # Apply decorators in order
        decorated = validate_name_unique(crud_attr_name, entity_name_plural)(func)
        decorated = audit_create(table_name)(decorated)
        return decorated
    return decorator