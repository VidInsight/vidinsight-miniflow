"""
SYSTEM METRICS COLLECTOR
=========================

Real-time collection of system and application metrics.
"""

import psutil
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import deque
import logging
from .base_monitoring import ThreadedMonitoringComponent, MonitoringUtils, create_metric_dict

logger = logging.getLogger(__name__)

class MetricsCollector(ThreadedMonitoringComponent):
    """
    Real-time system metrics collector with historical data retention.
    Collects CPU, memory, disk, network, and application-specific metrics.
    """
    
    def __init__(self, 
                 collection_interval: float = 1.0,
                 history_duration_minutes: int = 60,
                 enable_detailed_metrics: bool = True):
        """
        Initialize metrics collector
        
        Args:
            collection_interval: Seconds between metric collections
            history_duration_minutes: How long to keep historical data
            enable_detailed_metrics: Whether to collect detailed process metrics
        """
        super().__init__(
            history_duration_minutes=history_duration_minutes,
            component_name="MetricsCollector"
        )
        
        self.collection_interval = collection_interval
        self.enable_detailed_metrics = enable_detailed_metrics
        
        # Historical data storage (deque for memory efficiency)
        self.max_history_points = MonitoringUtils.calculate_history_points(
            history_duration_minutes, collection_interval
        )
        self.metrics_history: deque = deque(maxlen=self.max_history_points)
        
        # Collection control
        self.collecting = False
        self.collection_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Performance counters (additional to base class)
        self.collection_count = 0
        self.last_collection_time = None
        self.collection_errors = 0
        
        # Process reference for detailed metrics
        self.current_process = psutil.Process()
        
        # Network baseline (for delta calculations)
        self._last_network_io = None
        self._last_disk_io = None
        
        # Alert thresholds
        self.alert_thresholds = {}

    def start_collection(self) -> bool:
        """Start continuous metrics collection in background thread"""
        if self.collecting:
            logger.warning("Metrics collection already running")
            return False
        
        try:
            self.collecting = True
            self._stop_event.clear()
            self.collection_thread = threading.Thread(
                target=self._collection_loop,
                name="MetricsCollector",
                daemon=True
            )
            self.collection_thread.start()
            logger.info("Metrics collection started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start metrics collection: {e}")
            self.collecting = False
            return False

    def stop_collection(self) -> bool:
        """Stop metrics collection gracefully"""
        if not self.collecting:
            return True
        
        try:
            self._stop_event.set()
            self.collecting = False
            
            if self.collection_thread and self.collection_thread.is_alive():
                self.collection_thread.join(timeout=5.0)
            
            logger.info("Metrics collection stopped")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping metrics collection: {e}")
            return False

    def _collection_loop(self):
        """Main collection loop running in background thread"""
        logger.info("Metrics collection loop started")
        
        while not self._stop_event.is_set():
            try:
                start_time = time.time()
                
                # Collect metrics
                metrics = self._collect_current_metrics()
                
                # Store in history
                self.metrics_history.append(metrics)
                
                # Update counters
                self.collection_count += 1
                self.last_collection_time = datetime.utcnow()
                
                # Calculate collection time
                collection_duration = time.time() - start_time
                
                # Sleep for remainder of interval
                sleep_time = max(0, self.collection_interval - collection_duration)
                if sleep_time > 0:
                    self._stop_event.wait(sleep_time)
                else:
                    logger.warning(f"Metrics collection took {collection_duration:.3f}s - longer than interval {self.collection_interval}s")
                
            except Exception as e:
                self.collection_errors += 1
                logger.error(f"Error in metrics collection: {e}")
                self._stop_event.wait(1.0)  # Wait before retrying
        
        logger.info("Metrics collection loop ended")

    def _collect_current_metrics(self) -> Dict[str, Any]:
        """Collect current system and application metrics"""
        timestamp = datetime.utcnow()
        
        try:
            # System CPU metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else (0, 0, 0)
            
            # System Memory metrics
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Disk metrics
            disk_usage = psutil.disk_usage('/')
            disk_io = psutil.disk_io_counters()
            
            # Network metrics
            network_io = psutil.net_io_counters()
            
            # Process-specific metrics (current Miniflow process)
            process_memory = self.current_process.memory_info()
            process_cpu = self.current_process.cpu_percent()
            process_threads = self.current_process.num_threads()
            
            # Calculate deltas for I/O metrics
            disk_io_delta = self._calculate_io_delta(disk_io, self._last_disk_io, 'disk')
            network_io_delta = self._calculate_io_delta(network_io, self._last_network_io, 'network')
            
            # Store current values for next delta calculation
            self._last_disk_io = disk_io
            self._last_network_io = network_io
            
            metrics = {
                'timestamp': MonitoringUtils.format_timestamp(timestamp),
                'collection_duration_ms': 0,  # Will be updated after collection
                
                # System CPU
                'cpu': {
                    'percent': cpu_percent,
                    'count': cpu_count,
                    'frequency_mhz': cpu_freq.current if cpu_freq else 0,
                    'load_avg_1m': load_avg[0],
                    'load_avg_5m': load_avg[1],
                    'load_avg_15m': load_avg[2],
                    'status': self._get_cpu_status(cpu_percent)
                },
                
                # System Memory
                'memory': {
                    'total_gb': round(memory.total / (1024**3), 2),
                    'available_gb': round(memory.available / (1024**3), 2),
                    'used_gb': round(memory.used / (1024**3), 2),
                    'percent': memory.percent,
                    'swap_total_gb': round(swap.total / (1024**3), 2) if swap.total > 0 else 0,
                    'swap_used_gb': round(swap.used / (1024**3), 2) if swap.total > 0 else 0,
                    'swap_percent': swap.percent if swap.total > 0 else 0,
                    'status': self._get_memory_status(memory.percent)
                },
                
                # Disk I/O
                'disk': {
                    'total_gb': round(disk_usage.total / (1024**3), 2),
                    'used_gb': round(disk_usage.used / (1024**3), 2),
                    'free_gb': round(disk_usage.free / (1024**3), 2),
                    'percent': round((disk_usage.used / disk_usage.total) * 100, 1),
                    'read_bytes_delta': disk_io_delta.get('read_bytes', 0),
                    'write_bytes_delta': disk_io_delta.get('write_bytes', 0),
                    'read_ops_delta': disk_io_delta.get('read_count', 0),
                    'write_ops_delta': disk_io_delta.get('write_count', 0),
                    'status': self._get_disk_status(disk_usage.used / disk_usage.total)
                },
                
                # Network I/O
                'network': {
                    'bytes_sent_delta': network_io_delta.get('bytes_sent', 0),
                    'bytes_recv_delta': network_io_delta.get('bytes_recv', 0),
                    'packets_sent_delta': network_io_delta.get('packets_sent', 0),
                    'packets_recv_delta': network_io_delta.get('packets_recv', 0),
                    'errors_in': network_io.errin if network_io else 0,
                    'errors_out': network_io.errout if network_io else 0,
                    'drops_in': network_io.dropin if network_io else 0,
                    'drops_out': network_io.dropout if network_io else 0
                },
                
                # Process-specific (Miniflow)
                'process': {
                    'cpu_percent': process_cpu,
                    'memory_rss_mb': round(process_memory.rss / (1024**2), 2),
                    'memory_vms_mb': round(process_memory.vms / (1024**2), 2),
                    'threads': process_threads,
                    'status': self._get_process_status(process_cpu, process_memory.rss)
                }
            }
            
            # Add detailed metrics if enabled
            if self.enable_detailed_metrics:
                metrics.update(self._collect_detailed_metrics())
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            return {
                'timestamp': MonitoringUtils.format_timestamp(timestamp),
                'error': str(e),
                'status': 'error'
            }

    def _calculate_io_delta(self, current_io, last_io, io_type: str) -> Dict[str, int]:
        """Calculate I/O deltas between current and last measurements"""
        if not last_io or not current_io:
            return {}
        
        try:
            if io_type == 'disk':
                return {
                    'read_bytes': max(0, current_io.read_bytes - last_io.read_bytes),
                    'write_bytes': max(0, current_io.write_bytes - last_io.write_bytes),
                    'read_count': max(0, current_io.read_count - last_io.read_count),
                    'write_count': max(0, current_io.write_count - last_io.write_count)
                }
            elif io_type == 'network':
                return {
                    'bytes_sent': max(0, current_io.bytes_sent - last_io.bytes_sent),
                    'bytes_recv': max(0, current_io.bytes_recv - last_io.bytes_recv),
                    'packets_sent': max(0, current_io.packets_sent - last_io.packets_sent),
                    'packets_recv': max(0, current_io.packets_recv - last_io.packets_recv)
                }
        except Exception as e:
            logger.warning(f"Error calculating {io_type} delta: {e}")
        
        return {}

    def _collect_detailed_metrics(self) -> Dict[str, Any]:
        """Collect additional detailed metrics with enhanced process monitoring"""
        try:
            # File descriptors
            open_files = len(self.current_process.open_files())
            
            # Network connections
            connections = len(self.current_process.connections())
            
            # Child processes with detailed info
            children = self.current_process.children(recursive=True)
            child_processes = []
            total_child_memory = 0
            total_child_cpu = 0
            
            for child in children:
                try:
                    if child.is_running():
                        child_info = child.memory_info()
                        child_cpu = child.cpu_percent()
                        child_memory_mb = child_info.rss / (1024**2)
                        
                        child_processes.append({
                            'pid': child.pid,
                            'name': child.name(),
                            'status': child.status(),
                            'cpu_percent': child_cpu,
                            'memory_mb': round(child_memory_mb, 2),
                            'threads': child.num_threads(),
                            'create_time': child.create_time()
                        })
                        
                        total_child_memory += child_memory_mb
                        total_child_cpu += child_cpu
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            
            # System-wide process statistics
            system_processes = len(psutil.pids())
            
            # Enhanced network interface details
            network_interfaces = {}
            for interface, stats in psutil.net_io_counters(pernic=True).items():
                if stats.bytes_sent > 0 or stats.bytes_recv > 0:  # Active interfaces only
                    network_interfaces[interface] = {
                        'bytes_sent': stats.bytes_sent,
                        'bytes_recv': stats.bytes_recv,
                        'packets_sent': stats.packets_sent,
                        'packets_recv': stats.packets_recv,
                        'errors_in': stats.errin,
                        'errors_out': stats.errout,
                        'drops_in': stats.dropin,
                        'drops_out': stats.dropout
                    }
            
            # Enhanced disk per-partition details
            disk_partitions = {}
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disk_partitions[partition.device] = {
                        'mountpoint': partition.mountpoint,
                        'fstype': partition.fstype,
                        'total_gb': round(usage.total / (1024**3), 2),
                        'used_gb': round(usage.used / (1024**3), 2),
                        'free_gb': round(usage.free / (1024**3), 2),
                        'percent': round((usage.used / usage.total) * 100, 1)
                    }
                except PermissionError:
                    continue
            
            return {
                'detailed': {
                    'open_files': open_files,
                    'network_connections': connections,
                    'child_processes_count': len(child_processes),
                    'child_processes': child_processes[:5],  # Top 5 children
                    'total_child_memory_mb': round(total_child_memory, 2),
                    'total_child_cpu_percent': round(total_child_cpu, 2),
                    'system_processes_total': system_processes,
                    'process_create_time': self.current_process.create_time(),
                    'network_interfaces': network_interfaces,
                    'disk_partitions': disk_partitions
                }
            }
        except Exception as e:
            logger.warning(f"Error collecting detailed metrics: {e}")
            return {'detailed': {'status': 'error', 'error': str(e)}}

    def _get_cpu_status(self, cpu_percent: float) -> str:
        """Determine CPU status based on usage percentage"""
        if cpu_percent < 60:
            return 'healthy'
        elif cpu_percent < 85:
            return 'warning'
        else:
            return 'critical'

    def _get_memory_status(self, memory_percent: float) -> str:
        """Determine memory status based on usage percentage"""
        if memory_percent < 70:
            return 'healthy'
        elif memory_percent < 90:
            return 'warning'
        else:
            return 'critical'

    def _get_disk_status(self, disk_ratio: float) -> str:
        """Determine disk status based on usage ratio"""
        if disk_ratio < 0.8:
            return 'healthy'
        elif disk_ratio < 0.95:
            return 'warning'
        else:
            return 'critical'

    def _get_process_status(self, cpu_percent: float, memory_bytes: int) -> str:
        """Determine process status based on resource usage"""
        memory_mb = memory_bytes / (1024**2)
        
        if cpu_percent < 50 and memory_mb < 500:
            return 'healthy'
        elif cpu_percent < 80 and memory_mb < 1000:
            return 'warning'
        else:
            return 'critical'

    # PUBLIC API METHODS
    # ==================
    
    def get_current_metrics(self) -> Optional[Dict[str, Any]]:
        """Get the most recent metrics"""
        if not self.metrics_history:
            return None
        return dict(self.metrics_history[-1])  # Return copy

    def get_metrics_history(self, minutes: int = 10) -> List[Dict[str, Any]]:
        """Get metrics history for specified number of minutes"""
        if not self.metrics_history:
            return []
        
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        
        recent_metrics = []
        for metrics in reversed(self.metrics_history):
            try:
                timestamp = datetime.fromisoformat(metrics['timestamp'].replace('Z', '+00:00'))
                if timestamp >= cutoff_time:
                    recent_metrics.append(dict(metrics))  # Return copy
                else:
                    break
            except:
                continue
        
        return list(reversed(recent_metrics))

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get aggregated metrics summary"""
        if not self.metrics_history:
            return {'status': 'no_data'}
        
        try:
            current = self.get_current_metrics()
            history_5min = self.get_metrics_history(5)
            
            if not current or not history_5min:
                return {'status': 'insufficient_data'}
            
            # Calculate averages over last 5 minutes
            cpu_values = [m.get('cpu', {}).get('percent', 0) for m in history_5min]
            memory_values = [m.get('memory', {}).get('percent', 0) for m in history_5min]
            
            avg_cpu = sum(cpu_values) / len(cpu_values) if cpu_values else 0
            avg_memory = sum(memory_values) / len(memory_values) if memory_values else 0
            
            return {
                'status': 'healthy',
                'collection_stats': {
                    'total_collections': self.collection_count,
                    'errors': self.collection_errors,
                    'last_collection': MonitoringUtils.format_timestamp(self.last_collection_time) if self.last_collection_time else None,
                    'history_points': len(self.metrics_history),
                    'is_collecting': self.collecting
                },
                'current': current,
                'averages_5min': {
                    'cpu_percent': round(avg_cpu, 1),
                    'memory_percent': round(avg_memory, 1)
                },
                'trends': self._calculate_trends(history_5min)
            }
            
        except Exception as e:
            logger.error(f"Error generating metrics summary: {e}")
            return {'status': 'error', 'error': str(e)}

    def _calculate_trends(self, history: List[Dict[str, Any]]) -> Dict[str, str]:
        """Calculate trend directions for key metrics"""
        if len(history) < 3:
            return {'status': 'insufficient_data'}
        
        try:
            # Get first half and second half to compare trends
            mid_point = len(history) // 2
            first_half = history[:mid_point]
            second_half = history[mid_point:]
            
            # CPU trend
            cpu_first = sum(m.get('cpu', {}).get('percent', 0) for m in first_half) / len(first_half)
            cpu_second = sum(m.get('cpu', {}).get('percent', 0) for m in second_half) / len(second_half)
            
            # Memory trend  
            mem_first = sum(m.get('memory', {}).get('percent', 0) for m in first_half) / len(first_half)
            mem_second = sum(m.get('memory', {}).get('percent', 0) for m in second_half) / len(second_half)
            
            def get_trend(first_val, second_val, threshold=2.0):
                diff = second_val - first_val
                if abs(diff) < threshold:
                    return 'stable'
                return 'increasing' if diff > 0 else 'decreasing'
            
            return {
                'cpu': get_trend(cpu_first, cpu_second),
                'memory': get_trend(mem_first, mem_second)
            }
            
        except Exception as e:
            logger.warning(f"Error calculating trends: {e}")
            return {'status': 'error'}

    def is_collecting(self) -> bool:
        """Check if metrics collection is currently active"""
        return self.collecting and self.collection_thread and self.collection_thread.is_alive()
    
    def cleanup(self) -> None:
        """Cleanup metrics collector resources"""
        # Stop collection if running
        if self.is_collecting():
            self.stop_collection()
        
        # Clear historical data
        self.metrics_history.clear()
        
        # Reset counters
        self.collection_count = 0
        self.collection_errors = 0
        self.last_collection_time = None
        
        # Clear baselines
        self._last_network_io = None
        self._last_disk_io = None
        
        # Call base cleanup
        self._base_cleanup()
        
        logger.info("MetricsCollector cleanup completed")

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get metrics collection statistics"""
        return {
            'is_collecting': self.is_collecting(),
            'collection_count': self.collection_count,
            'collection_errors': self.collection_errors,
                            'last_collection_time': MonitoringUtils.format_timestamp(self.last_collection_time) if self.last_collection_time else None,
            'history_points': len(self.metrics_history),
            'max_history_points': self.max_history_points,
            'collection_interval': self.collection_interval,
            'history_duration_minutes': self.history_duration.total_seconds() / 60
        }
    
    # ENHANCED FEATURES
    # =================
    
    def set_alert_thresholds(self, 
                           cpu_warning: float = 80, 
                           cpu_critical: float = 95,
                           memory_warning: float = 85, 
                           memory_critical: float = 95,
                           disk_warning: float = 90, 
                           disk_critical: float = 98) -> None:
        """Set alerting thresholds for system metrics"""
        self.alert_thresholds = {
            'cpu': {'warning': cpu_warning, 'critical': cpu_critical},
            'memory': {'warning': memory_warning, 'critical': memory_critical},
            'disk': {'warning': disk_warning, 'critical': disk_critical}
        }
        logger.info(f"Alert thresholds updated: {self.alert_thresholds}")
    
    def check_alerts(self) -> Dict[str, Any]:
        """Check current metrics against alert thresholds"""
        if not hasattr(self, 'alert_thresholds'):
            return {'status': 'no_thresholds_set'}
        
        current = self.get_current_metrics()
        if not current:
            return {'status': 'no_metrics_available'}
        
        alerts = {
            'timestamp': MonitoringUtils.format_timestamp(),
            'alerts': [],
            'warnings': [],
            'status': 'healthy'
        }
        
        try:
            # Check CPU
            cpu_percent = current.get('cpu', {}).get('percent', 0)
            if cpu_percent >= self.alert_thresholds['cpu']['critical']:
                alerts['alerts'].append({
                    'type': 'cpu',
                    'level': 'critical',
                    'value': cpu_percent,
                    'threshold': self.alert_thresholds['cpu']['critical'],
                    'message': f"CPU usage critical: {cpu_percent:.1f}%"
                })
                alerts['status'] = 'critical'
            elif cpu_percent >= self.alert_thresholds['cpu']['warning']:
                alerts['warnings'].append({
                    'type': 'cpu',
                    'level': 'warning',
                    'value': cpu_percent,
                    'threshold': self.alert_thresholds['cpu']['warning'],
                    'message': f"CPU usage high: {cpu_percent:.1f}%"
                })
                if alerts['status'] == 'healthy':
                    alerts['status'] = 'warning'
            
            # Check Memory
            memory_percent = current.get('memory', {}).get('percent', 0)
            if memory_percent >= self.alert_thresholds['memory']['critical']:
                alerts['alerts'].append({
                    'type': 'memory',
                    'level': 'critical',
                    'value': memory_percent,
                    'threshold': self.alert_thresholds['memory']['critical'],
                    'message': f"Memory usage critical: {memory_percent:.1f}%"
                })
                alerts['status'] = 'critical'
            elif memory_percent >= self.alert_thresholds['memory']['warning']:
                alerts['warnings'].append({
                    'type': 'memory',
                    'level': 'warning',
                    'value': memory_percent,
                    'threshold': self.alert_thresholds['memory']['warning'],
                    'message': f"Memory usage high: {memory_percent:.1f}%"
                })
                if alerts['status'] == 'healthy':
                    alerts['status'] = 'warning'
            
            # Check Disk
            disk_percent = current.get('disk', {}).get('percent', 0)
            if disk_percent >= self.alert_thresholds['disk']['critical']:
                alerts['alerts'].append({
                    'type': 'disk',
                    'level': 'critical',
                    'value': disk_percent,
                    'threshold': self.alert_thresholds['disk']['critical'],
                    'message': f"Disk usage critical: {disk_percent:.1f}%"
                })
                alerts['status'] = 'critical'
            elif disk_percent >= self.alert_thresholds['disk']['warning']:
                alerts['warnings'].append({
                    'type': 'disk',
                    'level': 'warning',
                    'value': disk_percent,
                    'threshold': self.alert_thresholds['disk']['warning'],
                    'message': f"Disk usage high: {disk_percent:.1f}%"
                })
                if alerts['status'] == 'healthy':
                    alerts['status'] = 'warning'
            
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
            alerts['status'] = 'error'
            alerts['error'] = str(e)
        
        return alerts
    
    def get_aggregated_metrics(self, 
                             minutes: int = 60, 
                             aggregation_type: str = 'average') -> Dict[str, Any]:
        """Get aggregated metrics over specified time period"""
        if not self.metrics_history:
            return {'status': 'no_data'}
        
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        recent_metrics = []
        for m in self.metrics_history:
            try:
                # Handle both timezone-aware and naive timestamps
                timestamp_str = m['timestamp'].replace('Z', '+00:00')
                metric_time = datetime.fromisoformat(timestamp_str)
                
                # Convert to UTC if timezone-aware
                if metric_time.tzinfo is not None:
                    metric_time = metric_time.replace(tzinfo=None)
                
                if metric_time >= cutoff_time:
                    recent_metrics.append(m)
            except Exception as e:
                logger.warning(f"Error parsing timestamp {m.get('timestamp')}: {e}")
                continue
        
        if not recent_metrics:
            return {'status': 'no_recent_data'}
        
        try:
            # Extract numeric values
            cpu_values = [m.get('cpu', {}).get('percent', 0) for m in recent_metrics]
            memory_values = [m.get('memory', {}).get('percent', 0) for m in recent_metrics]
            disk_values = [m.get('disk', {}).get('percent', 0) for m in recent_metrics]
            
            # Network I/O
            network_sent = [m.get('network', {}).get('bytes_sent_delta', 0) for m in recent_metrics]
            network_recv = [m.get('network', {}).get('bytes_recv_delta', 0) for m in recent_metrics]
            
            # Process metrics
            process_cpu = [m.get('process', {}).get('cpu_percent', 0) for m in recent_metrics]
            process_memory = [m.get('process', {}).get('memory_rss_mb', 0) for m in recent_metrics]
            
            # Calculate aggregations
            if aggregation_type == 'average':
                aggregated = {
                    'cpu_percent': round(sum(cpu_values) / len(cpu_values), 2) if cpu_values else 0,
                    'memory_percent': round(sum(memory_values) / len(memory_values), 2) if memory_values else 0,
                    'disk_percent': round(sum(disk_values) / len(disk_values), 2) if disk_values else 0,
                    'network_sent_avg_bps': round(sum(network_sent) / len(network_sent), 2) if network_sent else 0,
                    'network_recv_avg_bps': round(sum(network_recv) / len(network_recv), 2) if network_recv else 0,
                    'process_cpu_percent': round(sum(process_cpu) / len(process_cpu), 2) if process_cpu else 0,
                    'process_memory_mb': round(sum(process_memory) / len(process_memory), 2) if process_memory else 0
                }
            elif aggregation_type == 'max':
                aggregated = {
                    'cpu_percent': max(cpu_values) if cpu_values else 0,
                    'memory_percent': max(memory_values) if memory_values else 0,
                    'disk_percent': max(disk_values) if disk_values else 0,
                    'network_sent_max_bps': max(network_sent) if network_sent else 0,
                    'network_recv_max_bps': max(network_recv) if network_recv else 0,
                    'process_cpu_percent': max(process_cpu) if process_cpu else 0,
                    'process_memory_mb': max(process_memory) if process_memory else 0
                }
            elif aggregation_type == 'min':
                aggregated = {
                    'cpu_percent': min(cpu_values) if cpu_values else 0,
                    'memory_percent': min(memory_values) if memory_values else 0,
                    'disk_percent': min(disk_values) if disk_values else 0,
                    'network_sent_min_bps': min(network_sent) if network_sent else 0,
                    'network_recv_min_bps': min(network_recv) if network_recv else 0,
                    'process_cpu_percent': min(process_cpu) if process_cpu else 0,
                    'process_memory_mb': min(process_memory) if process_memory else 0
                }
            else:
                return {'status': 'invalid_aggregation_type'}
            
            return {
                'status': 'success',
                'aggregation_type': aggregation_type,
                'time_period_minutes': minutes,
                'data_points': len(recent_metrics),
                'aggregated_metrics': aggregated,
                'timestamp': MonitoringUtils.format_timestamp()
            }
            
        except Exception as e:
            logger.error(f"Error calculating aggregated metrics: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def detect_bottlenecks(self, sensitivity: str = 'medium') -> Dict[str, Any]:
        """Detect system bottlenecks based on metrics patterns"""
        current = self.get_current_metrics()
        if not current:
            return {'status': 'no_metrics'}
        
        # Get recent metrics for trend analysis
        recent_metrics = self.get_metrics_history(minutes=10)
        if len(recent_metrics) < 5:
            return {'status': 'insufficient_history'}
        
        # Configure sensitivity thresholds
        thresholds = {
            'low': {'cpu': 70, 'memory': 80, 'disk': 85, 'io_high': 1000000},  # 1MB/s
            'medium': {'cpu': 60, 'memory': 70, 'disk': 80, 'io_high': 500000},  # 500KB/s
            'high': {'cpu': 50, 'memory': 60, 'disk': 75, 'io_high': 100000}   # 100KB/s
        }.get(sensitivity, {})
        
        bottlenecks = {
            'timestamp': MonitoringUtils.format_timestamp(),
            'sensitivity': sensitivity,
            'bottlenecks': [],
            'warnings': [],
            'overall_status': 'healthy'
        }
        
        try:
            # CPU bottleneck detection
            cpu_values = [m.get('cpu', {}).get('percent', 0) for m in recent_metrics]
            avg_cpu = sum(cpu_values) / len(cpu_values)
            max_cpu = max(cpu_values)
            
            if avg_cpu > thresholds['cpu'] or max_cpu > thresholds['cpu'] + 20:
                bottlenecks['bottlenecks'].append({
                    'type': 'cpu',
                    'severity': 'high' if max_cpu > thresholds['cpu'] + 20 else 'medium',
                    'description': f"High CPU usage detected - Avg: {avg_cpu:.1f}%, Max: {max_cpu:.1f}%",
                    'recommendation': "Consider optimizing CPU-intensive processes or scaling resources"
                })
                bottlenecks['overall_status'] = 'bottleneck_detected'
            
            # Memory bottleneck detection
            memory_values = [m.get('memory', {}).get('percent', 0) for m in recent_metrics]
            avg_memory = sum(memory_values) / len(memory_values)
            max_memory = max(memory_values)
            
            if avg_memory > thresholds['memory'] or max_memory > thresholds['memory'] + 15:
                bottlenecks['bottlenecks'].append({
                    'type': 'memory',
                    'severity': 'high' if max_memory > thresholds['memory'] + 15 else 'medium',
                    'description': f"High memory usage detected - Avg: {avg_memory:.1f}%, Max: {max_memory:.1f}%",
                    'recommendation': "Consider memory optimization or increasing available RAM"
                })
                bottlenecks['overall_status'] = 'bottleneck_detected'
            
            # Disk I/O bottleneck detection
            disk_read_values = [m.get('disk', {}).get('read_bytes_delta', 0) for m in recent_metrics]
            disk_write_values = [m.get('disk', {}).get('write_bytes_delta', 0) for m in recent_metrics]
            avg_disk_read = sum(disk_read_values) / len(disk_read_values)
            avg_disk_write = sum(disk_write_values) / len(disk_write_values)
            
            if avg_disk_read > thresholds['io_high'] or avg_disk_write > thresholds['io_high']:
                bottlenecks['bottlenecks'].append({
                    'type': 'disk_io',
                    'severity': 'medium',
                    'description': f"High disk I/O detected - Read: {avg_disk_read/1024:.1f}KB/s, Write: {avg_disk_write/1024:.1f}KB/s",
                    'recommendation': "Consider optimizing disk access patterns or using faster storage"
                })
                if bottlenecks['overall_status'] == 'healthy':
                    bottlenecks['overall_status'] = 'warning'
            
            # Network I/O bottleneck detection
            network_sent_values = [m.get('network', {}).get('bytes_sent_delta', 0) for m in recent_metrics]
            network_recv_values = [m.get('network', {}).get('bytes_recv_delta', 0) for m in recent_metrics]
            avg_net_sent = sum(network_sent_values) / len(network_sent_values)
            avg_net_recv = sum(network_recv_values) / len(network_recv_values)
            
            if avg_net_sent > thresholds['io_high'] or avg_net_recv > thresholds['io_high']:
                bottlenecks['warnings'].append({
                    'type': 'network_io',
                    'severity': 'low',
                    'description': f"High network I/O detected - Sent: {avg_net_sent/1024:.1f}KB/s, Recv: {avg_net_recv/1024:.1f}KB/s",
                    'recommendation': "Monitor network bandwidth and consider optimization"
                })
            
            # Process-specific bottleneck detection
            process_cpu_values = [m.get('process', {}).get('cpu_percent', 0) for m in recent_metrics]
            process_memory_values = [m.get('process', {}).get('memory_rss_mb', 0) for m in recent_metrics]
            avg_process_cpu = sum(process_cpu_values) / len(process_cpu_values)
            avg_process_memory = sum(process_memory_values) / len(process_memory_values)
            
            if avg_process_cpu > 50 or avg_process_memory > 1000:  # 1GB
                bottlenecks['warnings'].append({
                    'type': 'miniflow_process',
                    'severity': 'medium',
                    'description': f"Miniflow process resource usage - CPU: {avg_process_cpu:.1f}%, Memory: {avg_process_memory:.1f}MB",
                    'recommendation': "Monitor Miniflow process performance and consider optimization"
                })
            
        except Exception as e:
            logger.error(f"Error detecting bottlenecks: {e}")
            bottlenecks['status'] = 'error'
            bottlenecks['error'] = str(e)
        
        return bottlenecks