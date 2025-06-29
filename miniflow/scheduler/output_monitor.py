import time
import threading
import multiprocessing
from queue import Queue as ThreadQueue
from concurrent.futures import ThreadPoolExecutor, as_completed

from .. import database
from ..database.core import execute_bulk_operations
from ..database.functions.workflow_orchestration import process_execution_result

# TODO: Logger setup eklenecek

class MiniflowOutputMonitor:
    def __init__(self, db_path, polling_interval=0.5, manager=None, batch_size=25, worker_threads=4):
        # Database Params
        self.db_path = db_path
        self.polling_interval = polling_interval

        # Engine Params
        self.manager = manager
        # TODO: Manager kontrolü eklenecek

        self.batch_size = batch_size
        self.worker_count = min(worker_threads, multiprocessing.cpu_count())
        

        # Sınıf Params
        self.running = False
        self.main_thread = None
        self.worker_pool = None
        self.shutdown_event = threading.Event() # TODO: Araştırılacak

        # TODO: Retry - Error Queue

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

    def is_running(self):
        """
        DESC:
        RETURNS:
        """
        return self.running and self.main_thread and self.main_thread.is_alive()
    
    def get_stats(self):
        """
        DESC:
        RETURNS:
        """
        return {
            **self.stats,
            'worker_threads': self.worker_count,
            'batch_size': self.batch_size,
            'current_polling_interval': self.current_polling_interval,
            'empty_cycles': self.empty_cycles,
            'running': self.running
        } 

    def start(self):
        """
        DESC:
        RETURNS:
        """
        if self.running:
            # TODO: Logger - warning
            return True

        # Database connection check
        connection_result = database.check_database_connection(self.db_path)
        if not connection_result.success:
            # TODO: Logger - error
            return False
        
        self.running = True
        self.shutdown_event.clear() 

        self.worker_pool = ThreadPoolExecutor(max_workers=self.worker_count, 
                                              thread_name_prefix="OutputWorker")

        self.main_thread = threading.Thread(target=self.__monitoring_loop, 
                                            name="OutputMonitorThread",
                                            daemon=True)
        self.main_thread.start()

        # TOODO: Logger - info
        return True
    
    def stop(self):
        """
        DESC:
        RETURNS:
        """
        if not self.running:
            # TODO: Logger - warning
            return True
        
        self.running = False
        self.shutdown_event.set()

        if self.worker_pool:
            self.worker_pool.shutdown(wait=True)

        if self.main_thread and self.main_thread.is_alive():
            self.main_thread.join(timeout=5)

        # TODO: Logger - info
        return True
    
    def __monitoring_loop(self):
        """
        DESC: Main monitoring loop for result collection
        RETURNS: None
        """
        print("[OUTPUT_MONITOR] Starting monitoring loop")
        while self.running and not self.shutdown_event.is_set():
            try:
                results = self.__collect_results()

                if not results:
                    self.empty_cycles += 1
                    self.__adjust_polling_interval(idle=True)
                    time.sleep(self.current_polling_interval)
                    continue

                self.empty_cycles = 0
                self.__adjust_polling_interval(idle=False)

                print(f"[OUTPUT_MONITOR] Got {len(results)} results to process")

                self.__process_results(results) # Sonuçların işlenmesi
                time.sleep(self.current_polling_interval)
            except Exception as e:  
                print(f"[OUTPUT_MONITOR] Error in monitoring loop: {e}")
                time.sleep(1)

        print("[OUTPUT_MONITOR] Monitoring loop ended")


    def __collect_results(self):
        """
        DESC: Collect results from parallelism engine
        RETURNS: List of valid results
        """
        if not self.manager:
            print("[OUTPUT_MONITOR] ERROR: Manager is not set")
            raise ValueError("Manager is not set. Cannot collect results.")
        
        # 1. Manager üzerindne çıktı öğelerini topla
        raw_results = self.manager.get_output_items_bulk(
                max_items=self.batch_size, 
                timeout=0.1
            )
        
        print(f"[OUTPUT_MONITOR] Collected {len(raw_results)} raw results from manager")

        valid_results = []
        for result in raw_results:
            if self.__validate_result_format(result):
                valid_results.append(result)
                print(f"[OUTPUT_MONITOR] Valid result for node: {result.get('node_id', 'unknown')}")
            else:
                print(f"[OUTPUT_MONITOR] Invalid result format: {result}")
                self.stats['failed_results'] += 1   

        print(f"[OUTPUT_MONITOR] Validated {len(valid_results)} results")
        return valid_results

    def __validate_result_format(self, result):
        """
        DESC: Validate result format from parallelism engine
        RETURNS: bool
        """
        if not isinstance(result, dict):
            print(f"[OUTPUT_MONITOR] Result is not dict: {type(result)}")
            return False
        
        required_fields = ['execution_id', 'node_id', 'status']
        for field in required_fields:
            if field not in result:
                print(f"[OUTPUT_MONITOR] Missing required field: {field}")
                return False
            
        if result['status'] not in ['success', 'failed']:
            print(f"[OUTPUT_MONITOR] Invalid status: {result['status']}")
            return False
        
        # Accept either 'results' or 'result_data' field
        if 'results' not in result and 'result_data' not in result:
            print(f"[OUTPUT_MONITOR] Missing result data (neither 'results' nor 'result_data')")
            return False
        
        return True

        # TODO: Valid olmayan sonuçlar için çözüm
    
    def __adjust_polling_interval(self, idle=False):
        """
        DESC:
        RETURNS:
        """
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

    def __process_results(self, results):
        """
        DESC:
        RETURNS:
        """
        if not results:
            return
        
        execution_groups = {}
        for result in results:
            execution_id = result.get('execution_id')
            if execution_id not in execution_groups:
                execution_groups[execution_id] = []
            execution_groups[execution_id].append(result)

        futures = []
        for execution_id, group_result in execution_groups.items():
            future = self.worker_pool.submit(
                self.__process_execution_group, 
                group_result
            )
            futures.append(future)

        successful_results = 0
        failed_results = 0

        for future in as_completed(futures):
            try:
                success_count, fail_count = future.result()
                successful_results += success_count
                failed_results += fail_count
            except Exception as e:
                print(f"[OUTPUT_MONITOR] Exception in future processing: {e}")
                failed_results += 1

        # Update statistics
        self.stats['results_processed'] += successful_results
        self.stats['failed_results'] += failed_results
        self.stats['batches_processed'] += 1

        # TODO: Logger - info
        
    def __process_execution_group(self, group_result):
        """
        DESC:
        RETURNS:
        """
        success_count = 0
        fail_count = 0

        for result in group_result:
            try:
                # Handle both 'results' and 'result_data' field names
                result_data = result.get("result_data") or result.get("results")
                
                print(f"[OUTPUT_MONITOR] Processing result for node {result['node_id']}: status={result['status']}")
                
                orchestration_result = process_execution_result(
                    db_path=self.db_path,
                    execution_id=result["execution_id"],
                    node_id=result["node_id"],
                    status=result["status"],
                    result_data=result_data,
                    error_message=result.get("error_message")
                )

                self.stats['database_operations'] += 1

                if orchestration_result.success:
                    success_count += 1
                    print(f"[OUTPUT_MONITOR] Successfully processed result for node {result['node_id']}")
                else:
                    fail_count += 1
                    print(f"[OUTPUT_MONITOR] Failed to process result for node {result['node_id']}: {orchestration_result.error}")

            except Exception as e:
                print(f"[OUTPUT_MONITOR] Exception processing result for node {result.get('node_id', 'unknown')}: {e}")
                fail_count += 1

        return success_count, fail_count




