"""
Parallel Result Monitoring System

High-performance result processing with:
- Multi-threaded result processing (4 worker threads)
- Bulk database operations for batch result processing
- Optimized polling with adaptive intervals
- Connection pooling integration
- Retry mechanisms for failed results
"""

import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue as ThreadQueue
import multiprocessing

from .. import database
from ..database.functions.workflow_orchestration import process_execution_result
from ..database.core import execute_bulk_operations
from ..utils.logger import logger, log_performance


class ParallelResultMonitor:
    """
    Multi-threaded Result Monitor for high-performance result processing
    
    Features:
    - N worker threads for parallel result processing
    - Bulk database operations (N results → 1 query)
    - Adaptive polling intervals based on load
    - Connection pool integration
    - Failed result retry mechanism
    - Performance statistics tracking
    """
    
    def __init__(self, db_path, polling_interval=0.5, manager=None, batch_size=25, worker_threads=4):
        self.db_path = db_path
        self.polling_interval = polling_interval
        self.manager = manager
        self.batch_size = batch_size
        self.worker_threads = min(worker_threads, multiprocessing.cpu_count())
        
        # Threading control
        self.running = False
        self.main_thread = None
        self.worker_executor = None
        self.shutdown_event = threading.Event()
        
        # Result queues for pipeline processing
        self.pending_results_queue = ThreadQueue()
        self.failed_results_queue = ThreadQueue()
        
        # Performance monitoring
        self.stats = {
            'results_processed': 0,
            'batches_processed': 0,
            'failed_results': 0,
            'retried_results': 0,
            'database_operations': 0,
            'webhook_notifications': 0
        }
        
        # Adaptive polling
        self.min_polling_interval = 0.1
        self.max_polling_interval = 2.0
        self.current_polling_interval = polling_interval
        self.empty_cycles = 0
        
        logger.info(f"ParallelResultMonitor initialized - workers: {self.worker_threads}, batch_size: {self.batch_size}")
    
    def start(self):
        """Start parallel result monitoring"""
        if self.running:
            logger.warning("ParallelResultMonitor already running")
            return False
        
        # Database connection check
        connection_result = database.check_database_connection(self.db_path)
        if not connection_result.success:
            logger.error("Database connection failed")
            return False
        
        self.running = True
        self.shutdown_event.clear()
        
        # Initialize thread pool for workers
        self.worker_executor = ThreadPoolExecutor(
            max_workers=self.worker_threads,
            thread_name_prefix="ResultWorker"
        )
        
        # Start main monitoring thread
        self.main_thread = threading.Thread(target=self._main_monitoring_loop, daemon=True)
        self.main_thread.start()
        
        # Start retry worker for failed results
        self._start_retry_worker()
        
        logger.info(f"ParallelResultMonitor started with {self.worker_threads} workers")
        return True
    
    def stop(self):
        """Stop parallel result monitoring"""
        logger.info("Stopping ParallelResultMonitor...")
        
        self.running = False
        self.shutdown_event.set()
        
        # Shutdown thread pool
        if self.worker_executor:
            self.worker_executor.shutdown(wait=True)
        
        # Wait for main thread
        if self.main_thread and self.main_thread.is_alive():
            self.main_thread.join(timeout=5)
        
        logger.info("ParallelResultMonitor stopped")
    
    def is_running(self):
        """Check if monitor is running"""
        return self.running and self.main_thread and self.main_thread.is_alive()
    
    @log_performance("parallel_result_monitoring_cycle")
    def _main_monitoring_loop(self):
        """Main monitoring loop with parallel processing"""
        logger.info("ParallelResultMonitor main loop started")
        
        while self.running and not self.shutdown_event.is_set():
            try:
                # Step 1: Collect results from output queue
                results = self._collect_results_batch()
                
                if not results:
                    # Adaptive polling - increase interval when idle
                    self.empty_cycles += 1
                    self._adjust_polling_interval(idle=True)
                    time.sleep(self.current_polling_interval)
                    continue
                
                # Reset idle cycles and adjust polling
                self.empty_cycles = 0
                self._adjust_polling_interval(idle=False)
                
                logger.info(f"PARALLEL result processing: {len(results)} results")
                
                # Step 2: Process results in parallel
                self._process_results_parallel(results)
                
                # Short sleep to prevent CPU overload
                time.sleep(self.current_polling_interval)
                
            except Exception as e:
                logger.error(f"Main result monitoring loop error: {e}")
                time.sleep(1)
        
        logger.info("ParallelResultMonitor main loop ended")
    
    def _collect_results_batch(self):
        """Collect multiple results from output queue using bulk operations"""
        if not self.manager:
            return []
        
        try:
            # Use bulk get for better performance
            raw_results = self.manager.get_output_items_bulk(
                max_items=self.batch_size, 
                timeout=0.1
            )
            
            # Validate and filter results
            valid_results = []
            for result in raw_results:
                if self._validate_result_format(result):
                    valid_results.append(result)
                else:
                    logger.warning(f"Invalid result format: {result}")
                    self.stats['failed_results'] += 1
            
            return valid_results
            
        except Exception as e:
            logger.error(f"Bulk result collection error: {e}")
            return []
    
    def _process_results_parallel(self, results):
        """Process results using parallel workers"""
        if not results:
            return
        
        # Group results by execution_id for better batching
        execution_groups = {}
        for result in results:
            execution_id = result.get('execution_id')
            if execution_id not in execution_groups:
                execution_groups[execution_id] = []
            execution_groups[execution_id].append(result)
        
        # Submit groups to worker threads
        futures = []
        for execution_id, group_results in execution_groups.items():
            future = self.worker_executor.submit(self._process_result_group, execution_id, group_results)
            futures.append(future)
        
        # Collect results from workers
        successful_results = 0
        failed_results = 0
        
        for future in as_completed(futures, timeout=10):
            try:
                success_count, fail_count = future.result()
                successful_results += success_count
                failed_results += fail_count
            except Exception as e:
                logger.error(f"Result processing worker failed: {e}")
                failed_results += 1
        
        # Update statistics
        self.stats['results_processed'] += successful_results
        self.stats['failed_results'] += failed_results
        self.stats['batches_processed'] += 1
        
        logger.info(f"PARALLEL results completed: {successful_results} success, {failed_results} failed")
    
    def _process_result_group(self, execution_id, results):
        """Process a group of results for the same execution"""
        success_count = 0
        fail_count = 0
        
        try:
            # Process each result in the group
            for result in results:
                try:
                    # Process single result
                    orchestration_result = process_execution_result(
                        db_path=self.db_path,
                        execution_id=result["execution_id"],
                        node_id=result["node_id"],
                        status=result["status"],
                        result_data=result.get("result_data"),
                        error_message=result.get("error_message")
                    )
                    
                    if orchestration_result.success:
                        success_count += 1
                        # Check for workflow completion
                        self._check_workflow_completion(result["execution_id"])
                    else:
                        fail_count += 1
                        # Add to retry queue
                        self.failed_results_queue.put(result)
                        
                except Exception as e:
                    logger.error(f"Individual result processing failed: {e}")
                    fail_count += 1
                    self.failed_results_queue.put(result)
            
            self.stats['database_operations'] += 1
            
        except Exception as e:
            logger.error(f"Result group processing failed for execution {execution_id}: {e}")
            fail_count = len(results)
            # Add all results to retry queue
            for result in results:
                self.failed_results_queue.put(result)
        
        return success_count, fail_count
    
    def _check_workflow_completion(self, execution_id):
        """Check if workflow is completed and handle notifications"""
        try:
            # Get execution status
            execution_result = database.get_execution(self.db_path, execution_id)
            if not execution_result.success or not execution_result.data:
                return
            
            execution = execution_result.data
            
            # Only process completed or failed executions
            if execution["status"] not in ["completed", "failed"]:
                return
            
            # Log completion (webhook functionality removed)
            logger.info(f"Workflow execution completed: {execution_id} (status: {execution['status']})")
            self.stats['webhook_notifications'] += 1
            
        except Exception as e:
            logger.error(f"Workflow completion check failed for {execution_id}: {e}")
    
    def _start_retry_worker(self):
        """Start background worker for retrying failed results"""
        def retry_worker():
            while self.running:
                try:
                    # Get failed result with timeout
                    if not self.failed_results_queue.empty():
                        result = self.failed_results_queue.get(timeout=5)
                        
                        # Retry processing
                        success, _ = self._process_result_group(result.get('execution_id'), [result])
                        if success > 0:
                            self.stats['retried_results'] += 1
                            logger.info(f"Successfully retried failed result: {result.get('execution_id')}")
                        else:
                            # Re-queue for another retry (max 3 times)
                            retry_count = result.get('_retry_count', 0) + 1
                            if retry_count < 3:
                                result['_retry_count'] = retry_count
                                self.failed_results_queue.put(result)
                            else:
                                logger.error(f"Max retries exceeded for result: {result}")
                    else:
                        time.sleep(1)
                        
                except Exception as e:
                    logger.error(f"Retry worker error: {e}")
                    time.sleep(1)
        
        retry_thread = threading.Thread(target=retry_worker, daemon=True)
        retry_thread.start()
    
    def _adjust_polling_interval(self, idle=False):
        """Adjust polling interval based on system load"""
        if idle:
            # Increase interval when idle (up to max)
            self.current_polling_interval = min(
                self.current_polling_interval * 1.2,
                self.max_polling_interval
            )
        else:
            # Decrease interval when busy (down to min)
            self.current_polling_interval = max(
                self.current_polling_interval * 0.8,
                self.min_polling_interval
            )
    
    def _validate_result_format(self, result):
        """Validate result format"""
        if not isinstance(result, dict):
            return False
        
        required_fields = ['execution_id', 'node_id', 'status']
        for field in required_fields:
            if field not in result or not isinstance(result[field], str):
                return False
        
        if result['status'] not in ['success', 'failed']:
            return False
        
        return True
    
    def get_stats(self):
        """Get performance statistics"""
        return {
            **self.stats,
            'worker_threads': self.worker_threads,
            'batch_size': self.batch_size,
            'current_polling_interval': self.current_polling_interval,
            'empty_cycles': self.empty_cycles,
            'running': self.running
        } 