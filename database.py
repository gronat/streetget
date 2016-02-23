#TODO: http://stackoverflow.com/questions/16506429/check-if-element-is-already-in-a-queue

class Database:
    q = []      # queue
    d = {}      # data visited

    def __init__(self):
        pass

    def enqueue(self, key):
        if key not in self.q and key not in self.d:
            self.q.insert(0, key)

    def dequeue(self):
        return self.q.pop(0)

    def add(self, key, value):
        self.d[key] = value

    def has(self, key):
        return key in self.q or key in self.d

    def qempty(self):
        return self.qsize() == 0

    def qsize(self):
        return len(self.q)

    def dsize(self):
        return len(self.d)



