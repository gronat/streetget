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

    def cleanSentinels(self):
        self.q.not_full.acquire()
        try:
            while(len(self.q.queue) > 0 and self.isSentinel(self.q.queue[0])):
                # dead lock
                self.q.queue.popleft()
                self.q.unfinished_tasks -= 1
            self.q.not_full.notify()
        finally:
            self.q.not_full.release()

    def isSentinel(self, key):
        # 'isinstance' must be used, do not use '=='
        if  isinstance(key, Sentinel) or \
            str(key.__class__) == 'streetget.database.Sentinel':
            return True

        return False

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

        dbdata = Dbdata()
        dbdata.d = self.d
        dbdata.s = self.s
        dbdata.active = self.active
        dbdata.qvec = self.q.queue

        with open(fname, 'w') as f:
            pickle.dump(dbdata, f)

        if not self.active == 0:
            raise ValueError('Non-zero active thread counter.')

    def load(self, fname):
        with open(fname) as f:
            dbdata = pickle.load(f)

        self.d = dbdata.d
        self.s = dbdata.s
        self.active = dbdata.active
        self.q = Queue.Queue()
        for item in dbdata.qvec:
            self.q.put(item)

def test1():
    db = Database()
    for k in range(4):
        db.prependSentinel()
    db.cleanSentinels()

    if db.qsize() != 0:
        print 'FAILED'
    else:
        print 'PASSED'

def test2():
    fname = '/home/petr/work/python/shibuya/01/debug_db.pickle'
    db = Database()
    db.prependSentinel()
    db.save('foo.pickle')
    db.load(fname)
    db.cleanSentinels()
    if db.isSentinel(db.q.queue[0]):
        print 'FAILED'
    else:
        print 'PASSED'

if __name__ == '__main__':

    test1()
    test2()

    fname = '/home/petr/work/python/shibuya/01/debug_db.pickle'

    db = Database()
    db.load(fname)
    db.qsize()
