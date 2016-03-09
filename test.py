import Queue
import random
from time import sleep
import threading
import time

sentinel = object()

def doSomething(q,i):
    print 'Starting thread ' + str(i)
    while True:
        print 'getting from q'
        item = q.get()
        if item is sentinel:
            print 'sentinel'
            q.put(sentinel)
            q.task_done()
            break
        print 'thread %d pop from q %d' % (i,item,)
        sleep(random.randint(0,10)*0.1)
        q.task_done()
        print 'loop end'
    print 'exiting thread ' +str(i)

def run():
    q = Queue.Queue()
    for i in range(4):
        t = threading.Thread(target=doSomething, args=(q,i))
        t.setDaemon(True)
        t.start()


    for i in range(99):
        q.put(i)
    q.put(sentinel)
    q.task_done()

    q.join()
    sleep(2)
    print 'run end'

    sleep(3)
    return

def foo():
    now = time.time()
    dt  =now-foo.last
    print str(dt)


if __name__ == '__main__':
    foo.last = time.time()
    while True:
        foo()
        time.sleep(3)
    try:
        print 'a'
        raise KeyboardInterrupt
    except:
        print 'b'
        4/0
        raise KeyboardInterrupt
    finally:
        print 'c'