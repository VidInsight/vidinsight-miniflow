import multiprocessing
import json
import queue
import time


class BaseQueue:
    def __init__(self, maxsize=1000):  # Increased from 100 to 1000
        self.q = multiprocessing.Queue(maxsize=maxsize)
        self.dropped_items = 0  # Track dropped items for monitoring

    def put(self, item: json):
        """Enhanced put with better error handling"""
        try:
            self.q.put_nowait(item)
            return True
        except queue.Full:
            self.dropped_items += 1
            print(f"[BaseQueue] WARNING: Queue full, item dropped (total dropped: {self.dropped_items})")
            return False
        except Exception as e:
            self.dropped_items += 1
            print(f"[BaseQueue] ERROR: Put failed: {e}")
            return False
    
    def put_with_retry(self, item: json, max_retries=3, retry_delay=0.1):
        """Put with retry mechanism"""
        for attempt in range(max_retries):
            if self.put(item):
                return True
            
            if attempt < max_retries - 1:  # Don't sleep on last attempt
                time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
        
        # Final attempt with blocking put
        try:
            self.q.put(item, timeout=1.0)
            return True
        except:
            self.dropped_items += 1
            print("[BaseQueue] CRITICAL: Queue full after 3 retries, item dropped")
            return False
    
    def put_batch(self, items: list):
        """Batch put operation with retry mechanism"""
        if not items:
            return True
        
        successful = 0
        for item in items:
            if self.put(item):
                successful += 1
        
        success_rate = successful / len(items)
        if success_rate < 0.8:  # Less than 80% success
            print(f"[BaseQueue] WARNING: Batch put low success rate: {success_rate:.1%}")
        
        return success_rate > 0.5  # Return True if more than 50% successful

    def get_with_timeout(self, timeout=1.0):
        """Get with timeout - safer version"""
        try:
            return self.q.get(timeout=timeout)
        except queue.Empty:
            return None
        except Exception as e:
            print(f"[BaseQueue] ERROR: Get with timeout failed: {e}")
            return None

    def get(self):
        """Legacy get method - kept for compatibility"""
        try:
            item = self.q.get_nowait()
            return item
        except queue.Empty:
            return None
        except Exception as e:
            print(f"[BaseQueue] Get error: {e}")
            return None

    def get_without_task(self):
        return self.get()

    def is_empty(self):
        return self.q.empty()

    def size(self):
        """Get queue size with error handling"""
        try:
            return self.q.qsize()
        except Exception:
            return 0

    def qsize(self):
        """Alias for size() - compatibility"""
        return self.size()

    def get_stats(self):
        """Get queue statistics"""
        try:
            size = self.q.qsize()
        except:
            size = -1  # Unknown size
        
        return {
            'size': size,
            'dropped_items': self.dropped_items,
            'is_empty': size == 0 if size >= 0 else False
        }



