from threading import Thread
from ..queue_module import BaseQueue


class BaseThread:
    def __init__(self, target: callable, args: tuple, output_queue: BaseQueue):
        self.output_queue = output_queue
        self.thread = Thread(target=target, args=args + (self.output_queue,))

    def start(self):
        self.thread.start()
