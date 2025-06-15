#!/usr/bin/env python3
"""
Test-Enabled Scheduler

Bu scheduler test engine ile entegre çalışır:
- Mock execution engine kullanır
- Test queue system ile çalışır
- Real scheduler'ı simüle eder
- End-to-end testing sağlar
"""

import time
import threading
from typing import Dict, Any, Optional

from .mock_engine import MockExecutionEngine
from .test_queue import TestQueueSystem
from ..scheduler.queue_monitoring import QueueMonitor
from ..scheduler.result_monitoring import ResultMonitor
from .. import database


class TestEnabledQueueMonitor(QueueMonitor):
    """
    Test-enabled queue monitor
    
    Normal QueueMonitor'u extend eder ve test queue system kullanır
    """
    
    def __init__(self, db_path: str, test_queue: TestQueueSystem, mock_engine: MockExecutionEngine, polling_interval: int = 2):
        super().__init__(db_path, polling_interval)
        self.test_queue = test_queue
        self.mock_engine = mock_engine
        self.execution_thread = None
    
    def send_to_input_queue(self, task_payload: Dict[str, Any]):
        """
        Task'ı test input queue'ya gönder
        
        Args:
            task_payload: Task bilgileri
        """
        # Task payload'ı test queue'ya gönder
        success = self.test_queue.send_to_input_queue(task_payload)
        
        if success:
            print(f"📤 Test Queue: Task {task_payload.get('node_id', 'unknown')} sent to input queue")
        else:
            print(f"❌ Test Queue: Failed to send task {task_payload.get('node_id', 'unknown')}")
    
    def start(self):
        """Monitoring ve execution thread'lerini başlat"""
        # Parent start
        result = super().start()
        
        if result:
            # Execution thread'ini de başlat
            self.start_execution_thread()
        
        return result
    
    def stop(self):
        """Monitoring ve execution thread'lerini durdur"""
        # Execution thread'ini durdur
        self.stop_execution_thread()
        
        # Parent stop
        super().stop()
    
    def start_execution_thread(self):
        """Task execution thread'ini başlat"""
        if self.execution_thread and self.execution_thread.is_alive():
            return
        
        self.execution_thread = threading.Thread(
            target=self._execution_loop,
            daemon=True
        )
        self.execution_thread.start()
        print("🔧 Test Execution: Thread started")
    
    def stop_execution_thread(self):
        """Task execution thread'ini durdur"""
        if self.execution_thread and self.execution_thread.is_alive():
            self.execution_thread.join(timeout=3)
        print("🔧 Test Execution: Thread stopped")
    
    def _execution_loop(self):
        """Task execution ana döngüsü"""
        while self.running:
            try:
                # Input queue'dan task al
                task_payload = self.test_queue.get_from_input_queue(timeout=1.0)
                
                if task_payload:
                    # Task'ı execute et
                    result = self.mock_engine.execute_task(task_payload)
                    
                    # Result'ı output queue'ya gönder
                    self.test_queue.send_to_output_queue(result)
                
                time.sleep(0.5)  # Kısa bekleme
                
            except Exception as e:
                print(f"❌ Test Execution: Error in execution loop: {e}")
                time.sleep(1)
    
    def process_task(self, task):
        """
        Task'ı işle - test queue'ya gönder
        
        Args:
            task: Database'den gelen task bilgisi
            
        Returns:
            İşlem başarı durumu
        """
        try:
            task_id = task['id']
            node_id = task['node_id']
            execution_id = task['execution_id']
            
            # Node bilgilerini al
            node_result = database.get_node(self.db_path, node_id)
            if not node_result.success:
                return False
            
            node_info = node_result.data
            
            # Context oluştur
            from ..scheduler import context_manager
            params_dict = database.safe_json_loads(node_info.get('params', '{}'))
            processed_context = context_manager.create_context_for_task(
                params_dict, execution_id, self.db_path
            )
            
            # Task payload hazırla
            task_payload = {
                "execution_id": execution_id,
                "workflow_id": node_info['workflow_id'],
                "node_id": node_id,
                "type": node_info['type'],
                "script": node_info.get('script', ''),
                "params": processed_context,
                "task_id": task_id
            }
            
            # Test queue'ya gönder
            self.send_to_input_queue(task_payload)
            
            # Task'ı database'den sil (normal flow)
            delete_result = database.delete_task(self.db_path, task_id)
            return delete_result.success
            
        except Exception as e:
            print(f"❌ Test Queue Monitor: Error processing task: {e}")
            return False


