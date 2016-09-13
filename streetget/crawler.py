import threading
import os
import logging
import validator
import shutil
from panorama import Panorama
from database import Database
import time

loger = logging.getLogger('crawler')
loger.setLevel(logging.DEBUG)

class Crawler:
    t_save  = 300                # backup db every 5min
    n_thr   = 4                  # No. of crawling threads

    def __init__(self,
                    latlng=None, pano_id=None, validator=None,
                    root='myData', label='myCity', zoom=5,
                    images=False, depth=False, time=True
                 ):
        if not latlng and not pano_id:
            raise ValueError('start point (latlng or pano_id) not given')

        loger.info('___ Crawler starting ___')

        self.dir = os.path.join(root, label)
        self.fname = os.path.join(root, label, 'db.pickle')
        self.fname_bck = self.fname + '.bck'

        self.zoom = zoom if isinstance(zoom, list) else [zoom]  # zoom must be a list
        self.start_id = pano_id
        self.start_latlng = latlng
        self.inArea = validator

        self.db = Database()
        self.threads = self.n_thr * [None]      # thread vector allocation
        self.exit_flag = False                  # flag for signaling threads

        self.images = images
        self.depth = depth
        self.time = time

        if not os.path.exists(self.dir):        # create dir
            os.makedirs(self.dir)

        if os.path.exists(self.fname):          # resume existing crawler db
            if not self.load(self.fname):
                self.load(self.fname_bck)       # roll back to backup
        else:                                   # new  crawler db
            p = Panorama(self.start_id, self.start_latlng)
            self.db.enqueue(p.pano_id)          # starting panorama into a queue

    def save(self, fname):
        try:
            self.db.save(fname)
            loger.info('db saved to ' + fname)
        except Exception as e:
            msg = 'Database save failed! Active threads still accessing the database'
            loger.error(msg)
            raise e

    def load(self, fname):
        try:
            self.db.load(fname)
            return True
        except Exception as e:
            msg = 'db loadin failed! %s:%s' % (type(e).__name__, str(e))
            loger.error(msg)
        return False
    
    def backup(self):
        loger.debug('Bacingk up')
        self.stopThreads()
        try:
            self.save(self.fname)
            shutil.copyfile(self.fname, self.fname_bck)
        finally:
            self.startThreads()

    def visitPano(self, p):
        """
        Visits panorama, extracts meta data and adds
        info about panorama into database. Neighbour
        panoramas are added to the database queue.
        """
        if not (p and p.isValid() and self.inArea(p)):
            return

        neighbours = p.getAllNeighbours() if self.time else p.getSpatialNeighbours()
        for n in neighbours:
            self.db.enqueue(n)            # update queue

        if p.isCustom():
            return                        # not Google panorama

        data = {'latlng': p.getGPS(), 'date': p.getDate()}
        self.db.add(p.pano_id, data)      # update visited db
        
    def savePano(self, p, zoom):
        """
        Saves panorama image at given zoom-level and its
        metadata. Directory name corresponds to the first
        two characters of the pano_id hash.
        :param p: Panorama - object
        :param zoom: int [0-5] iterable - zoom levels
        """
        n_threads = 4

        if not (p and p.isValid() and self.inArea(p)):
            return

        if p.isCustom():
            return          # not Google panorama

        pdir = os.path.join(self.dir, '_' + p.pano_id[0:2])
        pname = p.pano_id
        pbase = os.path.join(pdir, pname)

        if not os.path.exists(pdir):
            os.makedirs(pdir)

        p.saveMeta(pbase + '_meta.json')
        p.saveTimeMeta(pbase + '_time_meta.json')

        if self.images:
            for z in zoom:
                if p.hasZoom(z):
                    p.saveImage(pbase + '_zoom_' + str(z) + '.jpg', z, n_threads)
        dzoom = 0
        if self.depth:
            p.saveDepthData(pbase+'_depth.json')
            p.saveDepthImage(pbase+'_zoom_0_depth.jpg', dzoom)

    def worker(self):
        while not self.exit_flag:
            pano_id = self.db.dequeue()
            if self.db.isSentinel(pano_id):
                self.db.task_done()
                return
            p = Panorama(pano_id)
            self.savePano(p, self.zoom)
            self.visitPano(p)
            self.db.task_done()

    def startThreads(self):
        self.exit_flag = False
        for j in range(self.n_thr):
            self.threads[j] = threading.Thread(target=self.worker)
            self.threads[j].start()
        loger.debug('Threads started')

    def stopThreads(self):
        loger.debug('Stopping threads...')
        for _ in self.threads:
            self.db.prependSentinel()   # sentinel exits thread

        for t in self.threads:
            t.join()
        loger.debug('Threads stopped')

    def onexit(self):
        print 'Sopping threads and saving.... please wait.'
        loger.debug('Exiting')
        self.stopThreads()
        self.save(self.fname)
        print 'Done'

    def run(self):
        """
        Performs parallel BFS crawling. Main threads perform crawling via BFS.
        There are two auxiliary threads. Former manages periodic database backup
        while latter periodically prints state of downloading. Saving the current
        state at KeyboardInterrupt is handled.
        """
        self.startThreads()
        monitor = Monitor(self.db)
        backuper = Backuper(self.backup, self.t_save)

        try:
            while not self.db.isCompleted():
                monitor.printReport()           # display current state
                backuper.check()                # periodic backup
                time.sleep(5)

            print('All panorama collected')

        except (KeyboardInterrupt, SystemExit):
            loger.debug('*** handling keyboard or system interrupt')
            #raise
        except Exception as e:
            raise e
        finally:
            self.onexit()

class Monitor:
    def __init__(self, db):
        self.db = db
        self.t0 = time.time()
        self.n0 = db.dsize()
        self.tl = self.t0
        self.nl = self.n0

    def printReport(self):
        t = time.time()
        n = self.db.dsize()

        avg = (n - self.n0)/(t - self.t0)*60
        v = (n - self.nl)/(t - self.tl)*60

        print 'Downloaded: %06d\t Queue: %05d\t %05d/min\t avg %05d/min' % \
              (n, self.db.qsize(), v, avg)

        self.tl = t
        self.nl = n

class Backuper:
    def __init__(self, backupFnc, period):
        self.tl = time.time()
        self.backupFnc = backupFnc
        self.period = period

    def check(self):
        t = time.time()
        if (t-self.tl) > self.period:
            print 'Calling backing up function'
            self.backupFnc()
            print 'Backed up!'
            self.tl = time.time()

if __name__ == '__main__':
    ll_Praha = (50.0833, 14.4167)
    ll_Berk = (37.8734834, -122.2593292)
    ll_Berk3 = (37.8734834, -122.2593292-0.01)

    # PARAMETERS
    ll0 = ll_Praha
    lbl = 'testPraha'
    z = [0, 3]              # zoom-level
    r = 500                 # radius
    #_______________

    print ll0


    circle = validator.circle(ll0, r)
    c = Crawler(latlng=ll0, label=lbl, zoom=z, validator=circle, root='../data', images=True, depth=True, time=False)
    c.run()
    pass

