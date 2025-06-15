import json
import threading
from multiprocessing import cpu_count, Pipe
from threading import Thread
from ..process import BaseProcess
from ..queue_module import BaseQueue


class QueueWatcher:
    def __init__(self, input_queue: BaseQueue, output_queue: BaseQueue):
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.cpu_count = cpu_count() - 1
        self.active_processes = []
        self.started = False
        self.shutdown_event = threading.Event()
        self.process_lock = threading.Lock()
        self.current_process_index = 0  # Round-robin selection

    def start(self):
        """Sadece bir kez başlatılabilir"""
        if self.started:
            raise RuntimeError("QueueWatcher already started")

        self.started = True
        self._start_processes()  # Sadece burada başlat
        self._start_watch_threads(self._watch_input)

    def _watch_input(self):
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

    def _get_next_process(self):
        """Round-robin process selection"""
        if not self.active_processes:
            return None

        process = self.active_processes[self.current_process_index]
        self.current_process_index = (self.current_process_index + 1) % len(self.active_processes)
        return process

    def _watch_output(self):
        while not self.shutdown_event.is_set():
            try:
                """item = self.output_queue.get_with_timeout(timeout=1.0)
                if item is not None:
                    print(item)"""
                pass
            except Exception as e:
                print(f"Output watcher error: {e}")

    def _start_processes(self):
        for p_count in range(self.cpu_count):
            parent_conn, child_conn = Pipe()
            process = BaseProcess(child_conn, self.output_queue)
            process.start()
            self.active_processes.append({
                'process': process,
                'pipe': parent_conn
            })

    def _create_thread(self, item: json):
        process = self._get_next_process()
        if not process:
            item["error_message"] = {"error": "No active processes available"}
            self.output_queue.put(item)
            return

        command_data = {
            "command": "start_thread",
            "data": "process.modules.python_runner.python_runner",
            "args": (item,),
            "kwargs": {}
        }
        process.get("pipe").send(command_data)

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
