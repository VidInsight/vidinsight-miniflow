#!/usr/bin/env python3
"""
Test Queue System

In-memory queue implementation for testing:
- Input queue: Tasks waiting to be executed
- Output queue: Completed task results
- Thread-safe operations
- Queue monitoring capabilities
"""

import threading
import time
from typing import Dict, Any, List, Optional
from queue import Queue, Empty
from datetime import datetime


class TestQueueSystem:
    """
    In-memory queue system for test execution
    
    Bu sistem test amaçlı olarak:
    - Input ve output queue'ları yönetir
    - Thread-safe operations sağlar
    - Queue monitoring ve statistics tutar
    - Real queue system'i simüle eder
    """
    
    def __init__(self):
        """Initialize queue system"""
        self.input_queue = Queue()
        self.output_queue = Queue()
        self.processing_queue = Queue()  # Currently being processed
        
        # Statistics
        self.stats = {
            "total_sent": 0,
            "total_received": 0,
            "total_processed": 0,
            "start_time": datetime.now(),
            "last_activity": datetime.now()
        }
        
        # Thread safety
        self.lock = threading.Lock()
        
        # Queue monitoring
        self.is_monitoring = False
        self.monitor_thread = None
    
    def send_to_input_queue(self, task_payload: Dict[str, Any]) -> bool:
        """
        Task'ı input queue'ya gönder
        
        Args:
            task_payload: Task bilgileri
            
        Returns:
            Success status
        """
        try:
            with self.lock:
                # Task'a timestamp ekle
                task_payload['queued_at'] = datetime.now().isoformat()
                task_payload['queue_id'] = f"q_{int(time.time() * 1000)}"
                
                # Queue'ya ekle
                self.input_queue.put(task_payload)
                
                # Statistics güncelle
                self.stats["total_sent"] += 1
                self.stats["last_activity"] = datetime.now()
                
                print(f"📤 Queue: Task {task_payload.get('node_id', 'unknown')} sent to input queue")
                return True
                
        except Exception as e:
            print(f"❌ Queue: Error sending task to input queue: {e}")
            return False
    
    def get_from_input_queue(self, timeout: float = 1.0) -> Optional[Dict[str, Any]]:
        """
        Input queue'dan task al
        
        Args:
            timeout: Bekleme süresi (saniye)
            
        Returns:
            Task payload veya None
        """
        try:
            task_payload = self.input_queue.get(timeout=timeout)
            
            with self.lock:
                # Processing queue'ya taşı
                task_payload['processing_started_at'] = datetime.now().isoformat()
                self.processing_queue.put(task_payload)
                
                print(f"📥 Queue: Task {task_payload.get('node_id', 'unknown')} retrieved from input queue")
                return task_payload
                
        except Empty:
            return None
        except Exception as e:
            print(f"❌ Queue: Error getting task from input queue: {e}")
            return None
    
    def send_to_output_queue(self, result_payload: Dict[str, Any]) -> bool:
        """
        Result'ı output queue'ya gönder
        
        Args:
            result_payload: Task execution result
            
        Returns:
            Success status
        """
        try:
            with self.lock:
                # Result'a timestamp ekle
                result_payload['result_queued_at'] = datetime.now().isoformat()
                
                # Output queue'ya ekle
                self.output_queue.put(result_payload)
                
                # Statistics güncelle
                self.stats["total_processed"] += 1
                self.stats["last_activity"] = datetime.now()
                
                print(f"📤 Queue: Result for {result_payload.get('node_id', 'unknown')} sent to output queue")
                return True
                
        except Exception as e:
            print(f"❌ Queue: Error sending result to output queue: {e}")
            return False
    
    def get_from_output_queue(self, timeout: float = 1.0) -> List[Dict[str, Any]]:
        """
        Output queue'dan tamamlanan results'ları al
        
        Args:
            timeout: Bekleme süresi (saniye)
            
        Returns:
            Results listesi
        """
        results = []
        
        try:
            # Mevcut tüm results'ları al
            while True:
                try:
                    result = self.output_queue.get(timeout=0.1)  # Kısa timeout
                    results.append(result)
                    
                    with self.lock:
                        self.stats["total_received"] += 1
                        self.stats["last_activity"] = datetime.now()
                        
                except Empty:
                    break
            
            if results:
                print(f"📥 Queue: Retrieved {len(results)} results from output queue")
            
            return results
            
        except Exception as e:
            print(f"❌ Queue: Error getting results from output queue: {e}")
            return results
    
    def get_queue_sizes(self) -> Dict[str, int]:
        """Queue boyutlarını döner"""
        with self.lock:
            return {
                "input_queue": self.input_queue.qsize(),
                "output_queue": self.output_queue.qsize(),
                "processing_queue": self.processing_queue.qsize()
            }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Queue istatistiklerini döner"""
        with self.lock:
            uptime = datetime.now() - self.stats["start_time"]
            
            return {
                **self.stats,
                "uptime_seconds": uptime.total_seconds(),
                "queue_sizes": self.get_queue_sizes(),
                "throughput": {
                    "tasks_per_second": self.stats["total_processed"] / max(uptime.total_seconds(), 1),
                    "avg_processing_time": "simulated"
                }
            }
    
    def clear_all_queues(self):
        """Tüm queue'ları temizle"""
        with self.lock:
            # Queue'ları boşalt
            while not self.input_queue.empty():
                try:
                    self.input_queue.get_nowait()
                except Empty:
                    break
            
            while not self.output_queue.empty():
                try:
                    self.output_queue.get_nowait()
                except Empty:
                    break
            
            while not self.processing_queue.empty():
                try:
                    self.processing_queue.get_nowait()
                except Empty:
                    break
            
            print("🗑️ Queue: All queues cleared")
    
    def start_monitoring(self, interval: float = 5.0):
        """Queue monitoring başlat"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_queues,
            args=(interval,),
            daemon=True
        )
        self.monitor_thread.start()
        print(f"👁️ Queue: Monitoring started (interval: {interval}s)")
    
    def stop_monitoring(self):
        """Queue monitoring durdur"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        print("👁️ Queue: Monitoring stopped")
    
    def _monitor_queues(self, interval: float):
        """Queue monitoring loop"""
        while self.is_monitoring:
            try:
                sizes = self.get_queue_sizes()
                stats = self.get_statistics()
                
                print(f"📊 Queue Monitor: Input={sizes['input_queue']}, "
                      f"Processing={sizes['processing_queue']}, "
                      f"Output={sizes['output_queue']}, "
                      f"Processed={stats['total_processed']}")
                
                time.sleep(interval)
                
            except Exception as e:
                print(f"❌ Queue Monitor: Error: {e}")
                time.sleep(1)
    
    def is_empty(self) -> bool:
        """Tüm queue'lar boş mu kontrol et"""
        sizes = self.get_queue_sizes()
        return all(size == 0 for size in sizes.values())
    
    def wait_for_completion(self, timeout: float = 30.0) -> bool:
        """
        Tüm queue'ların boşalmasını bekle
        
        Args:
            timeout: Maksimum bekleme süresi
            
        Returns:
            Completion status
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.is_empty():
                print("✅ Queue: All queues are empty - processing completed")
                return True
            
            time.sleep(0.5)
        
        print(f"⏰ Queue: Timeout after {timeout}s - queues not empty")
        return False 