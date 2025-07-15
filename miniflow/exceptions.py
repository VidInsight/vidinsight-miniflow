from typing import Optional, Dict, Any, Callable
from contextlib import contextmanager
from datetime import datetime
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class MiniflowException(Exception):
    """Ana exception sınıfı"""
    def __init__(self, message: str, error_code: str = None, details: str = None):
        self.message = message
        self.error_code = error_code or "GENERAL_ERROR"
        self.details = details


class DatabaseError(MiniflowException):
    """Veritabanı hataları için"""
    def __init__(self, message: str, details: str = None, error_code: str = None):
        super().__init__(message, error_code or "DATABASE_ERROR", details),

class EngineError(MiniflowException):
    """Execution Engine hataları için"""
    def __init__(self, message: str, details: str = None, error_code: str = None):
        super().__init__(message, error_code or "ENGINE_ERROR", details)

class SchedulerError(MiniflowException):
    """Scheduler hataları için"""
    def __init__(self, message: str, details: str = None, error_code: str = None):
        super().__init__(message, error_code or "SCHEDULER_ERROR", details)

class ValidationError(MiniflowException):
    """Veri doğrulama hataları için"""
    def __init__(self, message: str, details: str = None, error_code: str = None):
        super().__init__(message, error_code or "VALIDATION_ERROR", details)

class BusinessLogicError(MiniflowException):
    """İş mantığı hataları için"""
    def __init__(self, message: str, details: str = None, error_code: str = None):
        super().__init__(message, error_code or "BUSINESS_ERROR", details)

class ResourceError(MiniflowException):
    """Dosya/kaynak erişim hataları için"""
    def __init__(self, message: str, details: str = None, error_code: str = None):
        super().__init__(message, error_code or "RESOURCE_ERROR", details)


def create_error_response(exception: MiniflowException) -> Dict[str, Any]:
    # 1. Hatayı logla
    logger.error(f"Error: {exception.error_code} - {exception.message}")
    if exception.details:
        logger.error(f"Details: {exception.details}")

    # 2. Hata çıktısını döndür
    return {
        "status": "error",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "error_code": exception.error_code,
        "message": exception.message,
        "details": exception.details
    }

def handle_unexpected_error(error: Exception, context: str = "") -> Dict[str, Any]:
    # 1. Hatayı logla
    error_msg = f"Beklenmeyen hata oluştu{': ' + context if context else ''}"
    logger.error(f"Unexpected error in {context}: {str(error)}", exc_info=True)
    
    # Basit error response
    return {
        "status": "error",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "error_code": "INTERNAL_ERROR",
        "message": error_msg,
        "details": "Sistem yöneticisiyle iletişime geçin"
    } 


class ErrorManager:
    """Merkezi hata yönetim modülü"""

    @staticmethod
    def operation_context(operation_name: str):
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    logger.debug(f"Starting operation: {operation_name}")
                    result = func(*args, **kwargs)
                    logger.debug(f"Completed operation: {operation_name}")
                    return result
                
                except MiniflowException:
                    # Re-raise custom exceptions as-is
                    logger.warning(f"Business error in {operation_name}")
                    raise

                except OSError as e:
                    # File system errors
                    error_msg = f"File system error in {operation_name}"
                    logger.error(f"{error_msg}: {str(e)}")
                    raise ResourceError(error_msg, str(e))
                
                except Exception as e:
                    # Unexpected errors
                    error_msg = f"Unexpected error in {operation_name}"
                    logger.error(f"{error_msg}: {str(e)}", exc_info=True)
                    raise DatabaseError(error_msg, str(e))
                
            return wrapper
        return decorator
    

    @staticmethod
    def validate_engine_state(engine) -> None:
        """Validate that database engine is properly initialized"""
        if not engine:
            raise BusinessLogicError(
                "Database engine not initialized",
                "Call start() method before performing operations"
            )
    
    @staticmethod
    def validate_required_fields(data: dict, required_fields: list, operation: str) -> None:
        """Validate required fields in input data"""
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            raise ValidationError(
                f"Missing required fields for {operation}: {', '.join(missing_fields)}",
                f"Required fields: {required_fields}"
            )