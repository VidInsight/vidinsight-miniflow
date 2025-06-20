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
