import json
import threading
import time
from multiprocessing import cpu_count, Pipe
from threading import Thread
from ..process import BaseProcess
from ..queue_module import BaseQueue
import psutil


class QueueWatcher:
    def __init__(self, input_queue: BaseQueue, output_queue: BaseQueue, os: bool):
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.max_cpu_count = cpu_count() - 1
        self.min_process_count = 1
        self.active_processes = []
        self.started = False
        self.scaler_thread = None
        self.cleanup_thread = None  # Background cleanup thread
        self.shutdown_event = threading.Event()
        self.process_lock = threading.Lock()
        self.current_process_index = 0  # Round-robin selection
        self.priority = -19 if os else psutil.HIGH_PRIORITY_CLASS  # self._unix_process_classes() if os else self._nt_process_classes()
        print(f"QueueWatcher started with priority {self.priority}")

    def start(self):
        """Enhanced start with background cleanup"""
        if self.started:
            raise RuntimeError("QueueWatcher already started")

        self.started = True
        self._start_processes(self.min_process_count)
        self._start_watch_threads(self._watch_input)
        
        # SAFE: Background cleanup thread (non-interfering)
        self.cleanup_thread = threading.Thread(target=self._background_cleanup, daemon=True)
        self.cleanup_thread.start()
        print("[QUEUEWATCHER] Background cleanup started")

    def _watch_input(self):
        """Input Queue tracker"""
        while not self.shutdown_event.is_set():
            try:
                # Non-blocking get with timeout
                item = self.input_queue.get_with_timeout(timeout=1.0)
                if item is not None:
                    with self.process_lock:  # Thread-safe process assignment
                        if len(self.active_processes) > 0:
                            self._create_thread(item)
                        else:
                            # Re-queue item if no processes available
                            self.input_queue.put(item)

            except Exception as e:
                print(f"Input watcher error: {e}")

    def _get_process_thread_counts(self):
        """Legacy method - kept for compatibility"""
        return self._get_thread_counts_safe()

    def _get_thread_counts_safe(self):
        """SAFE: Non-blocking thread count collection"""
        thread_counts = []
        
        # SAFE: Snapshot without holding locks
        active_processes_snapshot = list(self.active_processes)  # Atomic copy
        
        for proc_dict in active_processes_snapshot:
            try:
                # SAFE: Quick health check first
                if not proc_dict['process'].process.is_alive():
                    thread_counts.append(None)
                    continue
                
                # SAFE: Non-blocking communication
                proc_dict['pipe'].send({"command": "get_thread_count"})
                
                # SAFE: Short timeout prevents hanging
                if proc_dict['pipe'].poll(timeout=0.5):  # 500ms max
                    resp = proc_dict['pipe'].recv()
                    thread_counts.append(resp.get("thread_count", 0))
                else:
                    thread_counts.append(None)  # Timeout
                    
            except Exception as e:
                print(f"[AUTO-SCALER] Thread count error: {e}")
                thread_counts.append(None)
        
        return thread_counts

    def _get_next_process(self):
        """SAFE: Round-robin process selection with bounds checking"""
        if not self.active_processes:
            return None
        
        # SAFE bounds check - this prevents the bug
        process_count = len(self.active_processes)
        if self.current_process_index >= process_count:
            self.current_process_index = 0
            print(f"[QUEUEWATCHER] Index reset: 0/{process_count}")
        
        process = self.active_processes[self.current_process_index]
        
        # SAFE round-robin advancement
        self.current_process_index = (self.current_process_index + 1) % process_count
        
        return process

    def _start_processes(self, count):
        """SAFE: Thread-safe process management with no API changes"""
        # Thread-safe process başlatma - existing API preserved
        processes_to_add = []
        
        # Process creation (lock dışında)
        for _ in range(count):
            try:
                parent_conn, child_conn = Pipe()
                process = BaseProcess(child_conn, self.output_queue)
                process.start()
                
                # Process sağlık kontrolü
                time.sleep(0.1)  # Process başlaması için kısa bekleme
                if process.process.is_alive():
                    self._set_process_priority(process.process.pid, self.priority)
                    processes_to_add.append({
                        'process': process,
                        'pipe': parent_conn,
                        'created_at': time.time()
                    })
                    print(f"[QUEUEWATCHER] Started process {process.process.pid}")
                else:
                    # Cleanup failed process
                    try:
                        parent_conn.close()
                        process.shutdown()
                    except:
                        pass
            except Exception as e:
                print(f"[QUEUEWATCHER] Failed to create process: {e}")
        
        # Atomic list update (SAFE)
        if processes_to_add:
            with self.process_lock:
                old_count = len(self.active_processes)
                self.active_processes.extend(processes_to_add)
                new_count = len(self.active_processes)
                
                # Index reset ONLY if processes added successfully
                if new_count > old_count:
                    print(f"[QUEUEWATCHER] Process count: {old_count} -> {new_count}")
                    # SAFE index reset - this is the key fix
                    self.current_process_index = self.current_process_index % new_count if new_count > 0 else 0

    def _stop_processes(self, count):
        """SAFE: Thread-safe process removal"""
        with self.process_lock:
            stop_count = min(count, len(self.active_processes) - self.min_process_count)
            stopped_pids = []
            
            for _ in range(stop_count):
                if len(self.active_processes) <= self.min_process_count:
                    break
                    
                p = self.active_processes.pop()
                try:
                    pid = p['process'].process.pid
                    p['pipe'].send({'command': 'shutdown'})
                    p['process'].shutdown()
                    p['pipe'].close()  # Resource cleanup
                    stopped_pids.append(pid)
                except Exception as e:
                    print(f"[QUEUEWATCHER] Error shutting down process: {e}")
            
            # Index bounds check after removal
            if self.current_process_index >= len(self.active_processes):
                self.current_process_index = 0
                
            print(f"[QUEUEWATCHER] Stopped processes: {stopped_pids}")

    def _create_thread(self, item: json):
        process = self._get_next_process()
        if not process:
            item["error_message"] = {"error": "No active processes available"}
            self.output_queue.put(item)
            return

        command_data = {
            "command": "start_thread",
            "data": "miniflow.parallelism_engine.process.modules.python_runner.python_runner",
            "args": (item,),
            "kwargs": {}
        }
        process.get("pipe").send(command_data)

    def _auto_scale_processes(self):
        """SAFE: Enhanced scaling with existing patterns"""
        scaling_cooldown = 0
        last_action_time = 0
        
        while not self.shutdown_event.is_set():
            try:
                current_time = time.time()
                
                # Rate limiting (prevents rapid scaling)
                if current_time - last_action_time < 3:
                    time.sleep(1)
                    continue
                
                # SAFE: Non-blocking metrics collection
                process_count = len(self.active_processes)  # Atomic read
                
                if process_count == 0:
                    print("[AUTO-SCALER] No processes, starting minimum")
                    self._start_processes(self.min_process_count)
                    last_action_time = current_time
                    continue
                
                # SAFE: CPU measurement
                cpu_usage = psutil.cpu_percent(interval=0.5)
                
                # SAFE: Thread count collection with timeout
                thread_counts = self._get_thread_counts_safe()
                valid_counts = [t for t in thread_counts if t is not None and t >= 0]
                
                if not valid_counts:
                    time.sleep(1)
                    continue
                
                avg_threads = sum(valid_counts) / len(valid_counts)
                max_threads = max(valid_counts)
                
                print(f"[AUTO-SCALER] Processes: {process_count}, CPU: {cpu_usage:.1f}%, "
                      f"Avg Threads: {avg_threads:.1f}, Max: {max_threads}")
                
                # CONSERVATIVE scaling logic (prevents thrashing)
                if (process_count < self.max_cpu_count and 
                    (avg_threads > 2.5 or max_threads > 4) and
                    cpu_usage < 90):  # Don't scale up if CPU maxed
                    
                    print("[AUTO-SCALER] Scaling UP (1 process)")
                    self._start_processes(1)
                    last_action_time = current_time
                    
                elif (process_count > self.min_process_count and 
                      avg_threads < 0.3 and 
                      cpu_usage < 20):
                    
                    print("[AUTO-SCALER] Scaling DOWN (1 process)")
                    self._stop_processes(1)
                    last_action_time = current_time
                
            except Exception as e:
                print(f"[AUTO-SCALER] Error: {e}")
            
            time.sleep(2)  # Conservative polling

    def _background_cleanup(self):
        """SAFE: Non-intrusive background cleanup"""
        while not self.shutdown_event.is_set():
            try:
                # SAFE: Infrequent cleanup (every 10 seconds)
                time.sleep(10)
                
                if self.shutdown_event.is_set():
                    break
                    
                self._cleanup_dead_processes_safe()
                
            except Exception as e:
                print(f"[CLEANUP] Background cleanup error: {e}")

    def _cleanup_dead_processes_safe(self):
        """SAFE: Non-blocking dead process removal"""
        with self.process_lock:
            initial_count = len(self.active_processes)
            
            # SAFE: Filter out dead processes
            alive_processes = []
            dead_pids = []
            
            for proc_dict in self.active_processes:
                try:
                    if proc_dict['process'].process.is_alive():
                        alive_processes.append(proc_dict)
                    else:
                        dead_pids.append(proc_dict['process'].process.pid)
                        # SAFE: Resource cleanup
                        try:
                            proc_dict['pipe'].close()
                        except:
                            pass
                except Exception:
                    # SAFE: Remove problematic entries
                    dead_pids.append("unknown")
            
            # SAFE: Atomic list replacement
            self.active_processes = alive_processes
            
            # SAFE: Index adjustment
            if len(self.active_processes) != initial_count:
                self.current_process_index = 0
                print(f"[CLEANUP] Removed {len(dead_pids)} dead processes: {dead_pids}")
                
                # SAFE: Ensure minimum processes
                if len(self.active_processes) < self.min_process_count:
                    needed = self.min_process_count - len(self.active_processes)
                    print(f"[CLEANUP] Starting {needed} replacement processes")
                    # This calls our safe _start_processes method
                    self._start_processes(needed)

    def shutdown(self):
        """Graceful shutdown"""
        self.shutdown_event.set()

        # Tüm process'lere shutdown komutu gönder
        for p in self.active_processes:
            try:
                p['pipe'].send({"command": "shutdown"})
                p['process'].shutdown()
            except Exception as e:
                print(f"Error shutting down process: {e}")

    def _start_watch_threads(self, input_func: callable):
        input_thread = Thread(target=input_func, daemon=True)
        input_thread.start()

        self.scaler_thread = threading.Thread(target=self._auto_scale_processes, daemon=True)
        self.scaler_thread.start()

    def _set_process_priority(self, pid: int, priority):
        """Setting process priority (with error handling)"""
        try:
            ps_process = psutil.Process(pid)
            ps_process.nice(priority)
            return True
        except (psutil.AccessDenied, PermissionError) as e:
            print(f"[QueueWatcher] Priority ayarlanamadı (normal): {e}")
            return False
        except Exception as e:
            print(f"[QueueWatcher] Priority ayarlama hatası: {e}")
            return False

    def _nt_process_classes(self):
        """Windows process priority classes"""
        return [psutil.IDLE_PRIORITY_CLASS, psutil.BELOW_NORMAL_PRIORITY_CLASS,
                psutil.NORMAL_PRIORITY_CLASS, psutil.ABOVE_NORMAL_PRIORITY_CLASS,
                psutil.HIGH_PRIORITY_CLASS, psutil.REALTIME_PRIORITY_CLASS]

    def _unix_process_classes(self):
        """Unix based systems process priority range (-20 max priority, 20 min priority)"""
        return [i for i in range(-20, 21)]
