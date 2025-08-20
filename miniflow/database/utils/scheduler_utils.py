"""
Dynamic Value Processor Module

Bu modül JSON sözlüklerindeki farklı değer tiplerini işler:
1. Dynamic value (via name): {{ node_name.node_variable}}
2. Dynamic value (via id): {{node_id.node_variable}} (id ND ile başlar)
3. Environment value: {${variable_name}}
4. Static value: sayısal değerler
"""

import re
import os
import json
import time
import functools
from typing import Dict, Any, Optional, List, Callable


# ==================================================================================== PERFORMANCE MONITORING ==

class PerformanceMonitor:
    """Database operation performance monitoring utility"""
    
    def __init__(self):
        self.metrics = {
            'query_times': [],
            'operation_counts': {},
            'slow_queries': [],
            'total_operations': 0
        }
    
    def record_query_time(self, operation: str, duration: float):
        """Record query execution time"""
        self.metrics['query_times'].append({
            'operation': operation,
            'duration': duration,
            'timestamp': time.time()
        })
        
        # Track slow queries (>100ms)
        if duration > 0.1:
            self.metrics['slow_queries'].append({
                'operation': operation,
                'duration': duration,
                'timestamp': time.time()
            })
    
    def record_operation(self, operation: str):
        """Record operation count"""
        self.metrics['operation_counts'][operation] = self.metrics['operation_counts'].get(operation, 0) + 1
        self.metrics['total_operations'] += 1
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        if not self.metrics['query_times']:
            return {'status': 'no_data'}
        
        durations = [q['duration'] for q in self.metrics['query_times']]
        return {
            'total_operations': self.metrics['total_operations'],
            'operation_counts': self.metrics['operation_counts'],
            'avg_query_time': sum(durations) / len(durations),
            'max_query_time': max(durations),
            'min_query_time': min(durations),
            'slow_query_count': len(self.metrics['slow_queries']),
            'recent_slow_queries': self.metrics['slow_queries'][-10:]  # Last 10 slow queries
        }
    
    def reset_metrics(self):
        """Reset all metrics"""
        self.metrics = {
            'query_times': [],
            'operation_counts': {},
            'slow_queries': [],
            'total_operations': 0
        }


# Global performance monitor instance
_performance_monitor = PerformanceMonitor()


def monitor_performance(operation_name: str = None):
    """Decorator to monitor function performance"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                _performance_monitor.record_query_time(op_name, duration)
                _performance_monitor.record_operation(op_name)
                return result
            except Exception as e:
                duration = time.time() - start_time
                _performance_monitor.record_query_time(f"{op_name}_error", duration)
                raise
        
        return wrapper
    return decorator


def get_performance_metrics() -> Dict[str, Any]:
    """Get current performance metrics"""
    return _performance_monitor.get_performance_summary()


def reset_performance_metrics():
    """Reset performance metrics"""
    _performance_monitor.reset_metrics()


# ==================================================================================== DYNAMIC VALUE PROCESSING ==

# Pattern tanımlamaları
DYNAMIC_NAME_PATTERN = r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}'
DYNAMIC_ID_PATTERN = r'\{\{\s*(ND[a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}'
ENV_PATTERN = r'\{\$\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}'


def match_pattern(pattern: str, value: str) -> Optional[str]:
    """Verilen pattern ile value'yu kontrol eder"""
    if not isinstance(value, str):
        return None
    
    match = re.match(pattern, value.strip())
    return match.group(1) if match else None


def is_dynamic_name(value: str) -> bool:
    """Dynamic name pattern kontrolü"""
    return match_pattern(DYNAMIC_NAME_PATTERN, value) is not None


def is_dynamic_id(value: str) -> bool:
    """Dynamic ID pattern kontrolü"""
    return match_pattern(DYNAMIC_ID_PATTERN, value) is not None


def is_environment(value: str) -> bool:
    """Environment variable pattern kontrolü"""
    return match_pattern(ENV_PATTERN, value) is not None


