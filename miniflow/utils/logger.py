import logging
import os
import sys
from datetime import datetime

class MiniflowLogger:
    """
    Miniflow Performance Optimized Logger
    Replaces print statements with configurable logging
    """
    
    def __init__(self, level=None):
        self.level = level or os.getenv('MINIFLOW_LOG_LEVEL', 'INFO')
        self.setup_logger()
    
    def setup_logger(self):
        """Setup logger with performance optimized settings"""
        # Create logger
        self.logger = logging.getLogger('miniflow')
        
        # Avoid duplicate handlers
        if self.logger.handlers:
            return
            
        # Set level
        log_level = getattr(logging, self.level.upper(), logging.INFO)
        self.logger.setLevel(log_level)
        
        # Create handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(log_level)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        # Add handler to logger
        self.logger.addHandler(handler)
    
    def debug(self, msg, *args):
        """Debug level logging"""
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(msg, *args)
    
    def info(self, msg, *args):
        """Info level logging"""
        if self.logger.isEnabledFor(logging.INFO):
            self.logger.info(msg, *args)
    
    def warning(self, msg, *args):
        """Warning level logging"""
        if self.logger.isEnabledFor(logging.WARNING):
            self.logger.warning(msg, *args)
    
    def error(self, msg, *args):
        """Error level logging"""
        if self.logger.isEnabledFor(logging.ERROR):
            self.logger.error(msg, *args)
    
    def performance(self, operation, duration_ms, details=None):
        """Performance monitoring logs"""
        msg = f"PERF: {operation} took {duration_ms:.2f}ms"
        if details:
            msg += f" - {details}"
        self.info(msg)

# Global logger instance
logger = MiniflowLogger()

# Performance monitoring decorator
def log_performance(operation_name):
    """Decorator to log function performance"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not logger.logger.isEnabledFor(logging.INFO):
                return func(*args, **kwargs)
                
            start_time = datetime.now()
            try:
                result = func(*args, **kwargs)
                duration = (datetime.now() - start_time).total_seconds() * 1000
                logger.performance(operation_name, duration)
                return result
            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds() * 1000
                logger.performance(f"{operation_name}_FAILED", duration, str(e))
                raise
        return wrapper
    return decorator 