"""
Base Monitor Class for Miniflow Scheduler
========================================
Common functionality for Input and Output monitors
"""

from concurrent.futures import ThreadPoolExecutor
import multiprocessing
import threading
import logging
import time
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseMonitor(ABC):
    """Base class for Miniflow monitors with common thread and worker pool management"""
    
    def __init__(self, database_engine, database_orchestration, execution_engine,
                 polling_interval=0.1, batch_size=50, worker_threads=4, thread_name_prefix="Worker"):
        
        # Database Manager Components
        self.database_engine = database_engine
        self.database_orchestration = database_orchestration
        self.execution_engine = execution_engine
        
        # Monitor Parameters
        self.polling_interval = polling_interval
        self.batch_size = batch_size
        self.worker_count = min(worker_threads, multiprocessing.cpu_count())
        self.thread_name_prefix = thread_name_prefix
        
        # Thread Management
        self.running = False
        self.main_thread = None
        self.worker_pool = None
        self.shutdown_event = threading.Event()
        
        # Validation
        self._validate_dependencies()
    
    def _validate_dependencies(self):
        """Validate required dependencies are provided"""
        if not self.database_engine:
            raise ValueError("Database Engine gerekli")
        if not self.database_orchestration:
            raise ValueError("Database Orchestration gerekli")
        if not self.execution_engine:
            raise ValueError("Execution Engine gerekli")
    
    def is_running(self):
        """Check if monitor is currently running"""
        return self.running and self.main_thread and self.main_thread.is_alive()
    
    def start(self):
        """Start the monitor with worker pool and main thread"""
        if self.is_running():
            logger.warning(f"{self.__class__.__name__} zaten çalışıyor")
            return True
        
        self.running = True
        self.shutdown_event.clear()
        
        # Initialize thread pool
        logger.debug(f"Worker pool oluşturuluyor - max_workers: {self.worker_count}")
        self.worker_pool = ThreadPoolExecutor(
            max_workers=self.worker_count,
            thread_name_prefix=self.thread_name_prefix
        )
        
        # Start main monitoring thread
        logger.debug(f"{self.__class__.__name__} ana thread başlatılıyor")
        self.main_thread = threading.Thread(
            target=self._monitoring_loop,
            name=f"{self.__class__.__name__}Thread",
            daemon=True
        )
        self.main_thread.start()
        
        logger.info(f"{self.__class__.__name__} başarıyla başlatıldı")
        return True
    
    def stop(self):
        """Stop the monitor gracefully"""
        if not self.running:
            logger.debug(f"{self.__class__.__name__} zaten durdurulmuş")
            return True
        
        logger.info(f"{self.__class__.__name__} durduruluyor")
        self.running = False
        self.shutdown_event.set()
        
        # Shutdown worker pool
        if self.worker_pool:
            logger.debug("Worker pool kapatılıyor")
            self.worker_pool.shutdown(wait=True)
        
        # Wait for main thread
        if self.main_thread and self.main_thread.is_alive():
            logger.debug("Ana thread sonlandırılması bekleniyor")
            self.main_thread.join(timeout=5)
        
        logger.info(f"{self.__class__.__name__} başarıyla durduruldu")
        return True
    
    def _monitoring_loop(self):
        """Main monitoring loop - to be implemented by subclasses"""
        logger.info(f"{self.__class__.__name__} ana işlem döngüsü başlatıldı")
        
        while self.running and not self.shutdown_event.is_set():
            try:
                # Call subclass implementation
                self._process_cycle()
                time.sleep(self.polling_interval)
            except Exception as e:
                logger.error(f"{self.__class__.__name__} döngü hatası: {e}")
                time.sleep(1)
        
        logger.debug(f"{self.__class__.__name__} döngüsü sonlandırıldı")
    
    @abstractmethod
    def _process_cycle(self):
        """Process one cycle of monitoring - must be implemented by subclasses"""
        pass
    
    def _create_task_payload_with_session(self, task):
        """Helper method to create task payload with database session"""
        with self.database_engine.get_session_context() as session:
            return self.database_orchestration.create_task_payload(session, task)