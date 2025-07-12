import json
import time
import psutil
from ..process import BaseProcess
from threading import Thread, Lock, Event
from multiprocessing import cpu_count, Pipe



class ProcessController:
    def __init__(self, output_queue, os: bool):
        self.output_queue = output_queue
        self.output_queue = output_queue
        self.max_cpu_count = cpu_count() - 1
        self.min_process_count = 2
        self.thread_lock_limit = self.max_cpu_count * 3
        self.active_processes = []
        self.started = False
        self.scaler_thread = None
        self.thread_count_list = []
        self.shutdown_event = Event()
        self.process_lock = Lock()
        self.auto_scale = False
        self.current_process_index = 0  # Round-robin selection
        self.priority = -19 if os else psutil.HIGH_PRIORITY_CLASS  # self._unix_process_classes() if os else self._nt_process_classes()

    def start(self):
        """Sadece bir kez başlatılabilir"""
        if self.started:
            raise RuntimeError("QueueWatcher already started")

        self.started = True
        if self.auto_scale:
            self._start_processes(self.min_process_count)
        else:
            self._start_processes(self.max_cpu_count)

        self._start_thread_counter()

    def _start_processes(self, count):
        for _ in range(count):
            cmd_parent_conn, cmd_child_conn = Pipe()
            health_parent_conn, health_child_conn = Pipe()
            process = BaseProcess(cmd_child_conn, health_child_conn, self.output_queue)
            process.start()
            self._set_process_priority(process.process.pid, self.priority)
            print(f"[QUEUEWATCHER] Starting process {process.process.pid}")
            self.active_processes.append({
                'process': process,
                'cmd_pipe': cmd_parent_conn,
                'health_pipe': health_parent_conn,
            })

    def _stop_processes(self, count):
        with self.process_lock:
            for _ in range(min(count, len(self.active_processes) - self.min_process_count)):
                p = self.active_processes.pop()
                try:
                    p['cmd_pipe'].send({'command': 'shutdown'})
                    p['process'].shutdown()
                except Exception as e:
                    print(f"Error shutting down process: {e}")

    def _get_next_process(self):
        """Select the process with the lowest thread count"""
        if not self.active_processes or None in self.thread_count_list:
            return None

        thread_count_list = self.thread_count_list

        if sum(thread_count_list) >= self.thread_lock_limit:
            selected_process = self.active_processes[self.current_process_index]
            self.current_process_index = (self.current_process_index + 1) % self.max_cpu_count

        else:
            index = thread_count_list.index(min(thread_count_list))
            selected_process = self.active_processes[index]
            self.current_process_index = index

        return selected_process

    def create_thread(self, item: json):
        process = self._get_next_process()
        if process is None:
            """item["error_message"] = {"error": "No active processes available"}
            self.output_queue.put(item)"""
            self.input_queue.put(item)
            return

        command_data = {
            "command": "start_thread",
            "data": "miniflow.parallelism_engine.process.modules.python_runner.python_runner",
            "args": (item,),
            "kwargs": {}
        }
        process.get("cmd_pipe").send(command_data)

    def _auto_scale_processes(self):
        while not self.shutdown_event.is_set():
            try:
                cpu_usage = psutil.cpu_percent(interval=1)
                self.thread_count_list = self._get_process_thread_counts()
                avg_threads = sum(t for t in self.thread_count_list if t is not None) / max(1, len(self.thread_count_list))
                print(self.thread_count_list)
                if len(self.active_processes) < self.max_cpu_count and avg_threads > 1.5:
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
                p['cmd_pipe'].send({"command": "shutdown"})
                p['process'].shutdown()
            except Exception as e:
                print(f"Error shutting down process: {e}")

    def _get_process_thread_counts(self):
        thread_counts = []
        with self.process_lock:
            for proc_dict in self.active_processes:
                try:
                    proc_dict['health_pipe'].send({"command": "get_thread_count"})
                    if proc_dict['health_pipe'].poll(0.05):  # 1 sn timeout
                        resp = proc_dict['health_pipe'].recv()
                        thread_counts.append(resp.get("thread_count", 0))
                    else:
                        thread_counts.append(None)
                except Exception as e:
                    print(f"Error getting thread count: {e}")
                    thread_counts.append(None)
        return thread_counts

    def _thread_count_updater(self):
        while not self.shutdown_event.is_set():
            self.thread_count_list = self._get_process_thread_counts()
            print(self.thread_count_list)
            time.sleep(0.2)

    def _start_thread_counter(self):
        if self.auto_scale:
            self.scaler_thread = Thread(target=self._auto_scale_processes, daemon=True)
            self.scaler_thread.start()

        else:
            self.scaler_thread = Thread(target=self._thread_count_updater, daemon=True)
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