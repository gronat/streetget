import Queue
import pickle
import logging

loger = logging.getLogger(__name__)
loger.setLevel(logging.WARNING)

class Dbdata:
    qvec = []
    d = dict()
    s = set()
    active = 0

'''
When sentinel is found in the queue
it terminates worker thread.
'''
class Sentinel:
    pass


class Database:
    def __init__(self):
        self.q = Queue.Queue()
        self.d = dict()
        self.s = set()
        self.active = 0

    def prependSentinel(self):
        self.q.not_empty.acquire()
        try:
            self.q.queue.appendleft(Sentinel())
            self.q.unfinished_tasks += 1
            self.q.not_empty.notify()
        finally:
            self.q.not_empty.release()

    def isSentinel(self, key):
        # 'isinstance' must be used, do not use '=='
        return isinstance(key, Sentinel)

    def enqueue(self, key):
        if key not in self.s:
            self.s.add(key)
            self.q.put(key)

    def dequeue(self):
        item = self.q.get()
        with self.q.mutex:
            self.active += 1
        return item

    def add(self, key, val):
        self.d[key] = val

    def has(self, key):
        return key in self.s

    def dsize(self):
        return len(self.d)

    def qsize(self):
        return self.q.unfinished_tasks - self.active

    def qempty(self):
        return self.qsize() == 0

    def task_done(self):
        with self.q.mutex:
            self.active -= 1
        self.q.task_done()

    def isCompleted(self):
        return self.q.unfinished_tasks == 0

    def join(self):
        self.q.join()

    def active(self):
        return self.active

    def save(self, fname):
        if not self.active == 0:
            raise ValueError('Data still being processed while attempting to save database.')

        dbdata = Dbdata()
        dbdata.d = self.d
        dbdata.s = self.s
        dbdata.active = self.active
        dbdata.qvec = self.q.queue

        with open(fname, 'w') as f:
            pickle.dump(dbdata, f)

    def load(self, fname):
        with open(fname) as f:
            dbdata = pickle.load(f)

        self.d = dbdata.d
        self.s = dbdata.s
        self.active = dbdata.active
        self.q = Queue.Queue()
        for item in dbdata.qvec:
            self.q.put(item)