class TestEnabledResultMonitor(ResultMonitor):
    """
    Test-enabled result monitor
    
    Normal ResultMonitor'u extend eder ve test queue system kullanır
    """
    
    def __init__(self, db_path: str, test_queue: TestQueueSystem, polling_interval: int = 2):
        super().__init__(db_path, polling_interval)
        self.test_queue = test_queue
    
    def get_from_output_queue(self):
        """
        Test output queue'dan sonuçları al
        
        Returns:
            Results listesi
        """
        return self.test_queue.get_from_output_queue()


class TestScheduler:
    """
    Test Scheduler - Complete test environment
    
    Bu scheduler test amaçlı olarak:
    - Mock execution engine kullanır
    - Test queue system ile çalışır
    - Real scheduler behavior'ını simüle eder
    - End-to-end testing sağlar
    """
    
    def __init__(self, db_path: str, failure_rate: float = 0.0):
        """
        Args:
            db_path: Database path
            failure_rate: Mock engine failure rate (0.0-1.0)
        """
        self.db_path = db_path
        self.running = False
        
        # Test components
        self.test_queue = TestQueueSystem()
        self.mock_engine = MockExecutionEngine(failure_rate=failure_rate)
        
        # Test-enabled monitors
        self.queue_monitor = TestEnabledQueueMonitor(
            db_path=db_path,
            test_queue=self.test_queue,
            mock_engine=self.mock_engine,
            polling_interval=2
        )
        
        self.result_monitor = TestEnabledResultMonitor(
            db_path=db_path,
            test_queue=self.test_queue,
            polling_interval=2
        )
    
    def start(self) -> bool:
        """
        Test scheduler'ı başlat
        
        Returns:
            Başarı durumu
        """
        if self.running:
            return False
        
        try:
            # Database bağlantı kontrolü
            connection_result = database.check_database_connection(self.db_path)
            if not connection_result.success:
                print("❌ Test Scheduler: Database connection failed")
                return False
            
            # Queue monitoring başlat
            self.test_queue.start_monitoring(interval=3.0)
            
            # Monitors başlat
            queue_started = self.queue_monitor.start()
            if not queue_started:
                print("❌ Test Scheduler: Queue monitor failed to start")
                return False
            
            result_started = self.result_monitor.start()
            if not result_started:
                print("❌ Test Scheduler: Result monitor failed to start")
                self.queue_monitor.stop()
                return False
            
            self.running = True
            print("🚀 Test Scheduler: Started successfully")
            return True
            
        except Exception as e:
            print(f"❌ Test Scheduler: Start error: {e}")
            return False
    
    def stop(self):
        """Test scheduler'ı durdur"""
        if not self.running:
            return
        
        self.running = False
        
        try:
            # Monitors durdur
            self.result_monitor.stop()
            self.queue_monitor.stop()
            
            # Queue monitoring durdur
            self.test_queue.stop_monitoring()
            
            print("🛑 Test Scheduler: Stopped successfully")
            
        except Exception as e:
            print(f"❌ Test Scheduler: Stop error: {e}")
    
    def is_running(self) -> bool:
        """Scheduler durumunu kontrol et"""
        return (self.running and 
                self.queue_monitor.is_running() and 
                self.result_monitor.is_running())
    
    def get_status(self) -> Dict[str, Any]:
        """Detaylı scheduler durumu"""
        queue_stats = self.test_queue.get_statistics()
        engine_stats = self.mock_engine.get_execution_stats()
        
        return {
            "scheduler_running": self.running,
            "queue_monitor_running": self.queue_monitor.is_running(),
            "result_monitor_running": self.result_monitor.is_running(),
            "queue_statistics": queue_stats,
            "engine_statistics": engine_stats,
            "database_path": self.db_path
        }
    
    def wait_for_completion(self, timeout: float = 30.0) -> bool:
        """
        Tüm task'ların tamamlanmasını bekle
        
        Args:
            timeout: Maksimum bekleme süresi
            
        Returns:
            Completion status
        """
        return self.test_queue.wait_for_completion(timeout)
    
    def clear_queues(self):
        """Tüm queue'ları temizle"""
        self.test_queue.clear_all_queues()
    
    def get_queue_sizes(self) -> Dict[str, int]:
        """Queue boyutlarını döner"""
        return self.test_queue.get_queue_sizes()


def create_test_scheduler(db_path: str, failure_rate: float = 0.0) -> TestScheduler:
    """
    Test scheduler factory function
    
    Args:
        db_path: Database path
        failure_rate: Mock engine failure rate
        
    Returns:
        TestScheduler instance
    """
    return TestScheduler(db_path, failure_rate) 