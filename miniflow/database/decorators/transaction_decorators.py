"""
Transaction management decorators for database operations.
"""

from functools import wraps
from typing import Callable, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from ...exceptions import DatabaseError, CRUDException


def transactional(auto_commit: bool = True, auto_rollback: bool = True):
    """
    Decorator to handle database transactions automatically.
    
    Args:
        auto_commit: Whether to automatically commit on success
        auto_rollback: Whether to automatically rollback on error
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Find session in arguments
            session = None
            for arg in args:
                if isinstance(arg, Session):
                    session = arg
                    break
            
            if 'session' in kwargs:
                session = kwargs['session']
            
            if not session:
                raise ValueError("No database session found in arguments")
            
            try:
                # Execute the function
                result = func(*args, **kwargs)
                
                # Auto commit if enabled
                if auto_commit:
                    session.commit()
                
                return result
                
            except (CRUDException, DatabaseError):
                # Re-raise our custom exceptions
                if auto_rollback:
                    session.rollback()
                raise
                
            except SQLAlchemyError as e:
                # Handle SQLAlchemy errors
                if auto_rollback:
                    session.rollback()
                raise DatabaseError(f"Database operation failed: {str(e)}")
                
            except Exception as e:
                # Handle unexpected errors
                if auto_rollback:
                    session.rollback()
                raise DatabaseError(f"Unexpected error in database operation: {str(e)}")
        
        return wrapper
    return decorator


def read_only_transaction(func: Callable) -> Callable:
    """
    Decorator for read-only operations that should not modify data.
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            result = func(*args, **kwargs)
            return result
        except SQLAlchemyError as e:
            raise DatabaseError(f"Database read operation failed: {str(e)}")
        except Exception as e:
            raise DatabaseError(f"Unexpected error in read operation: {str(e)}")
    
    return wrapper


def bulk_operation(chunk_size: int = 1000):
    """
    Decorator for bulk operations with chunking support.
    
    Args:
        chunk_size: Number of records to process in each chunk
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Add chunk_size to kwargs if not present
            if 'chunk_size' not in kwargs:
                kwargs['chunk_size'] = chunk_size
            
            try:
                result = func(*args, **kwargs)
                return result
            except SQLAlchemyError as e:
                raise DatabaseError(f"Bulk operation failed: {str(e)}")
            except Exception as e:
                raise DatabaseError(f"Unexpected error in bulk operation: {str(e)}")
        
        return wrapper
    return decorator
