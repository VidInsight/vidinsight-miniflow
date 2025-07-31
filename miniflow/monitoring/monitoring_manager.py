"""
MONITORING MANAGER
==================

Central management for all monitoring components.
Provides unified access to metrics, performance tracking, and database monitoring.
"""

import time
import logging
from typing import Dict, Any, Optional
from .metrics_collector import MetricsCollector
from .performance_tracker import PerformanceTracker
from .database_metrics import DatabaseMetrics
from .api_metrics import APIMetricsMiddleware
from .metrics_export import MetricsExporter

logger = logging.getLogger(__name__)

class MonitoringManager:
    """
    Central manager for all monitoring components.
    Provides unified interface for metrics collection, performance tracking, and monitoring.
    """
    
    def __init__(self, 
                 collection_interval: float = 1.0,
                 history_duration_minutes: int = 60,
                 enable_detailed_metrics: bool = True):
        """
        Initialize monitoring manager with all components
        
        Args:
            collection_interval: Seconds between metric collections
            history_duration_minutes: How long to keep historical data
            enable_detailed_metrics: Whether to collect detailed metrics
        """
        self.collection_interval = collection_interval
        self.history_duration_minutes = history_duration_minutes
        self.enable_detailed_metrics = enable_detailed_metrics
        
        # Initialize components
        self.metrics_collector: Optional[MetricsCollector] = None
        self.performance_tracker: Optional[PerformanceTracker] = None
        self.database_metrics: Optional[DatabaseMetrics] = None
        self.api_metrics: Optional[APIMetricsMiddleware] = None
        
        # Status tracking
        self.is_started = False
        self.components_status = {
            'metrics_collector': 'not_initialized',
            'performance_tracker': 'not_initialized', 
            'database_metrics': 'not_initialized',
            'api_metrics': 'not_initialized'
        }
    
    def start(self, database_engine=None) -> bool:
        """
        Start all monitoring components
        
        Args:
            database_engine: Database engine for DB monitoring
            
        Returns:
            True if all components started successfully
        """
        try:
            # Initialize metrics collector
            self.metrics_collector = MetricsCollector(
                collection_interval=self.collection_interval,
                history_duration_minutes=self.history_duration_minutes,
                enable_detailed_metrics=self.enable_detailed_metrics
            )
            
            # Initialize performance tracker
            self.performance_tracker = PerformanceTracker(
                history_duration_minutes=self.history_duration_minutes,
                aggregation_window_seconds=60
            )
            
            # Initialize database metrics
            self.database_metrics = DatabaseMetrics(
                history_duration_minutes=self.history_duration_minutes
            )
            
            # Initialize API metrics (placeholder - will be set when FastAPI app is available)
            self.api_metrics = None
            
            # Initialize metrics exporter
            self.metrics_exporter = MetricsExporter(monitoring_manager=self)
            
            # Register database engine if provided
            if database_engine and self.database_metrics:
                try:
                    self.database_metrics.register_engine(database_engine)
                    self.components_status['database_metrics'] = 'healthy'
                    logger.info("Database engine registered for monitoring")
                except Exception as e:
                    logger.warning(f"Failed to register database engine: {e}")
                    self.components_status['database_metrics'] = 'warning'
            
            # Start metrics collection
            if self.metrics_collector.start_collection():
                self.components_status['metrics_collector'] = 'healthy'
                logger.info("Metrics collection started successfully")
            else:
                self.components_status['metrics_collector'] = 'error'
                logger.warning("Failed to start metrics collection")
            
            # Performance tracker doesn't need explicit start
            self.components_status['performance_tracker'] = 'healthy'
            
            # API metrics placeholder (will be initialized when FastAPI app is available)
            self.components_status['api_metrics'] = 'unavailable'
            
            self.is_started = True
            logger.info("MonitoringManager started successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start MonitoringManager: {e}")
            self.is_started = False
            return False
    
    def stop(self) -> bool:
        """
        Stop all monitoring components
        
        Returns:
            True if all components stopped successfully
        """
        success = True
        
        try:
            # Stop metrics collector
            if self.metrics_collector:
                try:
                    self.metrics_collector.stop_collection()
                    self.components_status['metrics_collector'] = 'stopped'
                    logger.info("Metrics collection stopped successfully")
                except Exception as e:
                    logger.error(f"Error stopping metrics collector: {e}")
                    success = False
            
            # Stop performance tracker (cleanup any background tasks)
            if self.performance_tracker:
                try:
                    # Performance tracker doesn't have explicit stop, but we clean up
                    self.components_status['performance_tracker'] = 'stopped'
                    logger.info("Performance tracker stopped successfully")
                except Exception as e:
                    logger.error(f"Error stopping performance tracker: {e}")
                    success = False
            
            # Stop database metrics (cleanup listeners)
            if self.database_metrics:
                try:
                    self.database_metrics.cleanup()
                    self.components_status['database_metrics'] = 'stopped'
                    logger.info("Database metrics stopped successfully")
                except Exception as e:
                    logger.error(f"Error stopping database metrics: {e}")
                    success = False
            
            # API metrics (placeholder, no explicit stop needed)
            self.components_status['api_metrics'] = 'stopped'
            
            self.is_started = False
            logger.info("MonitoringManager stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping MonitoringManager: {e}")
            success = False
        
        return success
    
    def cleanup(self) -> None:
        """Cleanup all monitoring components and resources"""
        # Stop all components first
        self.stop()
        
        # Cleanup each component
        if self.metrics_collector:
            try:
                self.metrics_collector.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up metrics collector: {e}")
        
        if self.performance_tracker:
            try:
                self.performance_tracker.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up performance tracker: {e}")
        
        if self.database_metrics:
            try:
                self.database_metrics.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up database metrics: {e}")
        
        if self.api_metrics:
            try:
                self.api_metrics.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up API metrics: {e}")
        
        if self.metrics_exporter:
            try:
                self.metrics_exporter.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up metrics exporter: {e}")
        
        # Clear all references
        self.metrics_collector = None
        self.performance_tracker = None
        self.database_metrics = None
        self.api_metrics = None
        self.metrics_exporter = None
        
        # Reset status
        for component in self.components_status:
            self.components_status[component] = 'cleaned_up'
        
        logger.info("MonitoringManager cleanup completed")
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        if self.metrics_collector:
            return self.metrics_collector.get_current_metrics() or {}
        return {}
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics summary"""
        if self.performance_tracker:
            return {
                'operations_summary': self.performance_tracker.get_all_operations_summary(),
                'tracker_stats': self.performance_tracker.get_tracker_stats(),
                'slow_operations': self.performance_tracker.get_slow_operations(threshold_ms=1000, minutes=10),
                'error_operations': self.performance_tracker.get_error_operations(minutes=10)
            }
        return {}
    
    def get_database_metrics(self) -> Dict[str, Any]:
        """Get database metrics summary"""
        if self.database_metrics:
            return {
                'pool_status': self.database_metrics.get_pool_status(),
                'query_stats': self.database_metrics.get_query_stats(),
                'database_summary': self.database_metrics.get_database_summary(),
                'slow_queries': self.database_metrics.get_slow_queries(minutes=10),
                'failed_queries': self.database_metrics.get_failed_queries(minutes=10)
            }
        return {}
    
    def get_api_metrics(self) -> Dict[str, Any]:
        """Get API metrics summary"""
        if self.api_metrics:
            return {
                'request_stats': self.api_metrics.get_request_stats(),
                'response_stats': self.api_metrics.get_response_stats(),
                'error_stats': self.api_metrics.get_error_stats()
            }
        return {
            'status': 'unavailable',
            'reason': 'API metrics require FastAPI app integration'
        }
    
    def get_comprehensive_summary(self) -> Dict[str, Any]:
        """Get comprehensive monitoring summary"""
        return {
            'status': {
                'monitoring_manager': 'healthy' if self.is_started else 'stopped',
                'components': self.components_status.copy()
            },
            'system_metrics': self.get_system_metrics(),
            'performance_metrics': self.get_performance_metrics(),
            'database_metrics': self.get_database_metrics(),
            'api_metrics': self.get_api_metrics(),
            'collection_info': {
                'interval_seconds': self.collection_interval,
                'history_duration_minutes': self.history_duration_minutes,
                'detailed_metrics_enabled': self.enable_detailed_metrics
            }
        }
    
    def get_health_status(self) -> Dict[str, str]:
        """Get health status of all monitoring components"""
        return {
            'overall': 'healthy' if self.is_started else 'stopped',
            'metrics_collector': self.components_status.get('metrics_collector', 'unknown'),
            'performance_tracker': self.components_status.get('performance_tracker', 'unknown'),
            'database_metrics': self.components_status.get('database_metrics', 'unknown'),
            'api_metrics': self.components_status.get('api_metrics', 'unknown')
        }
    
    # Context manager support for easy usage
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
    
    # Performance tracking convenience methods
    def start_operation_tracking(self, operation_id: str, operation_name: str, **metadata):
        """Start tracking an operation (using record_metric)"""
        # Store operation start time for later use
        if not hasattr(self, '_operation_starts'):
            self._operation_starts = {}
        self._operation_starts[operation_id] = {
            'start_time': time.time(),
            'operation_name': operation_name,
            'metadata': metadata
        }
        return operation_id
    
    def stop_operation_tracking(self, operation_id: str, success: bool = True, **metadata):
        """Stop tracking an operation"""
        if (hasattr(self, '_operation_starts') and 
            operation_id in self._operation_starts and 
            self.performance_tracker):
            
            operation_info = self._operation_starts[operation_id]
            duration_ms = (time.time() - operation_info['start_time']) * 1000
            
            # Combine metadata
            combined_metadata = {**operation_info['metadata'], **metadata}
            
            # Record the metric
            self.performance_tracker.record_metric(
                operation=operation_info['operation_name'],
                duration_ms=duration_ms,
                success=success,
                metadata=combined_metadata
            )
            
            # Clean up
            del self._operation_starts[operation_id]
            return True
        return False
    
    def track_operation(self, operation_name: str, **metadata):
        """Context manager for operation tracking"""
        if self.performance_tracker:
            return self.performance_tracker.track_operation(operation_name, **metadata)
        return self._null_context_manager()
    
    def _null_context_manager(self):
        """Null context manager when performance tracker is not available"""
        class NullContextManager:
            def __enter__(self):
                return self
            def __exit__(self, exc_type, exc_val, exc_tb):
                pass
        return NullContextManager()
    
    def set_api_metrics(self, app):
        """Set API metrics with FastAPI app (for future integration)"""
        try:
            from .api_metrics import APIMetricsMiddleware
            self.api_metrics = APIMetricsMiddleware(
                app=app,
                performance_tracker=self.performance_tracker
            )
            self.components_status['api_metrics'] = 'healthy'
            logger.info("API metrics integrated with FastAPI app")
            return True
        except Exception as e:
            logger.error(f"Failed to integrate API metrics: {e}")
            self.components_status['api_metrics'] = 'error'
            return False
    
    # Convenience aliases for compatibility
    def get_metrics(self):
        """Alias for get_performance_metrics for test compatibility"""
        if self.performance_tracker:
            # Return simplified metrics list for test compatibility
            try:
                operations_summary = self.performance_tracker.get_all_operations_summary()
                # Convert to list format expected by tests
                operations_list = []
                for operation_name, stats in operations_summary.items():
                    if operation_name not in ['status', 'time_window_minutes', 'overall']:
                        operations_list.append({
                            'operation': operation_name,
                            'count': stats.get('count', 0),
                            'avg_duration_ms': stats.get('avg_duration_ms', 0)
                        })
                return operations_list
            except Exception as e:
                logger.warning(f"Error getting metrics for compatibility: {e}")
                return []
        return []
    
    def get_operation_stats(self, operation=None):
        """Alias for compatibility"""
        if self.performance_tracker and operation:
            return self.performance_tracker.get_operation_stats(operation)
        return {}
    
    def get_performance_summary(self):
        """Alias for compatibility"""
        return self.get_performance_metrics()
    
    def start_tracking(self, operation_id: str, operation_name: str, **metadata):
        """Alias for compatibility"""
        return self.start_operation_tracking(operation_id, operation_name, **metadata)
    
    def stop_tracking(self, operation_id: str, success: bool = True, **metadata):
        """Alias for compatibility"""
        return self.stop_operation_tracking(operation_id, success, **metadata)
    
    def get_query_metrics(self, minutes: int = 10):
        """Alias for compatibility"""
        if self.database_metrics:
            return self.database_metrics.get_query_stats(minutes)
        return {}
    
    def get_pool_metrics(self):
        """Alias for compatibility"""
        if self.database_metrics:
            return self.database_metrics.get_pool_status()
        return {}
    
    def get_performance_stats(self):
        """Alias for compatibility"""
        if self.database_metrics:
            return self.database_metrics.get_database_summary()
        return {}
    
    # ENHANCED FEATURES ACCESS
    # ========================
    
    def set_alert_thresholds(self, **kwargs):
        """Set alerting thresholds for system metrics"""
        if self.metrics_collector:
            return self.metrics_collector.set_alert_thresholds(**kwargs)
        return False
    
    def check_alerts(self):
        """Check current metrics against alert thresholds"""
        if self.metrics_collector:
            return self.metrics_collector.check_alerts()
        return {'status': 'no_metrics_collector'}
    
    def get_aggregated_metrics(self, **kwargs):
        """Get aggregated metrics over specified time period"""
        if self.metrics_collector:
            return self.metrics_collector.get_aggregated_metrics(**kwargs)
        return {'status': 'no_metrics_collector'}
    
    def detect_system_bottlenecks(self, **kwargs):
        """Detect system bottlenecks"""
        if self.metrics_collector:
            return self.metrics_collector.detect_bottlenecks(**kwargs)
        return {'status': 'no_metrics_collector'}
    
    def add_custom_metric(self, metric_name: str, value: float, **kwargs):
        """Add custom metric to performance tracker"""
        if self.performance_tracker:
            return self.performance_tracker.add_custom_metric(metric_name, value, **kwargs)
        return False
    
    def get_custom_metrics(self, **kwargs):
        """Get custom metrics from performance tracker"""
        if self.performance_tracker:
            return self.performance_tracker.get_custom_metrics(**kwargs)
        return []
    
    def detect_performance_bottlenecks(self, **kwargs):
        """Detect performance bottlenecks in operations"""
        if self.performance_tracker:
            return self.performance_tracker.detect_bottlenecks(**kwargs)
        return {'status': 'no_performance_tracker'}
    
    def get_performance_insights(self, **kwargs):
        """Get comprehensive performance insights"""
        if self.performance_tracker:
            return self.performance_tracker.get_performance_insights(**kwargs)
        return {'status': 'no_performance_tracker'}
    
    # METRICS EXPORT
    # ==============
    
    def export_prometheus_metrics(self):
        """Export metrics in Prometheus format"""
        if self.metrics_exporter:
            return self.metrics_exporter.export_prometheus_format()
        return "# No metrics exporter available\n"
    
    def export_json_metrics(self, include_detailed: bool = True):
        """Export metrics in JSON format"""
        if self.metrics_exporter:
            return self.metrics_exporter.export_json_format(include_detailed=include_detailed)
        return '{"error": "No metrics exporter available"}'
    
    def export_grafana_dashboard(self):
        """Get Grafana dashboard configuration"""
        if self.metrics_exporter:
            return self.metrics_exporter.export_grafana_dashboard_config()
        return {"error": "No metrics exporter available"}
    
    def save_metrics_to_file(self, format_type: str, file_path: str, **kwargs):
        """Save metrics to file"""
        if self.metrics_exporter:
            return self.metrics_exporter.save_to_file(format_type, file_path, **kwargs)
        return False
    
    def get_export_info(self):
        """Get information about export capabilities"""
        if self.metrics_exporter:
            return self.metrics_exporter.get_export_summary()
        return {"error": "No metrics exporter available"}