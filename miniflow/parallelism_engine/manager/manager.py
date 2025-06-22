from ..queue_module import BaseQueue
from ..engine import QueueWatcher
import json
import atexit
import signal
import sys
import platform


class Manager:
    def __init__(self):
        self.input_queue = BaseQueue()
        self.output_queue = BaseQueue()
        self.watcher = None
        self.started = False

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        atexit.register(self.shutdown)

    def start(self):
        if not self.started:
            self.watcher = QueueWatcher(self.input_queue, self.output_queue, False if platform.system() == "Windows" else True)
            self.watcher.start()
            self.started = True

    def put_item(self, item: json):
        if not self.started:
            self.start()
        return self.input_queue.put(item)

    def put_items_bulk(self, items: list):
        """
        Amaç: Birden fazla item'ı bulk olarak ekler (batch processing için)
        Döner: Başarı durumu (True/False)
        """
        if not self.started:
            self.start()
        
        if not items:
            return True
            
        success_count = 0
        total_items = len(items)
        
        # Tüm item'ları ekle
        for item in items:
            if self.input_queue.put(item):
                success_count += 1
        
        # Tüm item'lar başarılı ise True döner
        return success_count == total_items

    def shutdown(self):
        """Graceful shutdown"""
        if self.watcher and self.started:
            self.watcher.shutdown()
            self.started = False
            return True

    def _signal_handler(self, signum, frame):
        self.shutdown()
        sys.exit(0)

    def get_output_item(self):
        return self.output_queue.get_with_timeout(timeout=1.0)
