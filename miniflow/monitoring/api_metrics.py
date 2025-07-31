"""
API METRICS MIDDLEWARE
======================

FastAPI middleware for tracking request/response performance.
"""

import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)

class APIMetricsMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware to track API request/response metrics.
    """
    
    def __init__(self, 
                 app: ASGIApp,
                 performance_tracker=None,
                 track_request_body: bool = False,
                 track_response_body: bool = False):
        """
        Initialize API metrics middleware
        
        Args:
            app: FastAPI application
            performance_tracker: PerformanceTracker instance for recording metrics
            track_request_body: Whether to track request body size
            track_response_body: Whether to track response body size
        """
        super().__init__(app)
        self.performance_tracker = performance_tracker
        self.track_request_body = track_request_body
        self.track_response_body = track_response_body

    async def dispatch(self, request: Request, call_next):
        """Process request and track metrics"""
        start_time = time.time()
        
        # Extract request information
        method = request.method
        path = request.url.path
        operation = f"api_{method.lower()}_{path.replace('/', '_').strip('_')}"
        
        # Request metadata
        metadata = {
            "method": method,
            "path": path,
            "query_params": str(request.query_params) if request.query_params else None,
            "user_agent": request.headers.get("user-agent"),
            "content_type": request.headers.get("content-type"),
            "client_ip": self._get_client_ip(request)
        }
        
        # Track request body size if enabled
        if self.track_request_body:
            try:
                content_length = request.headers.get("content-length")
                if content_length:
                    metadata["request_body_size"] = int(content_length)
            except (ValueError, TypeError):
                pass
        
        # Process request
        response = None
        success = False
        error = None
        
        try:
            response = await call_next(request)
            success = 200 <= response.status_code < 400
            
            # Add response metadata
            metadata.update({
                "status_code": response.status_code,
                "response_size": self._get_response_size(response) if self.track_response_body else None
            })
            
            if not success:
                metadata["error_category"] = self._categorize_http_error(response.status_code)
            
        except Exception as e:
            error = str(e)
            metadata["error"] = error
            metadata["error_type"] = type(e).__name__
            logger.warning(f"API request failed: {method} {path} - {error}")
            
            # Re-raise the exception
            raise
        
        finally:
            # Calculate duration and record metrics
            duration_ms = (time.time() - start_time) * 1000
            
            # Record metrics if performance tracker available
            if self.performance_tracker:
                try:
                    self.performance_tracker.record_metric(
                        operation=operation,
                        duration_ms=duration_ms,
                        success=success,
                        metadata=metadata
                    )
                except Exception as tracker_error:
                    logger.warning(f"Failed to record API metrics: {tracker_error}")
            
            # Log slow requests
            if duration_ms > 1000:  # Log requests slower than 1 second
                logger.warning(
                    f"Slow API request: {method} {path} took {duration_ms:.1f}ms "
                    f"(status: {getattr(response, 'status_code', 'error')})"
                )
        
        return response

    def _get_client_ip(self, request: Request) -> Optional[str]:
        """Extract client IP address from request"""
        # Check common headers for real IP
        for header in ["x-forwarded-for", "x-real-ip", "x-client-ip"]:
            ip = request.headers.get(header)
            if ip:
                # Take first IP if multiple (x-forwarded-for can be comma-separated)
                return ip.split(",")[0].strip()
        
        # Fallback to direct client
        return getattr(request.client, "host", None) if request.client else None

    def _get_response_size(self, response: Response) -> Optional[int]:
        """Extract response body size"""
        try:
            content_length = response.headers.get("content-length")
            if content_length:
                return int(content_length)
        except (ValueError, TypeError):
            pass
        return None

    def _categorize_http_error(self, status_code: int) -> str:
        """Categorize HTTP error status codes"""
        if 400 <= status_code < 500:
            return "client_error"
        elif 500 <= status_code < 600:
            return "server_error"
        else:
            return "unknown_error"
    
    def cleanup(self) -> None:
        """Cleanup API metrics middleware resources"""
        # Nothing specific to cleanup for this middleware
        logger.info("APIMetricsMiddleware cleanup completed")

# Utility functions for API metrics
def get_api_metrics_summary(performance_tracker, minutes: int = 10) -> Dict[str, Any]:
    """
    Get API-specific metrics summary
    
    Args:
        performance_tracker: PerformanceTracker instance
        minutes: Time window in minutes
    
    Returns:
        Dictionary with API metrics summary
    """
    try:
        # Get all operations summary
        all_ops = performance_tracker.get_all_operations_summary(minutes=minutes)
        
        if all_ops.get('status') != 'ok':
            return {'status': 'no_data', 'time_window_minutes': minutes}
        
        # Filter API operations only
        api_operations = {}
        for operation, stats in all_ops.get('by_operation', {}).items():
            if operation.startswith('api_'):
                api_operations[operation] = stats
        
        if not api_operations:
            return {'status': 'no_api_data', 'time_window_minutes': minutes}
        
        # Calculate API-specific aggregates
        total_requests = sum(op['count'] for op in api_operations.values())
        total_successes = sum(op['success_count'] for op in api_operations.values())
        
        # Group by HTTP method
        method_stats = {}
        endpoint_stats = {}
        
        for operation, stats in api_operations.items():
            # Extract method and endpoint from operation name
            parts = operation.split('_')
            if len(parts) >= 2:
                method = parts[1].upper()
                endpoint = '_'.join(parts[2:]) if len(parts) > 2 else 'root'
                
                # Method aggregation
                if method not in method_stats:
                    method_stats[method] = {
                        'count': 0,
                        'success_count': 0,
                        'total_duration_ms': 0
                    }
                
                method_stats[method]['count'] += stats['count']
                method_stats[method]['success_count'] += stats['success_count']
                method_stats[method]['total_duration_ms'] += stats['avg_duration_ms'] * stats['count']
                
                # Endpoint aggregation
                endpoint_stats[endpoint] = stats
        
        # Calculate method averages
        for method, stats in method_stats.items():
            if stats['count'] > 0:
                stats['success_rate'] = (stats['success_count'] / stats['count']) * 100
                stats['avg_duration_ms'] = stats['total_duration_ms'] / stats['count']
            else:
                stats['success_rate'] = 0
                stats['avg_duration_ms'] = 0
        
        return {
            'status': 'ok',
            'time_window_minutes': minutes,
            'summary': {
                'total_requests': total_requests,
                'success_rate': (total_successes / total_requests) * 100 if total_requests > 0 else 0,
                'requests_per_minute': total_requests / minutes,
                'unique_endpoints': len(api_operations)
            },
            'by_method': method_stats,
            'by_endpoint': endpoint_stats,
            'top_endpoints': sorted(
                endpoint_stats.items(),
                key=lambda x: x[1]['count'],
                reverse=True
            )[:10]  # Top 10 by request count
        }
        
    except Exception as e:
        logger.error(f"Error generating API metrics summary: {e}")
        return {'status': 'error', 'error': str(e), 'time_window_minutes': minutes}

def get_slow_api_requests(performance_tracker, minutes: int = 10, threshold_ms: float = 1000) -> Dict[str, Any]:
    """Get slow API requests"""
    try:
        slow_operations = performance_tracker.get_slow_operations(
            threshold_ms=threshold_ms,
            minutes=minutes
        )
        
        # Filter API operations only
        slow_api_requests = [
            op for op in slow_operations
            if op.get('operation', '').startswith('api_')
        ]
        
        # Sort by duration (slowest first)
        slow_api_requests.sort(key=lambda x: x.get('duration_ms', 0), reverse=True)
        
        return {
            'time_window_minutes': minutes,
            'threshold_ms': threshold_ms,
            'slow_requests_count': len(slow_api_requests),
            'slow_requests': slow_api_requests
        }
        
    except Exception as e:
        logger.error(f"Error getting slow API requests: {e}")
        return {'status': 'error', 'error': str(e)}

def get_failed_api_requests(performance_tracker, minutes: int = 10) -> Dict[str, Any]:
    """Get failed API requests"""
    try:
        failed_operations = performance_tracker.get_error_operations(minutes=minutes)
        
        # Filter API operations only
        failed_api_requests = [
            op for op in failed_operations
            if op.get('operation', '').startswith('api_')
        ]
        
        # Group by error type/status code
        error_summary = {}
        for request in failed_api_requests:
            metadata = request.get('metadata', {})
            error_key = metadata.get('error_category', 'unknown_error')
            status_code = metadata.get('status_code', 'unknown')
            
            key = f"{error_key}_{status_code}"
            if key not in error_summary:
                error_summary[key] = {
                    'error_category': error_key,
                    'status_code': status_code,
                    'count': 0,
                    'endpoints': set()
                }
            
            error_summary[key]['count'] += 1
            error_summary[key]['endpoints'].add(metadata.get('path', 'unknown'))
        
        # Convert sets to lists for JSON serialization
        for error_info in error_summary.values():
            error_info['endpoints'] = list(error_info['endpoints'])
        
        return {
            'time_window_minutes': minutes,
            'failed_requests_count': len(failed_api_requests),
            'failed_requests': failed_api_requests,
            'error_summary': error_summary
        }
        
    except Exception as e:
        logger.error(f"Error getting failed API requests: {e}")
        return {'status': 'error', 'error': str(e)}