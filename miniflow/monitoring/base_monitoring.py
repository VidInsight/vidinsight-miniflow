"""
BASE MONITORING UTILITIES
========================

Common utilities and base classes for all monitoring components.
Provides shared functionality to reduce code duplication.
"""

import time
import threading
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import deque
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class MonitoringUtils:
    """Utility functions shared across monitoring components"""
    
    @staticmethod
    def format_timestamp(dt: datetime = None) -> str:
        """Format timestamp consistently across all monitoring components"""
        if dt is None:
            dt = datetime.utcnow()
        return dt.isoformat() + 'Z'
    
    @staticmethod
    def calculate_history_points(duration_minutes: int, interval_seconds: float) -> int:
        """Calculate maximum history points based on duration and interval"""
        return int((duration_minutes * 60) / interval_seconds)
    
    @staticmethod
    def truncate_string(text: str, max_length: int = 200, suffix: str = "...") -> str:
        """Truncate string consistently with suffix"""
        if len(text) > max_length:
            return text[:max_length] + suffix
        return text
    
    @staticmethod
    def safe_dict_get(data: dict, *keys, default=None):
        """Safely get nested dictionary values"""
        for key in keys:
            if isinstance(data, dict) and key in data:
                data = data[key]
            else:
                return default
        return data


class BaseMonitoringComponent(ABC):
    """Base class for all monitoring components with common functionality"""
    
    def __init__(self, 
                 history_duration_minutes: int = 60,
                 component_name: str = None):
        """
        Initialize base monitoring component
        
        Args:
            history_duration_minutes: How long to keep historical data
            component_name: Name of the component (for logging)
        """
        self.history_duration = timedelta(minutes=history_duration_minutes)
        self.component_name = component_name or self.__class__.__name__
        
        # Historical data storage
        self.history: deque = deque()
        self.history_lock = threading.RLock()
        
        # Component state
        self.is_initialized = False
        self.is_running = False
        self.initialization_time = datetime.utcnow()
        
        # Performance counters
        self.operation_count = 0
        self.error_count = 0
        self.last_operation_time = None
        
        self._log_initialization()
    
    def _log_initialization(self):
        """Log component initialization"""
        logger.info(f"{self.component_name} initialized - history: {self.history_duration.total_seconds()/60:.0f}min")
        self.is_initialized = True
    
    def _cleanup_old_entries(self, data_collection: deque = None):
        """Clean up old entries from historical data"""
        if data_collection is None:
            data_collection = self.history
            
        cutoff_time = datetime.utcnow() - self.history_duration
        
        with self.history_lock:
            while (data_collection and 
                   hasattr(data_collection[0], 'timestamp') and 
                   data_collection[0].timestamp < cutoff_time):
                data_collection.popleft()
    
    def _record_operation(self, success: bool = True):
        """Record operation for statistics"""
        self.operation_count += 1
        self.last_operation_time = datetime.utcnow()
        if not success:
            self.error_count += 1
    
    def get_status(self) -> Dict[str, Any]:
        """Get component status information"""
        uptime_seconds = (datetime.utcnow() - self.initialization_time).total_seconds()
        
        return {
            'component': self.component_name,
            'status': 'running' if self.is_running else 'stopped',
            'initialized': self.is_initialized,
            'uptime_seconds': uptime_seconds,
            'operation_count': self.operation_count,
            'error_count': self.error_count,
            'error_rate': (self.error_count / max(self.operation_count, 1)) * 100,
            'last_operation': MonitoringUtils.format_timestamp(self.last_operation_time) if self.last_operation_time else None,
            'history_size': len(self.history),
            'timestamp': MonitoringUtils.format_timestamp()
        }
    
    @abstractmethod
    def cleanup(self) -> None:
        """Cleanup component resources - must be implemented by subclasses"""
        pass
    
    def _base_cleanup(self):
        """Base cleanup functionality"""
        self.is_running = False
        
        with self.history_lock:
            self.history.clear()
        
        logger.info(f"{self.component_name} base cleanup completed")


class ThreadedMonitoringComponent(BaseMonitoringComponent):
    """Base class for monitoring components that use background threads"""
    
    def __init__(self, 
                 history_duration_minutes: int = 60,
                 component_name: str = None,
                 worker_threads: int = 1):
        super().__init__(history_duration_minutes, component_name)
        
        # Thread management
        self.worker_threads = worker_threads
        self.threads: List[threading.Thread] = []
        self.shutdown_event = threading.Event()
        self.thread_pool = None
    
    def _start_threads(self):
        """Start background threads for monitoring"""
        if self.is_running:
            logger.warning(f"{self.component_name} threads already running")
            return False
        
        self.is_running = True
        self.shutdown_event.clear()
        
        return True
    
    def _stop_threads(self, timeout: float = 5.0):
        """Stop background threads gracefully"""
        if not self.is_running:
            return True
        
        self.is_running = False
        self.shutdown_event.set()
        
        # Wait for threads to finish
        for thread in self.threads:
            if thread.is_alive():
                thread.join(timeout=timeout)
        
        # Clean thread pool if exists
        if self.thread_pool:
            self.thread_pool.shutdown(wait=True)
            self.thread_pool = None
        
        self.threads.clear()
        logger.info(f"{self.component_name} threads stopped")
        return True
    
    def cleanup(self):
        """Cleanup threaded component"""
        self._stop_threads()
        self._base_cleanup()


# Performance metric helpers
def create_metric_dict(operation: str, 
                      duration_ms: float = None,
                      success: bool = True,
                      timestamp: datetime = None,
                      **kwargs) -> Dict[str, Any]:
    """Create standardized metric dictionary"""
    if timestamp is None:
        timestamp = datetime.utcnow()
    
    metric = {
        'operation': operation,
        'success': success,
        'timestamp': MonitoringUtils.format_timestamp(timestamp),
    }
    
    if duration_ms is not None:
        metric['duration_ms'] = duration_ms
    
    # Add any additional fields
    metric.update(kwargs)
    
    return metric


# Decorator for performance tracking
def track_performance(operation_name: str = None):
    """Decorator to track method performance"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            success = False
            
            try:
                result = func(*args, **kwargs)
                success = True
                return result
            except Exception as e:
                logger.error(f"Performance tracking error in {op_name}: {e}")
                raise
            finally:
                duration_ms = (time.time() - start_time) * 1000
                
                # Try to record in global performance tracker if available
                try:
                    # This will be implemented when we refactor the performance tracker
                    pass
                except:
                    pass  # Fail silently
        
        return wrapper
    return decorator