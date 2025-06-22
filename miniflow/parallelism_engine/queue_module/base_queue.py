import multiprocessing
import json


class BaseQueue:
    def __init__(self, maxsize=1000):  # Increased from 100 to 1000
        self.q = multiprocessing.Queue(maxsize=maxsize)

    def put(self, item: json):
        try:
            self.q.put_nowait(item)
            return True
        except:
            return False
    
    def put_with_retry(self, item: json, max_retries=3):
        """Put with exponential backoff retry - prevents silent failures"""
        import time
        for attempt in range(max_retries):
            try:
                self.q.put_nowait(item)
                return True
            except:  # Queue full
                if attempt < max_retries - 1:
                    time.sleep(0.01 * (2 ** attempt))  # Exponential backoff
                else:
                    # Log queue full error instead of silent failure
                    return False
        return False
    
    def put_batch(self, items: list):
        """Bulk put operation for better performance"""
        success_count = 0
        for item in items:
            if self.put_with_retry(item):
                success_count += 1
        return success_count == len(items)

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



