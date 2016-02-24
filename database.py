# http://stackoverflow.com/questions/16506429/check-if-element-is-already-in-a-queue
# http://code.activestate.com/recipes/576694/
import collections
import Queue





class OrderedSet(collections.MutableSet):

    def __init__(self, iterable=None):
        self.end = end = []
        end += [None, end, end]         # sentinel node for doubly linked list
        self.map = {}                   # key --> [key, prev, next]
        if iterable is not None:
            self |= iterable

    def __len__(self):
        return len(self.map)

    def __contains__(self, key):
        return key in self.map

    def add(self, key):
        if key not in self.map:
            end = self.end
            curr = end[1]
            curr[2] = end[1] = self.map[key] = [key, curr, end]

    def discard(self, key):
        if key in self.map:
            key, prev, next = self.map.pop(key)
            prev[2] = next
            next[1] = prev

    def __iter__(self):
        end = self.end
        curr = end[2]
        while curr is not end:
            yield curr[0]
            curr = curr[2]

    def __reversed__(self):
        end = self.end
        curr = end[1]
        while curr is not end:
            yield curr[0]
            curr = curr[1]

    def pop(self, last=True):
        if not self:
            raise KeyError('set is empty')
        key = self.end[1][0] if last else self.end[2][0]
        self.discard(key)
        return key

    def __repr__(self):
        if not self:
            return '%s()' % (self.__class__.__name__,)
        return '%s(%r)' % (self.__class__.__name__, list(self))

    def __eq__(self, other):
        if isinstance(other, OrderedSet):
            return len(self) == len(other) and list(self) == list(other)
        return set(self) == set(other)


if __name__ == '__main__':
    s = OrderedSet('abracadaba')
    t = OrderedSet('simsalabim')
    print(s | t)
    print(s & t)
    print(s - t)

class OrderedSetQueue(Queue.Queue):
    def _init(self, maxsize):
        self.queue = OrderedSet()


    def put(self, key, block=True, timeout=None):
        if isinstance(key, str):
            key = (key,)

        self.not_full.acquire()
        try:
            for item in key:
                if item not in self.queue:
                    self._put(item)
                    self.unfinished_tasks += 1
                    self.not_empty.notify()
        finally:
            self.not_full.release()


    def _put(self, item):
        self.queue.add(item)

    def _get(self):
        return self.queue.pop()

    def __contains__(self, item):
        with self.mutex:
            return item in self.queue


class Database:
    q = OrderedSetQueue()      # queue
    d = {}      # data visited

    def __init__(self):
        pass

    def enqueue(self, key):
        self.q.put(key)

    def dequeue(self):
        return self.q.get()

    def task_done(self):
        self.q.task_done()

    def add(self, key, value):
        self.d[key] = value

    def has(self, key):
        return key in self.q or key in self.d

    def qempty(self):
        return self.q.empty() == 0

    def qsize(self):
        return len(self.q)

    def dsize(self):
        return len(self.d)