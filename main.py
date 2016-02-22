import sys
import Queue
from numpy import random
from panorama import Panorama







def printList(l, spaceStr=''):

    sys.stdout.write('\n')
    sys.stdout.write(spaceStr)
    for x in l:
        if not isinstance(x, list):
            sys.stdout.write(unicode(x) + ', ')
        else:
            printList(x, spaceStr+'\t')


def randomCrawl():
    latlng = (50, 14.41)
    p = Panorama(latlng=latlng)
    cnt = 0
    while True:
        cnt += 1
        print 'visited: ' + str(cnt)
        print p
        print '______________________\n'
        ids = p.getAllNeighbours()
        j = random.randint(0, len(ids)-1)
        pano_id = ids[j]
        if isinstance(pano_id, int):
            pass
        p = Panorama(pano_id)


def measure(evalFnc):
    import cProfile, pstats, StringIO

    pr = cProfile.Profile()
    pr.enable()
    # Measure performance
    evalFnc()
    #
    pr.disable()
    s = StringIO.StringIO()
    sortby = 'cumulative'
    ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
    ps.print_stats()
    print s.getvalue()


def runThreads():
    from Queue import Queue
    import threading

    num_worker_threads = 12
    printLock = threading.Lock()
    global n
    n = 0

    def worker():
        global n
        while True:
            pano_id = q.get()
            p = Panorama(pano_id)
            for pano_id in p.getAllNeighbours():
                q.put(pano_id)

            with printLock:
                n += 1
                print(n)
            q.task_done()

    q = Queue()

    for i in range(num_worker_threads):
         t = threading.Thread(target=worker)
         t.daemon = True
         t.start()

    p = Panorama(latlng=(50, 14.41))
    for pano_id in p.getAllNeighbours():
        q.put(pano_id)

    q.join()       # block until all tasks are done


import time
def run(p, zoom, n_threads):
    t0 = time.time()
    img = p.getImage(zoom, n_threads)
    t = time.time()
    print('t = '+str(t-t0))
    return img

if __name__ == '__main__':
    p = Panorama(latlng=(50, 14.41))
    #p.getTile(1,1)
    p.getImage(2)
    pass