def is_static(value: Any) -> bool:
    """Static value kontrolü"""
    return not isinstance(value, str) or (
        isinstance(value, str) and 
        not any([is_dynamic_name(value), is_dynamic_id(value), is_environment(value)])
    )


def extract_dynamic_name(value: str) -> Optional[tuple]:
    """Dynamic name'den node ve variable çıkarır"""
    matched = match_pattern(DYNAMIC_NAME_PATTERN, value)
    if matched:
        parts = matched.split('.')
        return (parts[0], parts[1]) if len(parts) == 2 else None
    return None


def extract_dynamic_id(value: str) -> Optional[tuple]:
    """Dynamic ID'den node ve variable çıkarır"""
    matched = match_pattern(DYNAMIC_ID_PATTERN, value)
    if matched:
        parts = matched.split('.')
        return (parts[0], parts[1]) if len(parts) == 2 else None
    return None


def extract_environment(value: str) -> Optional[str]:
    """Environment variable adını çıkarır"""
    return match_pattern(ENV_PATTERN, value)


def get_value_type(value: Any) -> str:
    """Değerin tipini belirler"""
    if not isinstance(value, str):
        return "static"
    
    if is_dynamic_id(value):
        return "dynamic_id"
    elif is_dynamic_name(value):
        return "dynamic_name"
    elif is_environment(value):
        return "environment"
    else:
        return "static"


@monitor_performance("categorize_variables")
def categorize_variables(data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Tüm değişkenleri kategorilere ayıran ana fonksiyon - Optimized version
    
    Returns:
        {
            "dynamic_variable_by_id": [{"dynamic_id": "ND123", "variable_name": "var_name", "target_variable": "output"}],
            "dynamic_variable_by_name": [{"node_name": "user", "variable_name": "var_name", "target_variable": "name"}],
            "environment_variables": [{"variable_name": "var_name", "env_variable": "API_KEY"}],
            "static_variables": [{"variable_name": "var_name", "value": "static_value"}]
        }
    """
    result = {
        "dynamic_variable_by_id": [],
        "dynamic_variable_by_name": [],
        "environment_variables": [],
        "static_variables": []
    }
    
    # Optimized: Single pass through data
    for var_name, value in data.items():
        value_type = get_value_type(value)
        
        if value_type == "dynamic_id":
            node_id, node_variable = extract_dynamic_id(value)
            if node_id and node_variable:
                result["dynamic_variable_by_id"].append({
                    "dynamic_id": node_id,
                    "variable_name": var_name,
                    "target_variable": node_variable
                })
        
        elif value_type == "dynamic_name":
            node_name, node_variable = extract_dynamic_name(value)
            if node_name and node_variable:
                result["dynamic_variable_by_name"].append({
                    "node_name": node_name,
                    "variable_name": var_name,
                    "target_variable": node_variable
                })
        
        elif value_type == "environment":
            env_var = extract_environment(value)
            if env_var:
                result["environment_variables"].append({
                    "variable_name": var_name,
                    "env_variable": env_var
                })
        
        else:  # static
            result["static_variables"].append({
                "variable_name": var_name,
                "value": value
            })
    
    return result


def main():
    """Test fonksiyonu"""
    test_data = {
        "var1": "{{ node_name.node_variable}}",
        "var2": "{{ND123.node_variable}}",
        "var3": "{${API_KEY}}",
        "var4": 10.0,
        "var5": "{{ user.name }}",
        "var6": "{{ND456.output}}",
        "var7": "{${DATABASE_URL}}",
        "var8": "normal_string",
        "var9": True
    }
    
    print("=== DYNAMIC VALUE PROCESSOR ===\n")
    
    print("=== KATEGORİZE EDİLMİŞ DEĞİŞKENLER ===")
    result = categorize_variables(test_data)
    print("Çıktı formatı:")
    for category, items in result.items():
        print(f"\n{category}:")
        for i, item in enumerate(items, 1):
            print(f"  {i:2d}. {item}")
    
    print("\n=== PERFORMANCE METRICS ===")
    metrics = get_performance_metrics()
    print(f"Performance Summary: {metrics}")


if __name__ == "__main__":
    main()