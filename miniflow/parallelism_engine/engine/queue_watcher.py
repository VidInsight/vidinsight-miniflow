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
        self.thread_lock_limit = self.max_cpu_count * 3
        self.active_processes = []
        self.started = False
        self.scaler_thread = None
        self.shutdown_event = threading.Event()
        self.process_lock = threading.Lock()
        self.current_process_index = 0  # Round-robin selection
        self.priority = -19 if os else psutil.HIGH_PRIORITY_CLASS  # self._unix_process_classes() if os else self._nt_process_classes()
        print(f"QueueWatcher started with priority {self.priority}")

    def start(self):
        """Sadece bir kez başlatılabilir"""
        if self.started:
            raise RuntimeError("QueueWatcher already started")

        self.started = True
        self._start_processes(self.min_process_count)  # Sadece burada başlat
        self._start_watch_threads(self._watch_input)

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
        thread_counts = []
        with self.process_lock:
            for proc_dict in self.active_processes:
                try:
                    proc_dict['pipe'].send({"command": "get_thread_count"})
                    if proc_dict['pipe'].poll():  # 1 sn timeout
                        resp = proc_dict['pipe'].recv()
                        thread_counts.append(resp.get("thread_count", 0))
                    else:
                        thread_counts.append(None)
                except Exception as e:
                    print(f"Error getting thread count: {e}")
                    thread_counts.append(None)
        return thread_counts

    def _get_next_process(self):
        """Select the process with the lowest thread count"""
        if not self.active_processes:
            return None

        min_threads = float('inf')
        selected_process = None

        for proc in self.active_processes:
            try:
                proc["pipe"].send({"command": "get_thread_count"})
                if proc["pipe"].poll(timeout=0.1):  # timeout önemli
                    resp = proc["pipe"].recv()
                    count = resp.get("thread_count", 0)
                    if count < min_threads:
                        min_threads = count
                        selected_process = proc
            except Exception as e:
                print(f"[Process Selection] Error polling thread count: {e}")

        return selected_process or self.active_processes[0]  # fallback

    def _check_process_thread_count(self, process):
        command_data = {"command": "start_thread"}
        with self.process_lock:
            process.get("pipe").send(command_data)
            if process['pipe'].poll():  # 1 sn timeout
                resp = process['pipe'].recv()
                count = resp.get("thread_count", 0)
                return count
            else:
                return 0

    def _start_processes(self, count):
        for _ in range(count):
            parent_conn, child_conn = Pipe()
            process = BaseProcess(child_conn, self.output_queue)
            process.start()
            self._set_process_priority(process.process.pid, self.priority)
            print(f"[QUEUEWATCHER] Starting process {process.process.pid}")
            self.active_processes.append({
                'process': process,
                'pipe': parent_conn
            })

    def _stop_processes(self, count):
        with self.process_lock:
            for _ in range(min(count, len(self.active_processes) - self.min_process_count)):
                p = self.active_processes.pop()
                try:
                    p['pipe'].send({'command': 'shutdown'})
                    p['process'].shutdown()
                except Exception as e:
                    print(f"Error shutting down process: {e}")

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
        while not self.shutdown_event.is_set():
            try:
                cpu_usage = psutil.cpu_percent(interval=1)
                thread_counts = self._get_process_thread_counts()
                avg_threads = sum(t for t in thread_counts if t is not None) / max(1, len(thread_counts))
                print(self._get_process_thread_counts())
                if len(self.active_processes) < self.max_cpu_count and avg_threads > 2:
                    print("[Parallelism Engine] Scaling up processes")
                    self._start_processes(1)

                elif cpu_usage < 30 and len(self.active_processes) > self.min_process_count and avg_threads < 1:
                    print("[Parallelism Engine] Scaling down processes")
                    self._stop_processes(1)

            except Exception as e:
                print(f"Scaler error: {e}")

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
