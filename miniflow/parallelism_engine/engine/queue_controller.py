from threading import Event, Lock, Thread
import time


class QueueController:
    def __init__(self, input_queue, process_controller):
        self.input_queue = input_queue
        self.process_controller = process_controller
        self.started = False
        self.shutdown_event = Event()
        self.process_lock = Lock()

    def start(self):
        if self.started:
            raise RuntimeError("QueueWatcher already started")

        watcher_thread = Thread(target=self.watch_input_queue, daemon=True)
        watcher_thread.start()

        self.started = True

    def watch_input_queue(self):
        while not self.shutdown_event.is_set():
            try:
                item = self.input_queue.get_with_timeout(timeout=1.0)
                if item is not None:
                    with self.process_lock:
                        if self.process_controller.create_thread(item):
                            print("[QUEUE CONTROLLER] Task Created")
                        else:
                            print("[QUEUE CONTROLLER] Task Can Not Created")

                        time.sleep(1)

            except Exception as e:
                print(f"Input watcher error: {e}")
