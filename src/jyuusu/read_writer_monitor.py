from contextlib import contextmanager
from threading import Lock, Condition


class ReadWriteMonitor:
    def __init__(self):
        self.lock = Lock()
        self.can_read = Condition(self.lock)
        self.can_write = Condition(self.lock)
        self.num_readers = 0
        self.num_waiting_writers = 0
        self.has_active_writer = False

    def acquire_read(self):
        with self.lock:
            while self.has_active_writer or self.num_waiting_writers > 0:
                self.can_read.wait()
            self.num_readers += 1

    def release_read(self):
        with self.lock:
            self.num_readers -= 1
            if self.num_readers == 0:
                self.can_write.notify()

    @contextmanager
    def read_session(self):
        self.acquire_read()
        yield
        self.release_read()

    def acquire_write(self):
        with self.lock:
            self.num_waiting_writers += 1
            while self.has_active_writer or self.num_readers > 0:
                self.can_write.wait()
            self.has_active_writer = True
            self.num_waiting_writers -= 1

    def release_write(self):
        with self.lock:
            self.has_active_writer = False
            if self.num_waiting_writers > 0:
                self.can_write.notify()
            else:
                self.can_read.notify_all()

    @contextmanager
    def write_session(self):
        self.acquire_write()
        yield
        self.release_write()