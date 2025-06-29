"""
Parallel Queue Monitoring System

This module provides multi-threaded queue monitoring to overcome
SQLite's single-connection bottleneck and achieve true parallelism.
"""

import time
import threading
import os
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue as ThreadQueue
import multiprocessing

from .. import database
from . import context_manager
from ..utils.logger import logger, log_performance
from ..database.functions.bulk_operations import bulk_get_nodes, bulk_resolve_contexts


class ParallelQueueMonitor:
    """
    Multi-threaded Queue Monitor for true parallel processing
    
    Features:
    - N worker threads for database operations
    - Connection pool per thread
    - Parallel task processing pipeline
    - Load balancing across workers
    - Non-blocking I/O operations
    """
    
    def __init__(self, db_path, polling_interval=0.1, manager=None, batch_size=50, worker_threads=4):
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
        
        # Task queues for pipeline processing
        self.ready_tasks_queue = ThreadQueue()
        self.prepared_payloads_queue = ThreadQueue()
        
        # Performance monitoring
        self.stats = {
            'tasks_processed': 0,
            'batches_processed': 0,
            'parallel_operations': 0,
            'database_operations': 0,
            'queue_operations': 0
        }
        
        # Scripts directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        miniflow_dir = os.path.dirname(current_dir)
        project_root = os.path.dirname(miniflow_dir)
        self.scripts_dir = os.path.join(project_root, 'scripts')
        
        logger.info(f"ParallelQueueMonitor initialized - workers: {self.worker_threads}, batch_size: {self.batch_size}")
    
    def start(self):
        """Start parallel queue monitoring"""
        if self.running:
            logger.warning("ParallelQueueMonitor already running")
            return False
        
        self.running = True
        self.shutdown_event.clear()
        
        # Initialize thread pool for workers
        self.worker_executor = ThreadPoolExecutor(
            max_workers=self.worker_threads,
            thread_name_prefix="QueueWorker"
        )
        
        # Start main monitoring thread
        self.main_thread = threading.Thread(target=self._main_monitoring_loop, daemon=True)
        self.main_thread.start()
        
        # Start pipeline worker threads
        self._start_pipeline_workers()
        
        logger.info(f"ParallelQueueMonitor started with {self.worker_threads} workers")
        return True
    
    def stop(self):
        """Stop parallel queue monitoring"""
        logger.info("Stopping ParallelQueueMonitor...")
        
        self.running = False
        self.shutdown_event.set()
        
        # Shutdown thread pool
        if self.worker_executor:
            self.worker_executor.shutdown(wait=True)
        
        # Wait for main thread
        if self.main_thread and self.main_thread.is_alive():
            self.main_thread.join(timeout=5)
        
        logger.info("ParallelQueueMonitor stopped")
    
    def is_running(self):
        """Check if monitor is running"""
        return self.running and self.main_thread and self.main_thread.is_alive()
    
    @log_performance("parallel_monitoring_cycle")
    def _main_monitoring_loop(self):
        """Main monitoring loop with parallel processing"""
        logger.info("ParallelQueueMonitor main loop started")
        
        while self.running and not self.shutdown_event.is_set():
            try:
                # Step 1: Get ready tasks in parallel
                futures = []
                for worker_id in range(self.worker_threads):
                    future = self.worker_executor.submit(self._get_ready_tasks_worker, worker_id)
                    futures.append(future)
                
                # Collect all ready tasks from workers
                all_ready_tasks = []
                for future in as_completed(futures, timeout=5):
                    try:
                        tasks = future.result()
                        if tasks:
                            all_ready_tasks.extend(tasks)
                    except Exception as e:
                        logger.error(f"Worker failed to get ready tasks: {e}")
                
                if not all_ready_tasks:
                    time.sleep(self.polling_interval)
                    continue
                
                logger.info(f"PARALLEL processing: {len(all_ready_tasks)} ready tasks")
                
                # Step 2: Process tasks in parallel batches
                self._process_tasks_parallel_pipeline(all_ready_tasks)
                
                # Short sleep to prevent CPU overload
                time.sleep(self.polling_interval)
                
            except Exception as e:
                logger.error(f"Main monitoring loop error: {e}")
                time.sleep(1)
        
        logger.info("ParallelQueueMonitor main loop ended")
    
    def _get_ready_tasks_worker(self, worker_id):
        """Worker function to get ready tasks"""
        try:
            # Get active executions first (same as legacy monitor)
            executions_result = database.list_executions(self.db_path)
            if not executions_result.success:
                return []
            
            active_executions = [
                exec_data for exec_data in executions_result.data
                if exec_data.get('status') in ['running', 'pending']
            ]
            
            if not active_executions:
                return []
            
            # Each worker processes a subset of executions
            worker_executions = active_executions[worker_id::self.worker_threads]
            
            all_ready_tasks = []
            limit_per_execution = max(1, (self.batch_size // self.worker_threads) // len(worker_executions)) if worker_executions else 1
            
            for execution in worker_executions:
                execution_id = execution['id']
                
                ready_result = database.get_ready_tasks_for_execution(
                    db_path=self.db_path,
                    execution_id=execution_id,
                    limit=limit_per_execution
                )
                
                if ready_result.success:
                    ready_tasks = ready_result.data.get('ready_tasks', [])
                    all_ready_tasks.extend(ready_tasks)
            
            self.stats['database_operations'] += 1
            logger.debug(f"Worker {worker_id} found {len(all_ready_tasks)} ready tasks from {len(worker_executions)} executions")
            return all_ready_tasks
            
        except Exception as e:
            logger.error(f"Worker {worker_id} failed to get ready tasks: {e}")
            return []
    
    def _process_tasks_parallel_pipeline(self, tasks):
        """Process tasks using parallel pipeline"""
        if not tasks:
            return
        
        # Step 1: Parallel batch marking
        task_ids = [task['id'] for task in tasks]
        batch_operations = [
            {
                'type': 'update',
                'query': 'UPDATE execution_queue SET status = ? WHERE id = ?',
                'params': ('running', task_id)
            }
            for task_id in task_ids
        ]
        
        # Execute bulk database operation
        bulk_result = database.execute_bulk_operations(self.db_path, batch_operations)
        if not bulk_result.success:
            logger.error(f"Bulk task marking failed: {bulk_result.error}")
            return
        
        self.stats['database_operations'] += 1
        logger.debug(f"Bulk marked {len(task_ids)} tasks as running")
        
        # Step 2: Parallel payload preparation
        payload_futures = []
        for task in tasks:
            future = self.worker_executor.submit(self._prepare_task_payload_optimized, task)
            payload_futures.append(future)
        
        # Collect prepared payloads
        prepared_payloads = []
        for future in as_completed(payload_futures, timeout=10):
            try:
                payload = future.result()
                if payload:
                    prepared_payloads.append(payload)
            except Exception as e:
                logger.error(f"Payload preparation failed: {e}")
        
        self.stats['parallel_operations'] += len(payload_futures)
        logger.debug(f"Prepared {len(prepared_payloads)}/{len(tasks)} payloads in parallel")
        
        # Step 3: Bulk queue send
        if prepared_payloads:
            success = self.manager.put_items_bulk(prepared_payloads)
            if success:
                # Step 4: Bulk task cleanup
                delete_operations = [
                    {
                        'type': 'delete',
                        'query': 'DELETE FROM execution_queue WHERE id = ?',
                        'params': (task_id,)
                    }
                    for task_id in task_ids
                ]
                
                delete_result = database.execute_bulk_operations(self.db_path, delete_operations)
                if delete_result.success:
                    self.stats['tasks_processed'] += len(prepared_payloads)
                    self.stats['batches_processed'] += 1
                    self.stats['queue_operations'] += 1
                    self.stats['database_operations'] += 1
                    
                    logger.info(f"PARALLEL PIPELINE completed: {len(prepared_payloads)} tasks processed")
                else:
                    logger.warning(f"Bulk delete failed: {delete_result.error}")
            else:
                logger.error("Bulk queue send failed")
    
    def _prepare_task_payload_optimized(self, task):
        """Optimized task payload preparation for parallel execution"""
        try:
            # Get node info (this will use connection pool)
            node_result = database.fetch_one(
                self.db_path,
                "SELECT id, workflow_id, name, type, script, params FROM nodes WHERE id = ?",
                (task['node_id'],)
            )
            
            if not node_result.success or not node_result.data:
                logger.error(f"Node not found for task {task['id']}")
                return None
            
            node_info = node_result.data
            
            # Parse parameters
            params_dict = database.safe_json_loads(node_info.get('params', '{}'))
            if isinstance(params_dict, str):
                try:
                    params_dict = json.loads(params_dict)
                except json.JSONDecodeError:
                    params_dict = {}
            
            # Create context (this can be optimized further with bulk operations)
            context = context_manager.create_context_for_task(
                params_dict,
                task['execution_id'],
                self.db_path
            )
            
            # Build payload
            task_payload = {
                "task_id": task['id'],
                "execution_id": task['execution_id'],
                "workflow_id": node_info['workflow_id'],
                "node_id": task['node_id'],
                "script_path": os.path.join(self.scripts_dir, node_info.get('script', '')),
                "context": context,
                "node_name": node_info['name'],
                "node_type": node_info['type']
            }
            
            return task_payload
            
        except Exception as e:
            logger.error(f"Payload preparation failed for task {task['id']}: {e}")
            return None
    
    def _start_pipeline_workers(self):
        """Start pipeline worker threads for continuous processing"""
        # These could be additional background workers for specific tasks
        # For now, we're using the main ThreadPoolExecutor
        pass
    
    def get_stats(self):
        """Get performance statistics"""
        return {
            **self.stats,
            'worker_threads': self.worker_threads,
            'batch_size': self.batch_size,
            'running': self.running
        } 