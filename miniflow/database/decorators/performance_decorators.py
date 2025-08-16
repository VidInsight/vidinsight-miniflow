
"""
MINIFLOW DATABASE PERFORMANCE DECORATORS
=========================================

Database operasyonları için performance monitoring decorator'ları.
Otomatik timing, memory tracking ve performance logging sağlar.
"""

import time
import functools
from typing import Callable, Any, Optional


def monitor_performance(operation_name: str = None, 
                       track_memory: bool = False,
                       log_args: bool = False):
    """
    Database operasyonları için performance monitoring decorator
    
    Args:
        operation_name: Custom operation adı (default: class.method)
        track_memory: Memory usage tracking (requires psutil)
        log_args: Method arguments'ları log'la
    
    Usage:
        @monitor_performance("create_workflow", track_memory=True)
        def create_workflow(self, session, **data):
            pass
    """
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # Logger'ı ve gerekli method'ları kontrol et
            if not _has_valid_logger(self, 'performance_log'):
                # Fallback: method'u normal çalıştır
                return func(self, *args, **kwargs)
            
            # Operation name belirleme
            op_name = operation_name or f"{self.__class__.__name__}.{func.__name__}"
            
            # Context bilgileri
            context = {
                'method': func.__name__,
                'class': self.__class__.__name__
            }
            
            if log_args:
                context.update({
                    'args_count': len(args),
                    'kwargs_keys': list(kwargs.keys())
                })
            
            # Performance measurement
            start_time = time.time()
            start_memory = _get_memory_usage() if track_memory else 0
            
            try:
                # Method execution
                result = func(self, *args, **kwargs)
                
                # Success metrics
                duration = time.time() - start_time
                end_memory = _get_memory_usage() if track_memory else 0
                
                # Performance logging
                metrics = {
                    'status': 'success',
                    'duration_ms': round(duration * 1000, 2)
                }
                
                if track_memory:
                    metrics['memory_delta_mb'] = round((end_memory - start_memory) / 1024 / 1024, 2)
                
                metrics.update(context)
                
                # Safe logging call
                try:
                    self._logger.performance_log(op_name, duration * 1000, **metrics)
                except Exception:
                    # Logger hatası varsa sessizce devam et
                    pass
                
                return result
                
            except Exception as e:
                # Error metrics
                duration = time.time() - start_time
                
                metrics = {
                    'status': 'error',
                    'duration_ms': round(duration * 1000, 2),
                    'exception_type': type(e).__name__
                }
                metrics.update(context)
                
                # Safe error logging
                try:
                    self._logger.performance_log(op_name, duration * 1000, **metrics)
                except Exception:
                    # Logger hatası varsa sessizce devam et
                    pass
                
                raise
        
        return wrapper
    return decorator


def monitor_database_operation(operation_type: str = "database_op"):
    """
    Database-specific operations için specialized monitoring
    
    Args:
        operation_type: Operation kategorisi (crud, query, transaction)
    """
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, session, *args, **kwargs):
            # Logger ve operation_context method'unu kontrol et
            if not _has_valid_logger(self, 'operation_context'):
                return func(self, session, *args, **kwargs)
            
            operation_name = f"{operation_type}.{func.__name__}"
            
            try:
                with self._logger.operation_context(operation_name,
                                                  operation_type=operation_type,
                                                  has_session=session is not None):
                    return func(self, session, *args, **kwargs)
            except (AttributeError, TypeError):
                # Context manager çalışmazsa normal çalıştır
                return func(self, session, *args, **kwargs)
        
        return wrapper
    return decorator


def _has_valid_logger(obj: Any, method_name: str) -> bool:
    """
    Objenin geçerli bir logger'a ve belirtilen method'a sahip olup olmadığını kontrol eder
    
    Args:
        obj: Kontrol edilecek obje
        method_name: Logger'da olması gereken method adı
    
    Returns:
        bool: Logger ve method geçerliyse True
    """
    return (hasattr(obj, '_logger') and 
            obj._logger is not None and
            hasattr(obj._logger, method_name) and
            callable(getattr(obj._logger, method_name)))


def _get_memory_usage() -> int:
    """
    Memory usage in bytes
    
    Returns:
        int: Memory usage in bytes, 0 if psutil is not available
    """
    try:
        import psutil
        import os
        process = psutil.Process(os.getpid())
        return process.memory_info().rss
    except (ImportError, Exception):
        return 0