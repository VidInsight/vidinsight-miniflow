from multiprocessing import Process, Pipe
from .base_thread import BaseThread
from ..queue_module import BaseQueue
import threading
import time
import importlib


class BaseProcess:
    def __init__(self, pipe, output_queue: BaseQueue):
        """
        pipe: Bu process'e özel child_conn
        output_queue: Sonuçları QueueWatcher'a göndermek için paylaşılan kuyruk
        """
        self.pipe = pipe
        self.output_queue = output_queue
        # Lock'ları process içinde oluşturacağız - pickle issue
        self.process = Process(target=self.run_process, args=(self.pipe, self.output_queue))

    def _cleanup_dead_threads(self):
        """Bitmiş thread'leri listeden çıkar"""
        if hasattr(self, 'threads'):
            self.threads = [t for t in self.threads if t.thread.is_alive()]

    def start(self):
        self.process.start()

    def run_process(self, pipe, output_queue):
        """
        Bu method, process içinde çalışacak.
        pipe: Bu process'e özel child_conn
        output_queue: Sonuçları QueueWatcher'a göndermek için paylaşılan kuyruk
        """
        # Process içinde lock ve thread listesi oluştur
        self.threads = []
        self.lock = threading.Lock()
        self.shutdown_event = threading.Event()
        
        def thread_controller():
            while not self.shutdown_event.is_set():
                try:
                    self._cleanup_dead_threads()
                    # Pipe'tan yeni komut var mı kontrol et
                    if pipe.poll():
                        command_data = pipe.recv()  # pipe üzerinden komutu al

                        if command_data["command"] == "start_thread":
                            dotted_path = command_data["data"]
                            target_func = self.import_from_path(dotted_path)
                            args = command_data.get("args", ())
                            kwargs = command_data.get("kwargs", {})

                            self.start_thread(target_func, args, kwargs)
                            
                        elif command_data["command"] == "shutdown":
                            self.shutdown_event.set()
                            break

                        elif command_data["command"] == "get_thread_count":
                            pipe.send({"thread_count": len(self.threads)})
                            
                        elif command_data["command"] == "ping":
                            pipe.send({"status": "pong"})
                            
                except Exception as e:
                    output_queue.put({"error": f"Thread controller error: {e}"})

                time.sleep(0.1)  # Daha responsive

        # Komutları dinleyen thread'i başlat
        controller = threading.Thread(target=thread_controller, daemon=True)
        controller.start()

        # Graceful shutdown için controller thread'ini bekle
        while not self.shutdown_event.is_set():
            time.sleep(1)

    def start_thread(self, target, args, kwargs):
        """
        Yeni thread başlat ve yönet.
        """
        thread = BaseThread(target=target, args=args, output_queue=self.output_queue)
        thread.start()
        
        if hasattr(self, 'lock'):
            with self.lock:
                self.threads.append(thread)
                # Periyodik temizlik
                if len(self.threads) > 3:  # Threshold
                    self._cleanup_dead_threads()

    def shutdown(self):
        """Graceful shutdown"""
        if hasattr(self, 'shutdown_event'):
            self.shutdown_event.set()
        if self.process.is_alive():
            self.process.terminate()
            self.process.join(timeout=5)

    def import_from_path(self, dotted_path):
        """
        Örnek: "process.modules.bash_runner.bash_runner"
        """
        module_path, func_name = dotted_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        return getattr(module, func_name)
