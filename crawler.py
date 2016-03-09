import threading
import os
import dill
import logging
import validator
import matplotlib.pyplot as plt
import shutil
from panorama import Panorama
from database2 import Database
import time

loger = logging.getLogger('crawler')
loger.setLevel(logging.DEBUG)

class Crawler:
    t_save  = 300                # backup db every 10min
    n_thr   = 16                 # No. of crawling threads

    def __init__(self,
                    latlng=None, pano_id=None, label='myCity',
                    root='myData', validator=None, zoom=5, images=False
                 ):
        if not latlng and not pano_id:
            raise ValueError('start point (latlng or pano_id) not given')

        loger.info('___ Crawler starting ___')

        self.dir = os.path.join(root, label)
        self.fname = os.path.join(root, label, 'db.pickle')
        self.fname_bck = self.fname + '.bck'

        self.zoom = zoom if isinstance(zoom, list) else [zoom]
        self.start_id = pano_id
        self.start_latlng = latlng
        self.inArea = validator

        self.db = Database()
        self.threads = self.n_thr * [None]      # thread vector allocation
        self.exit_flag = False                  # flag for signaling threads

        self.images = images

        if not os.path.exists(self.dir):        # new dataset
            os.makedirs(self.dir)
            p = Panorama(self.start_id, self.start_latlng)
            self.db.enqueue(p.pano_id)          # starting panorama into a queue
        else:
            if not self.load(self.fname):       # restore existing database
                self.load(self.fname_bck)       # roll back to backup

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
        loger.debug('Backup')
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

        for n in p.getAllNeighbours():
            self.db.enqueue(n)            # update queue
            
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

        pdir = os.path.join(self.dir, '_' + p.pano_id[0:2])
        pname = p.pano_id
        pbase = os.path.join(pdir, pname)

        if not os.path.exists(pdir):
            os.makedirs(pdir)

        p.saveMeta(pbase + '_meta.json')
        p.saveTimeMeta(pbase + '_time_meta.json')
        if self.images:
            for z in zoom:
                p.saveImage(pbase + '_zoom_' + str(z) + '.jpg', z, n_threads)

    def threader(self):
        while not self.exit_flag:
            pano_id = self.db.dequeue()
            if self.db.isSentinel(pano_id):
                self.db.task_done()
                return
            p = Panorama(pano_id)
            self.visitPano(p)
            self.savePano(p, self.zoom)
            self.db.task_done()

    def startThreads(self):
        self.exit_flag = False
        for j in range(self.n_thr):
            self.threads[j] = threading.Thread(target=self.threader)
            self.threads[j].start()
        loger.debug('Threads started')

    def stopThreads(self):
        for _ in self.threads:
            self.db.prependSentinel()

        for t in self.threads:
            t.join()
        loger.debug('Threads stopped')

    def onexit(self):
        loger.debug('Exiting')
        self.stopThreads()
        self.save(self.fname)

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
                monitor.printReport()
                backuper.check()
                time.sleep(2)


            print('All panorama collected')
        except (KeyboardInterrupt, SystemExit):
            loger.debug('*** handling keyboard or system interrupt')
            #raise
        except Exception as e:
            raise
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

        print 'DB size: %06d\t Q size: %05d\t %05d/min\t avg %05d/min' % \
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
            self.backupFnc()
            print 'Backed up!'
            self.tl = time.time()

def plotData(fname):
    db = Database()
    db.load(fname)
    d = db.d
    lat = [d[key]['latlng'][0] for key in d]
    lng = [d[key]['latlng'][1] for key in d]
    lat = [lat[j] for j in range(0,len(lat),1)]
    lng = [lng[j] for j in range(0,len(lng),1)]
    h = plt.plot(lng, lat, '.')
    plt.grid()

    return h


if __name__ == '__main__':
    ll_Praha = (50.0833, 14.4167)
    ll_Berk = (37.8734834, -122.2593292)
    ll_Berk3 = (37.8734834, -122.2593292-0.01)

    # PARAMETERS
    ll0 = ll_Praha
    lbl = 'testPraha'
    z = [0, 4]                   # zoom-level
    r = 500                 # radius
    #_______________

    print ll0

    # Setting up loger
    l_fmt = '%(asctime)s %(levelname)s: %(message)s'      # format
    l_dfmt = '%m/%d/%Y %I:%M:%S %p'                       # date format
    l_fname = 'err_'+lbl+'.log'                           # file name
    logging.basicConfig(filename=l_fname, format=l_fmt, datefmt=l_dfmt)

    circle = validator.circle(ll0, r)
    c = Crawler(latlng=ll0, label=lbl, zoom=z, validator=circle, root='../data', images=True)
    c.run()
    h = plotData(c.fname)
    plt.show()
    pass

