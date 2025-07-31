"""
PERFORMANCE TRACKER
===================

Tracks application performance metrics including execution times,
throughput, and response times.
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from collections import defaultdict, deque
from dataclasses import dataclass
from contextlib import contextmanager
import logging
from .base_monitoring import BaseMonitoringComponent, MonitoringUtils, create_metric_dict

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetric:
    """Container for a single performance measurement"""
    operation: str
    duration_ms: float
    timestamp: datetime
    success: bool
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'operation': self.operation,
            'duration_ms': self.duration_ms,
            'timestamp': MonitoringUtils.format_timestamp(self.timestamp),
            'success': self.success,
            'metadata': self.metadata or {}
        }

class PerformanceTracker(BaseMonitoringComponent):
    """
    Tracks application performance metrics with automatic aggregation.
    """
    
    def __init__(self, 
                 history_duration_minutes: int = 60,
                 aggregation_window_seconds: int = 60):
        """
        Initialize performance tracker
        
        Args:
            history_duration_minutes: How long to keep detailed metrics
            aggregation_window_seconds: Window size for aggregated metrics
        """
        super().__init__(
            history_duration_minutes=history_duration_minutes,
            component_name="PerformanceTracker"
        )
        
        self.aggregation_window = timedelta(seconds=aggregation_window_seconds)
        
        # Raw metrics storage
        self.metrics: deque = deque()
        self.metrics_lock = threading.RLock()
        
        # Aggregated metrics by operation type
        self.aggregated_metrics: Dict[str, deque] = defaultdict(lambda: deque())
        
        # Current operation tracking (for nested operations)
        self._operation_stack = threading.local()
        
        # Performance counters (additional to base class)
        self.total_operations = 0
        self.failed_operations = 0

    @contextmanager
    def track_operation(self, operation: str, metadata: Dict[str, Any] = None):
        """
        Context manager to track operation performance
        
        Usage:
            with tracker.track_operation("database_query", {"table": "users"}):
                # database operation
                pass
        """
        start_time = time.time()
        success = False
        error = None
        
        # Initialize operation stack if not exists
        if not hasattr(self._operation_stack, 'stack'):
            self._operation_stack.stack = []
        
        self._operation_stack.stack.append(operation)
        
        try:
            yield
            success = True
        except Exception as e:
            error = str(e)
            raise
        finally:
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000
            
            # Pop from stack
            if self._operation_stack.stack:
                self._operation_stack.stack.pop()
            
            # Record metric
            self.record_metric(
                operation=operation,
                duration_ms=duration_ms,
                success=success,
                metadata={**(metadata or {}), **({'error': error} if error else {})}
            )

    def record_metric(self, 
                     operation: str, 
                     duration_ms: float, 
                     success: bool = True,
                     metadata: Dict[str, Any] = None) -> None:
        """Record a performance metric manually"""
        with self.metrics_lock:
            metric = PerformanceMetric(
                operation=operation,
                duration_ms=duration_ms,
                timestamp=datetime.utcnow(),
                success=success,
                metadata=metadata
            )
            
            self.metrics.append(metric)
            self.total_operations += 1
            
            if not success:
                self.failed_operations += 1
            
            # Clean old metrics
            self._cleanup_old_metrics()
            
            # Update aggregated metrics
            self._update_aggregated_metrics(metric)

    def _cleanup_old_metrics(self) -> None:
        """Remove metrics older than history duration"""
        cutoff_time = datetime.utcnow() - self.history_duration
        
        # Clean raw metrics
        while self.metrics and self.metrics[0].timestamp < cutoff_time:
            self.metrics.popleft()
        
        # Clean aggregated metrics
        for operation_metrics in self.aggregated_metrics.values():
            while operation_metrics and operation_metrics[0].timestamp < cutoff_time:
                operation_metrics.popleft()

    def _update_aggregated_metrics(self, metric: PerformanceMetric) -> None:
        """Update aggregated metrics for the operation"""
        operation = metric.operation
        
        # Find or create aggregation window
        window_start = self._get_window_start(metric.timestamp)
        
        # Check if we need a new aggregation window
        operation_aggregates = self.aggregated_metrics[operation]
        
        if not operation_aggregates or operation_aggregates[-1]['window_start'] != window_start:
            # Create new aggregation window
            new_aggregate = {
                'operation': operation,
                'window_start': window_start,
                'window_end': window_start + self.aggregation_window,
                'timestamp': window_start,
                'count': 0,
                'success_count': 0,
                'failure_count': 0,
                'total_duration_ms': 0.0,
                'min_duration_ms': float('inf'),
                'max_duration_ms': 0.0,
                'durations': []  # For percentile calculations
            }
            operation_aggregates.append(new_aggregate)
        
        # Update current window
        current_window = operation_aggregates[-1]
        current_window['count'] += 1
        current_window['total_duration_ms'] += metric.duration_ms
        current_window['min_duration_ms'] = min(current_window['min_duration_ms'], metric.duration_ms)
        current_window['max_duration_ms'] = max(current_window['max_duration_ms'], metric.duration_ms)
        current_window['durations'].append(metric.duration_ms)
        
        if metric.success:
            current_window['success_count'] += 1
        else:
            current_window['failure_count'] += 1

    def _get_window_start(self, timestamp: datetime) -> datetime:
        """Calculate aggregation window start time"""
        seconds_since_epoch = timestamp.timestamp()
        window_seconds = self.aggregation_window.total_seconds()
        window_start_seconds = (seconds_since_epoch // window_seconds) * window_seconds
        return datetime.fromtimestamp(window_start_seconds)

    # PUBLIC API METHODS
    # ==================
    
    def get_operation_stats(self, operation: str, minutes: int = 10) -> Dict[str, Any]:
        """Get performance statistics for a specific operation"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        
        with self.metrics_lock:
            # Get recent metrics for this operation
            recent_metrics = [
                m for m in self.metrics 
                if m.operation == operation and m.timestamp >= cutoff_time
            ]
            
            if not recent_metrics:
                return {'operation': operation, 'status': 'no_data'}
            
            # Calculate statistics
            durations = [m.duration_ms for m in recent_metrics]
            successes = [m for m in recent_metrics if m.success]
            failures = [m for m in recent_metrics if not m.success]
            
            durations.sort()
            total_count = len(recent_metrics)
            
            stats = {
                'operation': operation,
                'time_window_minutes': minutes,
                'total_count': total_count,
                'success_count': len(successes),
                'failure_count': len(failures),
                'success_rate': (len(successes) / total_count) * 100 if total_count > 0 else 0,
                'duration_stats': {
                    'avg_ms': sum(durations) / len(durations),
                    'min_ms': min(durations),
                    'max_ms': max(durations),
                    'p50_ms': durations[len(durations) // 2] if durations else 0,
                    'p95_ms': durations[int(len(durations) * 0.95)] if durations else 0,
                    'p99_ms': durations[int(len(durations) * 0.99)] if durations else 0
                },
                'throughput': {
                    'operations_per_minute': total_count / minutes,
                    'operations_per_second': total_count / (minutes * 60)
                }
            }
            
            return stats

    def get_all_operations_summary(self, minutes: int = 10) -> Dict[str, Any]:
        """Get summary of all tracked operations"""
        with self.metrics_lock:
            cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
            recent_metrics = [m for m in self.metrics if m.timestamp >= cutoff_time]
            
            if not recent_metrics:
                return {'status': 'no_data', 'time_window_minutes': minutes}
            
            # Group by operation
            operations = defaultdict(list)
            for metric in recent_metrics:
                operations[metric.operation].append(metric)
            
            # Calculate summary for each operation
            operation_summaries = {}
            for operation, metrics in operations.items():
                durations = [m.duration_ms for m in metrics]
                successes = [m for m in metrics if m.success]
                
                operation_summaries[operation] = {
                    'count': len(metrics),
                    'success_count': len(successes),
                    'success_rate': (len(successes) / len(metrics)) * 100,
                    'avg_duration_ms': sum(durations) / len(durations),
                    'min_duration_ms': min(durations),
                    'max_duration_ms': max(durations)
                }
            
            # Overall summary
            total_operations = len(recent_metrics)
            total_successes = len([m for m in recent_metrics if m.success])
            all_durations = [m.duration_ms for m in recent_metrics]
            
            return {
                'status': 'ok',
                'time_window_minutes': minutes,
                'overall': {
                    'total_operations': total_operations,
                    'success_rate': (total_successes / total_operations) * 100,
                    'avg_duration_ms': sum(all_durations) / len(all_durations),
                    'throughput_per_minute': total_operations / minutes
                },
                'by_operation': operation_summaries,
                'tracked_operations': list(operations.keys())
            }

    def get_slow_operations(self, 
                           threshold_ms: float = 1000, 
                           minutes: int = 10) -> List[Dict[str, Any]]:
        """Get operations that exceeded duration threshold"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        
        with self.metrics_lock:
            slow_operations = [
                m.to_dict() for m in self.metrics 
                if (m.timestamp >= cutoff_time and 
                    m.duration_ms > threshold_ms)
            ]
            
            # Sort by duration (slowest first)
            slow_operations.sort(key=lambda x: x['duration_ms'], reverse=True)
            
            return slow_operations

    def get_error_operations(self, minutes: int = 10) -> List[Dict[str, Any]]:
        """Get failed operations"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        
        with self.metrics_lock:
            error_operations = [
                m.to_dict() for m in self.metrics 
                if (m.timestamp >= cutoff_time and not m.success)
            ]
            
            # Sort by timestamp (most recent first)
            error_operations.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return error_operations

    def get_performance_trends(self, operation: str = None, hours: int = 1) -> Dict[str, Any]:
        """Get performance trends over time"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        with self.metrics_lock:
            # Get relevant aggregated metrics
            if operation:
                aggregated_data = [
                    window for window in self.aggregated_metrics.get(operation, [])
                    if window['timestamp'] >= cutoff_time
                ]
            else:
                # All operations combined
                aggregated_data = []
                for op_windows in self.aggregated_metrics.values():
                    aggregated_data.extend([
                        window for window in op_windows
                        if window['timestamp'] >= cutoff_time
                    ])
            
            if not aggregated_data:
                return {'status': 'no_data', 'operation': operation, 'hours': hours}
            
            # Calculate trends
            trend_data = []
            for window in sorted(aggregated_data, key=lambda x: x['timestamp']):
                avg_duration = (window['total_duration_ms'] / window['count']) if window['count'] > 0 else 0
                success_rate = (window['success_count'] / window['count'] * 100) if window['count'] > 0 else 0
                
                trend_data.append({
                    'timestamp': MonitoringUtils.format_timestamp(window['timestamp']),
                    'avg_duration_ms': avg_duration,
                    'success_rate': success_rate,
                    'throughput': window['count'] / (self.aggregation_window.total_seconds() / 60),  # per minute
                    'operation': window.get('operation', 'all')
                })
            
            return {
                'status': 'ok',
                'operation': operation or 'all',
                'hours': hours,
                'data_points': len(trend_data),
                'trends': trend_data
            }

    def get_tracker_stats(self) -> Dict[str, Any]:
        """Get performance tracker statistics"""
        with self.metrics_lock:
            return {
                'total_operations_tracked': self.total_operations,
                'failed_operations': self.failed_operations,
                'success_rate': ((self.total_operations - self.failed_operations) / self.total_operations * 100) if self.total_operations > 0 else 100,
                'metrics_in_memory': len(self.metrics),
                'tracked_operation_types': len(self.aggregated_metrics),
                'operation_types': list(self.aggregated_metrics.keys()),
                'history_duration_minutes': self.history_duration.total_seconds() / 60,
                'aggregation_window_seconds': self.aggregation_window.total_seconds()
            }

    def clear_metrics(self) -> None:
        """Clear all metrics (use with caution)"""
        with self.metrics_lock:
            self.metrics.clear()
            self.aggregated_metrics.clear()
            self.total_operations = 0
            self.failed_operations = 0
            logger.info("All performance metrics cleared")
    
    # ENHANCED FEATURES
    # =================
    
    def add_custom_metric(self, 
                         metric_name: str, 
                         value: float, 
                         tags: Dict[str, str] = None,
                         timestamp: datetime = None) -> None:
        """Add a custom metric to the performance tracker"""
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        custom_metric = PerformanceMetric(
            operation=f"custom_{metric_name}",
            duration_ms=value,  # Using duration field for custom value
            timestamp=timestamp,
            success=True,
            metadata={
                'metric_type': 'custom',
                'metric_name': metric_name,
                'tags': tags or {},
                'is_custom': True
            }
        )
        
        with self.metrics_lock:
            self.metrics.append(custom_metric)
            self.total_operations += 1
            
            # Add to aggregated metrics
            operation = f"custom_{metric_name}"
            self.aggregated_metrics[operation].append(custom_metric)
            
            # Cleanup old metrics
            self._cleanup_old_metrics()
        
        logger.debug(f"Custom metric added: {metric_name} = {value}")
    
    def get_custom_metrics(self, metric_name: str = None, minutes: int = 60) -> List[Dict[str, Any]]:
        """Get custom metrics, optionally filtered by name and time"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        
        with self.metrics_lock:
            custom_metrics = []
            for metric in self.metrics:
                try:
                    # Ensure metric is PerformanceMetric and has required attributes
                    if (hasattr(metric, 'metadata') and 
                        hasattr(metric, 'timestamp') and
                        metric.metadata and 
                        metric.metadata.get('is_custom', False) and
                        metric.timestamp >= cutoff_time):
                        custom_metrics.append(metric)
                except Exception as e:
                    logger.warning(f"Error processing metric in get_custom_metrics: {e}")
                    continue
            
            # Filter by metric name if specified
            if metric_name:
                filtered_metrics = []
                for metric in custom_metrics:
                    try:
                        if metric.metadata.get('metric_name') == metric_name:
                            filtered_metrics.append(metric)
                    except Exception as e:
                        logger.warning(f"Error filtering metric by name: {e}")
                        continue
                custom_metrics = filtered_metrics
            
            # Convert to dictionary format
            result = []
            for metric in custom_metrics:
                try:
                    result.append({
                        'metric_name': metric.metadata.get('metric_name') if metric.metadata else None,
                        'value': metric.duration_ms,
                        'timestamp': MonitoringUtils.format_timestamp(metric.timestamp),
                        'tags': metric.metadata.get('tags', {}) if metric.metadata else {},
                        'operation': metric.operation
                    })
                except Exception as e:
                    logger.warning(f"Error converting metric to dict: {e}")
                    continue
            
            return result
    
    def detect_bottlenecks(self, 
                          operation: str = None, 
                          threshold_percentile: float = 95,
                          minutes: int = 30) -> Dict[str, Any]:
        """Detect performance bottlenecks in operations"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        
        with self.metrics_lock:
            # Get recent metrics
            recent_metrics = []
            for metric in self.metrics:
                try:
                    # Ensure metric is PerformanceMetric object
                    if (hasattr(metric, 'timestamp') and 
                        hasattr(metric, 'success') and
                        metric.timestamp >= cutoff_time and 
                        metric.success):
                        recent_metrics.append(metric)
                except Exception as e:
                    logger.warning(f"Error processing metric in detect_bottlenecks: {type(metric)} - {e}")
                    continue
            
            if not recent_metrics:
                return {
                    'status': 'no_data',
                    'message': 'No recent performance data available'
                }
            
            # Group by operation
            operations_data = defaultdict(list)
            for metric in recent_metrics:
                # Skip custom metrics for bottleneck detection
                if not (metric.metadata and metric.metadata.get('is_custom', False)):
                    operations_data[metric.operation].append(metric.duration_ms)
            
            if operation and operation not in operations_data:
                return {
                    'status': 'operation_not_found',
                    'message': f'Operation "{operation}" not found in recent data'
                }
            
            bottlenecks = {
                'timestamp': MonitoringUtils.format_timestamp(),
                'analysis_period_minutes': minutes,
                'threshold_percentile': threshold_percentile,
                'bottlenecks': [],
                'slow_operations': [],
                'overall_status': 'healthy'
            }
            
            try:
                # Analyze each operation or specific operation
                operations_to_analyze = {operation: operations_data[operation]} if operation else operations_data
                
                for op_name, durations in operations_to_analyze.items():
                    if len(durations) < 5:  # Need minimum samples
                        continue
                    
                    # Calculate statistics
                    avg_duration = sum(durations) / len(durations)
                    max_duration = max(durations)
                    min_duration = min(durations)
                    
                    # Calculate percentiles
                    sorted_durations = sorted(durations)
                    p95_index = int(len(sorted_durations) * (threshold_percentile / 100))
                    p95_duration = sorted_durations[min(p95_index, len(sorted_durations) - 1)]
                    
                    # Detect bottlenecks
                    is_bottleneck = False
                    severity = 'low'
                    
                    # High average duration (>1 second)
                    if avg_duration > 1000:
                        is_bottleneck = True
                        severity = 'high'
                    # High percentile duration (>500ms)
                    elif p95_duration > 500:
                        is_bottleneck = True
                        severity = 'medium'
                    # High variability (max is 10x average)
                    elif max_duration > avg_duration * 10:
                        is_bottleneck = True
                        severity = 'medium'
                    # Many slow operations (>100ms average)
                    elif avg_duration > 100 and len(durations) > 20:
                        severity = 'low'
                        bottlenecks['slow_operations'].append({
                            'operation': op_name,
                            'avg_duration_ms': round(avg_duration, 2),
                            'max_duration_ms': round(max_duration, 2),
                            'p95_duration_ms': round(p95_duration, 2),
                            'sample_count': len(durations),
                            'recommendation': 'Monitor this operation for potential optimization'
                        })
                    
                    if is_bottleneck:
                        bottlenecks['bottlenecks'].append({
                            'operation': op_name,
                            'severity': severity,
                            'avg_duration_ms': round(avg_duration, 2),
                            'max_duration_ms': round(max_duration, 2),
                            'min_duration_ms': round(min_duration, 2),
                            'p95_duration_ms': round(p95_duration, 2),
                            'sample_count': len(durations),
                            'variability_ratio': round(max_duration / avg_duration, 2),
                            'recommendation': self._get_bottleneck_recommendation(severity, avg_duration, max_duration)
                        })
                        
                        if severity == 'high':
                            bottlenecks['overall_status'] = 'critical'
                        elif severity == 'medium' and bottlenecks['overall_status'] != 'critical':
                            bottlenecks['overall_status'] = 'warning'
                
                # Summary
                bottlenecks['summary'] = {
                    'total_operations_analyzed': len(operations_to_analyze),
                    'bottlenecks_detected': len(bottlenecks['bottlenecks']),
                    'slow_operations_detected': len(bottlenecks['slow_operations']),
                    'total_samples': sum(len(durations) for durations in operations_to_analyze.values())
                }
                
            except Exception as e:
                logger.error(f"Error detecting bottlenecks: {e}")
                bottlenecks['status'] = 'error'
                bottlenecks['error'] = str(e)
            
            return bottlenecks
    
    def _get_bottleneck_recommendation(self, severity: str, avg_duration: float, max_duration: float) -> str:
        """Get recommendation based on bottleneck severity and metrics"""
        if severity == 'high':
            if avg_duration > 5000:  # 5 seconds
                return "Critical: Operation is extremely slow. Consider algorithm optimization or caching."
            elif avg_duration > 2000:  # 2 seconds
                return "High: Operation is very slow. Review implementation and consider optimization."
            else:
                return "High: Operation has performance issues. Investigate and optimize."
        elif severity == 'medium':
            if max_duration > avg_duration * 20:
                return "Medium: High variability detected. Look for edge cases or resource contention."
            else:
                return "Medium: Operation is slower than optimal. Consider minor optimizations."
        else:
            return "Low: Monitor this operation for trends and potential future optimization."
    
    def get_performance_insights(self, minutes: int = 60) -> Dict[str, Any]:
        """Get comprehensive performance insights and recommendations"""
        insights = {
            'timestamp': MonitoringUtils.format_timestamp(),
            'analysis_period_minutes': minutes,
            'insights': [],
            'recommendations': [],
            'performance_score': 100
        }
        
        try:
            # Get bottlenecks
            bottlenecks = self.detect_bottlenecks(minutes=minutes)
            
            # Analyze performance patterns
            cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
            recent_metrics = [
                metric for metric in self.metrics
                if metric.timestamp >= cutoff_time
            ]
            
            if not recent_metrics:
                insights['insights'].append("No recent performance data available for analysis")
                return insights
            
            # Calculate overall statistics
            total_operations = len(recent_metrics)
            failed_operations = len([m for m in recent_metrics if not m.success])
            success_rate = ((total_operations - failed_operations) / total_operations * 100) if total_operations > 0 else 100
            
            all_durations = [m.duration_ms for m in recent_metrics if m.success]
            if all_durations:
                avg_duration = sum(all_durations) / len(all_durations)
                max_duration = max(all_durations)
                
                # Performance scoring
                performance_score = 100
                
                # Deduct for slow operations
                if avg_duration > 1000:
                    performance_score -= 40
                elif avg_duration > 500:
                    performance_score -= 20
                elif avg_duration > 100:
                    performance_score -= 10
                
                # Deduct for failures
                if success_rate < 95:
                    performance_score -= 30
                elif success_rate < 99:
                    performance_score -= 10
                
                # Deduct for bottlenecks
                if bottlenecks.get('overall_status') == 'critical':
                    performance_score -= 30
                elif bottlenecks.get('overall_status') == 'warning':
                    performance_score -= 15
                
                insights['performance_score'] = max(0, performance_score)
                
                # Generate insights
                insights['insights'].extend([
                    f"Analyzed {total_operations} operations over {minutes} minutes",
                    f"Success rate: {success_rate:.1f}%",
                    f"Average operation duration: {avg_duration:.1f}ms",
                    f"Maximum operation duration: {max_duration:.1f}ms"
                ])
                
                # Generate recommendations
                if performance_score < 70:
                    insights['recommendations'].append("Critical: Immediate performance optimization needed")
                elif performance_score < 85:
                    insights['recommendations'].append("Warning: Performance improvements recommended")
                else:
                    insights['recommendations'].append("Good: Performance is within acceptable range")
                
                if avg_duration > 500:
                    insights['recommendations'].append("Consider optimizing slow operations")
                
                if success_rate < 95:
                    insights['recommendations'].append("Investigate and fix operation failures")
                
                # Add bottleneck recommendations
                if bottlenecks.get('bottlenecks'):
                    insights['recommendations'].append(f"Address {len(bottlenecks['bottlenecks'])} detected bottlenecks")
                
            insights['bottlenecks_summary'] = bottlenecks
            
        except Exception as e:
            logger.error(f"Error generating performance insights: {e}")
            insights['error'] = str(e)
        
        return insights
    
    def cleanup(self) -> None:
        """Cleanup performance tracker resources"""
        with self.metrics_lock:
            # Clear all metrics
            self.metrics.clear()
            
            # Clear aggregated metrics
            self.aggregated_metrics.clear()
            
            # Reset counters
            self.total_operations = 0
            self.failed_operations = 0
        
        # Call base cleanup
        self._base_cleanup()
        
        logger.info("PerformanceTracker cleanup completed")

# Global performance tracker instance
_global_tracker: Optional[PerformanceTracker] = None
_tracker_lock = threading.Lock()

def get_global_tracker() -> PerformanceTracker:
    """Get or create global performance tracker instance"""
    global _global_tracker
    
    if _global_tracker is None:
        with _tracker_lock:
            if _global_tracker is None:
                _global_tracker = PerformanceTracker()
    
    return _global_tracker

def track_performance(operation: str, metadata: Dict[str, Any] = None):
    """Decorator for tracking function performance"""
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            tracker = get_global_tracker()
            with tracker.track_operation(operation, metadata):
                return func(*args, **kwargs)
        return wrapper
    return decorator