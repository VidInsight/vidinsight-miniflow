"""
METRICS EXPORT MODULE
=====================

Provides metrics export functionality for external monitoring systems like Prometheus, Grafana, etc.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
from .base_monitoring import MonitoringUtils

logger = logging.getLogger(__name__)

class MetricsExporter:
    """
    Exports monitoring metrics to various external formats and systems
    """
    
    def __init__(self, monitoring_manager=None):
        """Initialize metrics exporter with monitoring manager"""
        self.monitoring_manager = monitoring_manager
    
    def export_prometheus_format(self) -> str:
        """Export metrics in Prometheus text format"""
        if not self.monitoring_manager:
            return "# No monitoring manager available\n"
        
        prometheus_metrics = []
        timestamp = int(datetime.utcnow().timestamp() * 1000)  # Prometheus uses milliseconds
        
        try:
            # Get current metrics
            system_metrics = self.monitoring_manager.get_system_metrics()
            performance_metrics = self.monitoring_manager.get_performance_metrics()
            database_metrics = self.monitoring_manager.get_database_metrics()
            
            # System metrics
            if system_metrics:
                prometheus_metrics.extend([
                    f"# HELP miniflow_cpu_percent System CPU usage percentage",
                    f"# TYPE miniflow_cpu_percent gauge",
                    f"miniflow_cpu_percent {{instance=\"miniflow\"}} {system_metrics.get('cpu', {}).get('percent', 0)} {timestamp}",
                    "",
                    f"# HELP miniflow_memory_percent System memory usage percentage", 
                    f"# TYPE miniflow_memory_percent gauge",
                    f"miniflow_memory_percent {{instance=\"miniflow\"}} {system_metrics.get('memory', {}).get('percent', 0)} {timestamp}",
                    "",
                    f"# HELP miniflow_disk_percent System disk usage percentage",
                    f"# TYPE miniflow_disk_percent gauge", 
                    f"miniflow_disk_percent {{instance=\"miniflow\"}} {system_metrics.get('disk', {}).get('percent', 0)} {timestamp}",
                    "",
                    f"# HELP miniflow_process_memory_mb Miniflow process memory usage in MB",
                    f"# TYPE miniflow_process_memory_mb gauge",
                    f"miniflow_process_memory_mb {{instance=\"miniflow\"}} {system_metrics.get('process', {}).get('memory_rss_mb', 0)} {timestamp}",
                    "",
                    f"# HELP miniflow_process_cpu_percent Miniflow process CPU usage percentage",
                    f"# TYPE miniflow_process_cpu_percent gauge",
                    f"miniflow_process_cpu_percent {{instance=\"miniflow\"}} {system_metrics.get('process', {}).get('cpu_percent', 0)} {timestamp}",
                    ""
                ])
                
                # Network metrics
                network = system_metrics.get('network', {})
                if network:
                    prometheus_metrics.extend([
                        f"# HELP miniflow_network_bytes_sent_total Total network bytes sent",
                        f"# TYPE miniflow_network_bytes_sent_total counter",
                        f"miniflow_network_bytes_sent_total {{instance=\"miniflow\"}} {network.get('bytes_sent_delta', 0)} {timestamp}",
                        "",
                        f"# HELP miniflow_network_bytes_recv_total Total network bytes received",
                        f"# TYPE miniflow_network_bytes_recv_total counter", 
                        f"miniflow_network_bytes_recv_total {{instance=\"miniflow\"}} {network.get('bytes_recv_delta', 0)} {timestamp}",
                        ""
                    ])
            
            # Performance metrics
            if performance_metrics:
                tracker_stats = performance_metrics.get('tracker_stats', {})
                if tracker_stats:
                    prometheus_metrics.extend([
                        f"# HELP miniflow_operations_total Total number of operations tracked",
                        f"# TYPE miniflow_operations_total counter",
                        f"miniflow_operations_total {{instance=\"miniflow\"}} {tracker_stats.get('total_operations_tracked', 0)} {timestamp}",
                        "",
                        f"# HELP miniflow_operations_failed_total Total number of failed operations",
                        f"# TYPE miniflow_operations_failed_total counter",
                        f"miniflow_operations_failed_total {{instance=\"miniflow\"}} {tracker_stats.get('failed_operations', 0)} {timestamp}",
                        "",
                        f"# HELP miniflow_success_rate Operation success rate percentage",
                        f"# TYPE miniflow_success_rate gauge",
                        f"miniflow_success_rate {{instance=\"miniflow\"}} {tracker_stats.get('success_rate', 100)} {timestamp}",
                        ""
                    ])
            
            # Database metrics  
            if database_metrics:
                db_summary = database_metrics.get('database_summary', {})
                if db_summary:
                    prometheus_metrics.extend([
                        f"# HELP miniflow_db_queries_total Total database queries",
                        f"# TYPE miniflow_db_queries_total counter", 
                        f"miniflow_db_queries_total {{instance=\"miniflow\"}} {db_summary.get('total_queries', 0)} {timestamp}",
                        "",
                        f"# HELP miniflow_db_slow_queries_total Total slow database queries",
                        f"# TYPE miniflow_db_slow_queries_total counter",
                        f"miniflow_db_slow_queries_total {{instance=\"miniflow\"}} {db_summary.get('slow_queries', 0)} {timestamp}",
                        "",
                        f"# HELP miniflow_db_failed_queries_total Total failed database queries", 
                        f"# TYPE miniflow_db_failed_queries_total counter",
                        f"miniflow_db_failed_queries_total {{instance=\"miniflow\"}} {db_summary.get('failed_queries', 0)} {timestamp}",
                        ""
                    ])
            
            return "\n".join(prometheus_metrics)
            
        except Exception as e:
            logger.error(f"Error exporting Prometheus metrics: {e}")
            return f"# Error exporting metrics: {e}\n"
    
    def export_json_format(self, include_detailed: bool = True) -> str:
        """Export metrics in JSON format"""
        if not self.monitoring_manager:
            return json.dumps({"error": "No monitoring manager available"})
        
        try:
            comprehensive_data = self.monitoring_manager.get_comprehensive_summary()
            
            # Add export metadata
            export_data = {
                "export_timestamp": MonitoringUtils.format_timestamp(),
                "export_format": "json",
                "miniflow_version": "1.0.0",  # Could be dynamic
                "metrics_data": comprehensive_data
            }
            
            if not include_detailed:
                # Remove detailed sections for lighter export
                if 'system_metrics' in export_data['metrics_data']:
                    system_metrics = export_data['metrics_data']['system_metrics']
                    if 'detailed' in system_metrics:
                        del system_metrics['detailed']
            
            return json.dumps(export_data, indent=2, default=str)
            
        except Exception as e:
            logger.error(f"Error exporting JSON metrics: {e}")
            return json.dumps({"error": str(e), "timestamp": MonitoringUtils.format_timestamp()})
    
    def export_grafana_dashboard_config(self) -> Dict[str, Any]:
        """Generate Grafana dashboard configuration for Miniflow metrics"""
        dashboard_config = {
            "dashboard": {
                "id": None,
                "title": "Miniflow Monitoring Dashboard",
                "tags": ["miniflow", "monitoring"],
                "timezone": "browser",
                "refresh": "5s",
                "time": {
                    "from": "now-1h",
                    "to": "now"
                },
                "panels": [
                    {
                        "id": 1,
                        "title": "System CPU Usage",
                        "type": "stat",
                        "targets": [
                            {
                                "expr": "miniflow_cpu_percent",
                                "legendFormat": "CPU %"
                            }
                        ],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "percent",
                                "min": 0,
                                "max": 100
                            }
                        },
                        "gridPos": {"h": 8, "w": 6, "x": 0, "y": 0}
                    },
                    {
                        "id": 2,
                        "title": "System Memory Usage",
                        "type": "stat",
                        "targets": [
                            {
                                "expr": "miniflow_memory_percent",
                                "legendFormat": "Memory %"
                            }
                        ],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "percent",
                                "min": 0,
                                "max": 100
                            }
                        },
                        "gridPos": {"h": 8, "w": 6, "x": 6, "y": 0}
                    },
                    {
                        "id": 3,
                        "title": "Miniflow Process Memory",
                        "type": "graph",
                        "targets": [
                            {
                                "expr": "miniflow_process_memory_mb",
                                "legendFormat": "Memory MB"
                            }
                        ],
                        "yAxes": [
                            {
                                "unit": "bytes",
                                "min": 0
                            }
                        ],
                        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0}
                    },
                    {
                        "id": 4,
                        "title": "Operations Success Rate",
                        "type": "stat",
                        "targets": [
                            {
                                "expr": "miniflow_success_rate",
                                "legendFormat": "Success Rate"
                            }
                        ],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "percent",
                                "min": 0,
                                "max": 100,
                                "thresholds": {
                                    "steps": [
                                        {"color": "red", "value": 0},
                                        {"color": "yellow", "value": 95},
                                        {"color": "green", "value": 99}
                                    ]
                                }
                            }
                        },
                        "gridPos": {"h": 8, "w": 6, "x": 0, "y": 8}
                    },
                    {
                        "id": 5,
                        "title": "Database Queries",
                        "type": "graph",
                        "targets": [
                            {
                                "expr": "rate(miniflow_db_queries_total[5m])",
                                "legendFormat": "Queries/sec"
                            },
                            {
                                "expr": "rate(miniflow_db_slow_queries_total[5m])",
                                "legendFormat": "Slow Queries/sec"
                            },
                            {
                                "expr": "rate(miniflow_db_failed_queries_total[5m])",
                                "legendFormat": "Failed Queries/sec"
                            }
                        ],
                        "yAxes": [
                            {
                                "unit": "reqps",
                                "min": 0
                            }
                        ],
                        "gridPos": {"h": 8, "w": 18, "x": 6, "y": 8}
                    },
                    {
                        "id": 6,
                        "title": "Network I/O",
                        "type": "graph",
                        "targets": [
                            {
                                "expr": "rate(miniflow_network_bytes_sent_total[5m])",
                                "legendFormat": "Bytes Sent/sec"
                            },
                            {
                                "expr": "rate(miniflow_network_bytes_recv_total[5m])",
                                "legendFormat": "Bytes Recv/sec"
                            }
                        ],
                        "yAxes": [
                            {
                                "unit": "binBps",
                                "min": 0
                            }
                        ],
                        "gridPos": {"h": 8, "w": 24, "x": 0, "y": 16}
                    }
                ]
            }
        }
        
        return dashboard_config
    
    def save_to_file(self, format_type: str, file_path: str, **kwargs) -> bool:
        """Save metrics to file in specified format"""
        try:
            if format_type.lower() == 'prometheus':
                content = self.export_prometheus_format()
            elif format_type.lower() == 'json':
                content = self.export_json_format(**kwargs)
            elif format_type.lower() == 'grafana':
                content = json.dumps(self.export_grafana_dashboard_config(), indent=2)
            else:
                raise ValueError(f"Unsupported format: {format_type}")
            
            # Ensure directory exists
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"Metrics exported to {file_path} in {format_type} format")
            return True
            
        except Exception as e:
            logger.error(f"Error saving metrics to file: {e}")
            return False
    
    def get_export_summary(self) -> Dict[str, Any]:
        """Get summary of available export options"""
        return {
            "supported_formats": [
                {
                    "name": "prometheus",
                    "description": "Prometheus text format for scraping",
                    "content_type": "text/plain",
                    "use_case": "Direct Prometheus scraping"
                },
                {
                    "name": "json", 
                    "description": "Comprehensive JSON format",
                    "content_type": "application/json",
                    "use_case": "API integration, data analysis"
                },
                {
                    "name": "grafana",
                    "description": "Grafana dashboard configuration",
                    "content_type": "application/json", 
                    "use_case": "Import dashboard to Grafana"
                }
            ],
            "export_capabilities": [
                "System metrics (CPU, Memory, Disk, Network)",
                "Process metrics (Miniflow process specific)",
                "Performance metrics (Operations, Success rate)",
                "Database metrics (Queries, Performance)",
                "Custom metrics (User-defined)",
                "Real-time data export",
                "Historical data export"
            ],
            "integration_examples": {
                "prometheus_scrape_config": """
# Add to prometheus.yml
- job_name: 'miniflow'
  static_configs:
    - targets: ['localhost:8000']
  metrics_path: '/metrics'
  scrape_interval: 15s
""",
                "grafana_import": "Import the dashboard JSON via Grafana UI -> Import Dashboard",
                "api_usage": "GET /api/monitoring/export?format=json"
            }
        }
    
    def cleanup(self) -> None:
        """Cleanup metrics exporter resources"""
        # Nothing specific to cleanup for this exporter
        self.monitoring_manager = None
        logger.info("MetricsExporter cleanup completed")

# Convenience functions
def export_metrics_prometheus(monitoring_manager) -> str:
    """Quick export to Prometheus format"""
    exporter = MetricsExporter(monitoring_manager)
    return exporter.export_prometheus_format()

def export_metrics_json(monitoring_manager, include_detailed: bool = True) -> str:
    """Quick export to JSON format"""
    exporter = MetricsExporter(monitoring_manager)
    return exporter.export_json_format(include_detailed=include_detailed)

def save_grafana_dashboard(monitoring_manager, file_path: str) -> bool:
    """Quick save Grafana dashboard configuration"""
    exporter = MetricsExporter(monitoring_manager)
    return exporter.save_to_file('grafana', file_path)