"""
DATABASE METRICS COLLECTOR
===========================

Tracks database connection pool status and query performance.
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import deque
import logging
import sqlalchemy
from sqlalchemy import event
from .base_monitoring import BaseMonitoringComponent, MonitoringUtils

logger = logging.getLogger(__name__)

class DatabaseMetrics(BaseMonitoringComponent):
    """
    Database metrics collector for connection pool and query performance monitoring.
    """
    
    def __init__(self, history_duration_minutes: int = 60):
        """Initialize database metrics collector"""
        super().__init__(
            history_duration_minutes=history_duration_minutes,
            component_name="DatabaseMetrics"
        )
        
        # Query performance tracking
        self.query_history: deque = deque()
        self.query_lock = threading.RLock()
        
        # Connection pool metrics
        self.pool_metrics: Dict[str, Any] = {}
        self.pool_lock = threading.RLock()
        
        # Engine tracking (using consistent engine URL as key)
        self.engines_tracked = set()
        
        # Performance counters (additional to base class)
        self.total_queries = 0
        self.slow_queries = 0
        self.failed_queries = 0

    def _get_sqlalchemy_engine(self, engine):
        """Helper to get actual SQLAlchemy engine from wrapper"""
        return engine.get_engine if hasattr(engine, 'get_engine') else engine
    
    def _truncate_statement(self, statement: str, max_length: int = 200) -> str:
        """Helper to truncate SQL statements consistently"""
        return MonitoringUtils.truncate_string(statement, max_length)

    def register_engine(self, engine) -> None:
        """Register SQLAlchemy engine for monitoring"""
        try:
            # Get actual SQLAlchemy engine from DatabaseEngine wrapper
            sqlalchemy_engine = self._get_sqlalchemy_engine(engine)
            engine_url = str(sqlalchemy_engine.url)
            
            if engine_url in self.engines_tracked:
                logger.debug(f"Engine {engine_url} already registered")
                return
            
            # Register query timing events
            @event.listens_for(sqlalchemy_engine, "before_cursor_execute")
            def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
                context._query_start_time = time.time()
                context._query_statement = self._truncate_statement(statement)
                context._query_executemany = executemany

            @event.listens_for(sqlalchemy_engine, "after_cursor_execute")
            def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
                if hasattr(context, '_query_start_time'):
                    duration_ms = (time.time() - context._query_start_time) * 1000
                    self._record_query(
                        statement=getattr(context, '_query_statement', self._truncate_statement(statement)),
                        duration_ms=duration_ms,
                        success=True,
                        executemany=getattr(context, '_query_executemany', executemany)
                    )

            @event.listens_for(sqlalchemy_engine, "handle_error")
            def handle_error(exception_context):
                if hasattr(exception_context.connection._connection, '_query_start_time'):
                    duration_ms = (time.time() - exception_context.connection._connection._query_start_time) * 1000
                else:
                    duration_ms = 0
                
                statement = str(exception_context.statement) if exception_context.statement else "UNKNOWN"
                self._record_query(
                    statement=self._truncate_statement(statement),
                    duration_ms=duration_ms,
                    success=False,
                    error=str(exception_context.sqlalchemy_exception)
                )

            # Track this engine
            self.engines_tracked.add(engine_url)
            
            logger.info(f"Database engine registered for monitoring: {getattr(sqlalchemy_engine.url, 'database', 'unknown')}")
            
        except Exception as e:
            logger.error(f"Failed to register engine for monitoring: {e}")

    def _record_query(self, 
                     statement: str, 
                     duration_ms: float, 
                     success: bool = True,
                     executemany: bool = False,
                     error: str = None) -> None:
        """Record a database query for performance tracking"""
        with self.query_lock:
            query_record = {
                'timestamp': datetime.utcnow(),
                'statement': statement,
                'duration_ms': duration_ms,
                'success': success,
                'executemany': executemany,
                'error': error
            }
            
            self.query_history.append(query_record)
            self.total_queries += 1
            
            if not success:
                self.failed_queries += 1
            
            if duration_ms > 1000:  # Slow query threshold: 1 second
                self.slow_queries += 1
            
            # Clean old records
            self._cleanup_old_queries()

    def _cleanup_old_queries(self) -> None:
        """Remove query records older than history duration"""
        cutoff_time = datetime.utcnow() - self.history_duration
        
        while self.query_history and self.query_history[0]['timestamp'] < cutoff_time:
            self.query_history.popleft()

    def update_pool_metrics(self, engine) -> None:
        """Update connection pool metrics for given engine"""
        try:
            # Get actual SQLAlchemy engine from DatabaseEngine wrapper
            sqlalchemy_engine = self._get_sqlalchemy_engine(engine)
            pool = sqlalchemy_engine.pool
            
            with self.pool_lock:
                pool_info = {
                    'timestamp': datetime.utcnow(),
                    'size': pool.size(),
                    'checked_in': pool.checkedin(),
                    'checked_out': pool.checkedout(),
                    'overflow': pool.overflow(),
                    'invalid': pool.invalid(),
                    'total_connections': pool.size() + pool.overflow(),
                    'utilization': 0.0,
                    'status': 'healthy'
                }
                
                # Calculate utilization percentage
                total_capacity = pool.size() + getattr(pool, '_max_overflow', 0)
                if total_capacity > 0:
                    active_connections = pool.checkedout()
                    pool_info['utilization'] = (active_connections / total_capacity) * 100
                
                # Determine pool status
                if pool_info['utilization'] > 90:
                    pool_info['status'] = 'critical'
                elif pool_info['utilization'] > 75:
                    pool_info['status'] = 'warning'
                else:
                    pool_info['status'] = 'healthy'
                
                engine_id = str(engine.url)
                self.pool_metrics[engine_id] = pool_info
                
        except Exception as e:
            logger.warning(f"Failed to update pool metrics: {e}")

    # PUBLIC API METHODS
    # ==================
    
    def get_query_stats(self, minutes: int = 10) -> Dict[str, Any]:
        """Get query performance statistics"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        
        with self.query_lock:
            recent_queries = [
                q for q in self.query_history 
                if q['timestamp'] >= cutoff_time
            ]
            
            if not recent_queries:
                return {
                    'time_window_minutes': minutes,
                    'status': 'no_data',
                    'total_queries': 0
                }
            
            # Calculate statistics
            durations = [q['duration_ms'] for q in recent_queries]
            successful_queries = [q for q in recent_queries if q['success']]
            failed_queries = [q for q in recent_queries if not q['success']]
            slow_queries = [q for q in recent_queries if q['duration_ms'] > 1000]
            
            durations.sort()
            total_count = len(recent_queries)
            
            stats = {
                'time_window_minutes': minutes,
                'status': 'ok',
                'query_counts': {
                    'total': total_count,
                    'successful': len(successful_queries),
                    'failed': len(failed_queries),
                    'slow': len(slow_queries),
                    'success_rate': (len(successful_queries) / total_count) * 100 if total_count > 0 else 0
                },
                'performance': {
                    'avg_duration_ms': sum(durations) / len(durations) if durations else 0,
                    'min_duration_ms': min(durations) if durations else 0,
                    'max_duration_ms': max(durations) if durations else 0,
                    'p50_duration_ms': durations[len(durations) // 2] if durations else 0,
                    'p95_duration_ms': durations[int(len(durations) * 0.95)] if durations else 0,
                    'p99_duration_ms': durations[int(len(durations) * 0.99)] if durations else 0
                },
                'throughput': {
                    'queries_per_minute': total_count / minutes,
                    'queries_per_second': total_count / (minutes * 60)
                }
            }
            
            return stats

    def get_slow_queries(self, minutes: int = 10, threshold_ms: float = 1000) -> List[Dict[str, Any]]:
        """Get slow queries that exceeded duration threshold"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        
        with self.query_lock:
            slow_queries = [
                {
                    'timestamp': MonitoringUtils.format_timestamp(q['timestamp']),
                    'statement': q['statement'],
                    'duration_ms': q['duration_ms'],
                    'success': q['success'],
                    'error': q.get('error')
                }
                for q in self.query_history 
                if (q['timestamp'] >= cutoff_time and 
                    q['duration_ms'] > threshold_ms)
            ]
            
            # Sort by duration (slowest first)
            slow_queries.sort(key=lambda x: x['duration_ms'], reverse=True)
            
            return slow_queries

    def get_failed_queries(self, minutes: int = 10) -> List[Dict[str, Any]]:
        """Get failed queries"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        
        with self.query_lock:
            failed_queries = [
                {
                    'timestamp': MonitoringUtils.format_timestamp(q['timestamp']),
                    'statement': q['statement'],
                    'duration_ms': q['duration_ms'],
                    'error': q.get('error', 'Unknown error')
                }
                for q in self.query_history 
                if (q['timestamp'] >= cutoff_time and not q['success'])
            ]
            
            # Sort by timestamp (most recent first)
            failed_queries.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return failed_queries

    def get_pool_status(self) -> Dict[str, Any]:
        """Get current connection pool status for all tracked engines"""
        with self.pool_lock:
            return dict(self.pool_metrics)  # Return copy

    def get_database_summary(self) -> Dict[str, Any]:
        """Get comprehensive database metrics summary"""
        try:
            query_stats = self.get_query_stats(minutes=10)
            pool_status = self.get_pool_status()
            slow_queries = self.get_slow_queries(minutes=10, threshold_ms=1000)
            failed_queries = self.get_failed_queries(minutes=10)
            
            # Overall database health assessment
            overall_status = 'healthy'
            
            # Check query performance
            if query_stats.get('status') == 'ok':
                query_counts = query_stats.get('query_counts', {})
                success_rate = query_counts.get('success_rate', 100)
                avg_duration = query_stats.get('performance', {}).get('avg_duration_ms', 0)
                
                if success_rate < 95 or avg_duration > 500:
                    overall_status = 'warning'
                if success_rate < 90 or avg_duration > 1000:
                    overall_status = 'critical'
            
            # Check pool health
            for engine_id, pool_info in pool_status.items():
                pool_util = pool_info.get('utilization', 0)
                if pool_util > 90:
                    overall_status = 'critical'
                elif pool_util > 75 and overall_status == 'healthy':
                    overall_status = 'warning'
            
            return {
                'timestamp': MonitoringUtils.format_timestamp(),
                'overall_status': overall_status,
                'query_performance': query_stats,
                'connection_pools': pool_status,
                'issues': {
                    'slow_queries_count': len(slow_queries),
                    'failed_queries_count': len(failed_queries),
                    'slow_queries': slow_queries[:5],  # Top 5 slowest
                    'failed_queries': failed_queries[:5]  # Most recent 5
                },
                'lifetime_stats': {
                    'total_queries': self.total_queries,
                    'slow_queries': self.slow_queries,
                    'failed_queries': self.failed_queries,
                    'success_rate': ((self.total_queries - self.failed_queries) / self.total_queries * 100) if self.total_queries > 0 else 100
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating database summary: {e}")
            return {
                'timestamp': MonitoringUtils.format_timestamp(),
                'overall_status': 'error',
                'error': str(e)
            }

    def clear_metrics(self) -> None:
        """Clear all metrics (use with caution)"""
        with self.query_lock:
            self.query_history.clear()
            self.total_queries = 0
            self.slow_queries = 0
            self.failed_queries = 0
        
        with self.pool_lock:
            self.pool_metrics.clear()
        
        logger.info("All database metrics cleared")
    
    def cleanup(self) -> None:
        """Cleanup database metrics and event listeners"""
        try:
            # Clear tracked engines
            for engine_url in list(self.engines_tracked):
                logger.debug(f"Cleaned up monitoring for engine: {engine_url}")
            self.engines_tracked.clear()
            
            # Clear all metrics
            self.clear_metrics()
            
            logger.info("DatabaseMetrics cleanup completed successfully")
            
        except Exception as e:
            logger.error(f"Error during DatabaseMetrics cleanup: {e}")
