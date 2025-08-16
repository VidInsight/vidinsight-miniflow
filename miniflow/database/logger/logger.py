"""
MINIFLOW DATABASE LOGGER
========================

Database operasyonları için context-aware logger wrapper.
Her component için specialized logging methods sağlar.
"""

import logging
import time
import json
from typing import Any, Dict, Optional, Union
from contextlib import contextmanager
from datetime import datetime, timezone


class DatabaseLogger:
    """
    Database operasyonları için context-aware logger wrapper.
    Her component için specialized logging methods sağlar.
    """

    def __init__(self, component: str):
        self.component = component
        self.logger = logging.getLogger(f"miniflow.database.{component}")
    
    def debug(self, message: str, operation: str = None, **context):
        """Debug level logging with context"""
        self._log(logging.DEBUG, message, operation, **context)
    
    def info(self, message: str, operation: str = None, **context):
        """Info level logging with context"""
        self._log(logging.INFO, message, operation, **context)
    
    def warning(self, message: str, operation: str = None, **context):
        """Warning level logging with context"""
        self._log(logging.WARNING, message, operation, **context)
    
    def error(self, message: str, operation: str = None, exception: Exception = None, **context):
        """Error level logging with context and exception details"""
        if exception:
            context.update({
                'exception_type': type(exception).__name__,
                'exception_message': str(exception),
                'exception_args': exception.args
            })
        self._log(logging.ERROR, message, operation, **context)
    
    def _log(self, level: int, message: str, operation: str = None, **context):
        """Base logging method with context"""
        extra = {
            'component': self.component,
            'operation': operation,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }
        
        # Context bilgilerini extra'ya ekle
        for key, value in context.items():
            # Complex data types için JSON formatına çevir
            if isinstance(value, (dict, list)):
                try:
                    extra[key] = json.dumps(value) if len(str(value)) > 100 else value
                except (TypeError, ValueError):
                    extra[key] = str(value)
            else:
                extra[key] = value
        # Log işlemi
        self.logger.log(level, message, extra=extra)

    @contextmanager
    def operation_context(self, operation: str, **context):
        """Operation context manager"""
        start_time = time.time()
        operation_id = f"{operation}_{int(start_time * 1000)}"

        # Start Logging
        self.debug(f"Starting operation: {operation}", 
                  operation=operation, 
                  operation_id=operation_id,
                  **context)

        try:
            yield operation_id
            
            # Success logging
            duration = time.time() - start_time
            self.debug(f"Completed operation: {operation}", 
                      operation=operation,
                      operation_id=operation_id,
                      duration_ms=round(duration * 1000, 2),
                      status="success",
                      **context)
            
        except Exception as e:
            # Error logging
            duration = time.time() - start_time
            self.error(f"Failed operation: {operation}", 
                      operation=operation,
                      operation_id=operation_id,
                      duration_ms=round(duration * 1000, 2),
                      status="failed",
                      exception=e,
                      **context)
            raise

    def performance_log(self, operation: str, duration_ms: float, **metrics):
        """Performance monitoring için specialized logging"""
        perf_logger = logging.getLogger("miniflow.database.performance")

        extra = {
            'component': self.component,
            'operation': operation,
            'duration_ms': duration_ms,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        extra.update(metrics)

        perf_logger.info(f"Performance: {operation} completed in {duration_ms}ms", extra=extra)

    def audit_log(self, action: str, resource_type: str, resource_id: str, **details):
        """Audit logging için specialized method"""
        audit_logger = logging.getLogger('miniflow.database.audit')
        
        extra = {
            'component': self.component,
            'operation': 'audit',
            'audit_action': action,
            'resource_type': resource_type,
            'resource_id': resource_id,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        extra.update(details)
        
        audit_logger.info(f"Audit: {action} on {resource_type}:{resource_id}", extra=extra)


class PerformanceLogger:
    """Performance monitoring için specialized logger"""
    
    def __init__(self, component: str):
        self.component = component
        self.logger = logging.getLogger('miniflow.database.performance')
    
    @contextmanager
    def measure(self, operation: str, **context):
        """Performance measurement context manager"""
        start_time = time.time()
        start_memory = self._get_memory_usage()  # Opsiyonel: memory tracking
        
        try:
            yield
        finally:
            duration = time.time() - start_time
            end_memory = self._get_memory_usage()
            
            self.logger.info(f"Performance: {operation}", extra={
                'component': self.component,
                'operation': operation,
                'duration_ms': round(duration * 1000, 2),
                'memory_delta_mb': round((end_memory - start_memory) / 1024 / 1024, 2),
                **context
            })
    
    def _get_memory_usage(self) -> int:
        """Memory usage in bytes (opsiyonel)"""
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            return process.memory_info().rss
        except ImportError:
            return 0


def get_database_logger(component: str) -> DatabaseLogger:
    """Database logger factory function"""
    return DatabaseLogger(component)


def get_performance_logger(component: str) -> PerformanceLogger:
    """Performance logger factory function"""
    return PerformanceLogger(component)