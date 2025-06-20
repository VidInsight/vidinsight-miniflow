import multiprocessing
import json


class BaseQueue:
    def __init__(self, maxsize=100):
        self.q = multiprocessing.Queue(maxsize=maxsize)

    def put(self, item: json):
        try:
            self.q.put_nowait(item)
            return True
        except:
            return False

    def get_with_timeout(self, timeout=1.0):
        """Timeout ile non-blocking get"""
        try:
            item = self.q.get(timeout=timeout)
            return item
        except:
            return None

    def get(self):
        try:
            item = self.q.get_nowait()
            return item
        except:
            return None

    def get_without_task(self):
        return self.get()

    def is_empty(self):
        return self.q.empty()

    def size(self):
        return self.q.qsize()



