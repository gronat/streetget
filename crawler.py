import threading
import os
from math import sqrt

import dill
import json
import logging
import matplotlib.pyplot as plt
from panorama import Panorama
from database2 import Database
from time import sleep



# Setting up loger
l_fmt = '%(asctime)s %(levelname)s: %(message)s'      # format
l_dfmt = '%m/%d/%Y %I:%M:%S %p'                       # date format
l_fname = 'err_panorama.log'                          # file name
logging.basicConfig(filename=l_fname, format=l_fmt, datefmt=l_dfmt)
loger = logging.getLogger('crawler')
loger.setLevel(logging.DEBUG)


class Crawler:
    t_save = 600                # backup db every 10min
    n_thr = 4
    threads = n_thr * [None]    # thread vector allocation
    db = Database()
    x = []
    y = []

    def __init__(self, latlng=None, pano_id=None, label='myCity', root='myData', validator=None):
        if not latlng and not pano_id:
            raise ValueError('start point (latlng or pano_id) not given')

        loger.info('___ Crawler starting ___')

        self.dir = os.path.join(root, label)
        self.fname = os.path.join(root, label, 'db.pickle')
        self.fname_bck = self.fname + '.bck'
        self.start_id = pano_id
        self.start_latlng = latlng
        self.exit_flag = False                  # flag for signaling threads
        self.inArea = validator

        if not os.path.exists(self.dir):        # new dataset
            os.makedirs(self.dir)
        else:
            if not self.resume(self.fname):     # restores existing database
                self.resume(self.fname_bck)     # roll back to backup

    def resume(self, fname):
        """
        Resumes existing serialized database.
        """
        if not os.path.isfile(fname):
            loger.warning('No file: '+ fname)
            return
        loger.info('Resuming db from ' + fname)

        try:
            with open(self.fname) as f:
                db = dill.load(f)
            if not db.processing == 0:          # integrity check
                raise ImportError()
            self.db = db
            loger.info('db resumed')
        except ImportError:
            loger.error(
                'db corrupted: q unfinished jobs %d' % (
                    self.db.processing
                )
            )
            return False
        except Exception as e:
            loger.error('db resume failed:' +
                            type(e).__name__ +
                            str(e)
                        )
            return False

        return True


    def save(self, fname):
        """
        Saves existing database using the dill package.
        Notice that pickle package can't handle objects
        with mutex lock. Hence, dill is used instead of pickle
        :return:
        """
        loger.info('Saving db')
        if not self.db.processing == 0:
                loger.error(
                    'db corrupted: q unfinished jobs %d' %
                    (
                        self.db.processing
                    )
                )
                return False

        with open(fname, 'wb') as f:
                dill.dump(self.db, f)
                loger.info('db saved to ' + fname)
                return True

    def clean(self):
        """
        Cleans before exit:
        Let the threads finish jobs and save the database.
        """
        loger.debug('Cleaning')
        self.stopThreads()
        self.save(self.fname)

    def backup(self):
        loger.debug('Backup')
        self.stopThreads()
        self.save(self.fname)
        self.save(self.fname_bck)
        self.startThreads()

    def printStatus(self):
        """
        Prints some info about current state of downloading.
        """
        dt = 2
        N = 0
        avg = 0
        while True:
            N += 1
            n0 = self.db.dsize()
            sleep(dt)
            n1 = self.db.dsize()
            v = (n1 - n0) /dt*60
            avg += (v - avg)/N
            print 'db-sz %05d\t q-sz %d\t alive: %d \t %d p/m\t avg: %.1f' % (
                n1,
                self.db.qsize(),
                threading.active_count(),
                v,
                avg,
            )

    def threader(self):
        zoom = 1
        while not self.exit_flag:
            pano_id = self.db.dequeue()
            p = Panorama(pano_id)
            self.visitPano(p)
            self.savePano(p, zoom)
            self.db.task_done()

    def visitPano(self, p):
        """
        Visits panorama, extracts meta data and adds
        info about panorama into database. Neighbour
        panoramas are added to the database queue.
        """

        if not p.isValid() or not self.inArea(p):
            return

        gps = p.getGPS()
        date = p.getDate()
        neighbours = p.getAllNeighbours()
        data = {'latlng': gps, 'date': date}

        self.x.append(gps[0])
        self.y.append(gps[1])

        self.db.add(p.pano_id, data)      # update visited
        for n in neighbours:
            self.db.enqueue(n)          # update queue


    def savePano(self, p, zoom):
        """
        Saves panorama image at given zoom-level and its
        metadata. Directory name corresponds to the first
        two characters of the pano_id hash.
        :param p: Panorama - object
        :param zoom: int - zoom level
        """
        if not p or not p.isValid():
            return
        fdir = p.pano_id[0:2]
        fname = p.pano_id
        fbase = os.path.join(self.dir, fdir, fname)

        p.saveMeta(fbase + '_meta.json')
        p.saveTimeMeta(fbase + '_time_meta.json')
        p.saveImg(fbase + '_zoom_' + str(zoom) + '.jgp')

    def startThreads(self):
        self.exit_flag = False
        # Starting threads
        for j in range(self.n_thr):
            t = threading.Thread(target=self.threader)
            t.start()
            self.threads[j] = t
        loger.debug('Threads started')

    def stopThreads(self):
        self.exit_flag = True
        # Stopping threads
        for t in self.threads:
            t.join()
        loger.debug('Threads stopped')

    def backupPeriodic(self):
        while True:
            sleep(self.t_save)
            self.backup()

    def run(self):
        """
        Performs parallel BFS crawling. Main threads perform crawling via BFS.
        There are two auxiliary threads. Former manages periodic database backup
        while latter periodically prints state of downloading. Saving the current
        state at KeyboardInterrupt is handled.
        """
        # Threads for BFS
        self.startThreads()

        # Thread for periodic db backup
        t = threading.Thread(target=self.backupPeriodic)
        t.daemon = True
        t.start()

        # Thread that prints a progress
        t = threading.Thread(target=self.printStatus)
        t.daemon = True
        t.start()

        try:
            # Enqueueing the first job
            p = Panorama(self.start_id, self.start_latlng)
            self.db.enqueue(p.pano_id)

            while not self.db.q.unfinished_tasks == 0:
                sleep(1)
            self.db.join()
        except (KeyboardInterrupt, SystemExit):
            loger.debug('*** handling keyboard or system interrupt')
            self.clean()
            raise

        self.save(self.fname)
        print('All panorama collected')


def plotData(fname):
    with open(fname) as f:
        db = pickle.load(f)
    d = db.d
    lat = [d[key]['latlng'][0] for key in d]
    lng = [d[key]['latlng'][1] for key in d]
    lat = [lat[j] for j in range(0,len(lat),100)]
    lng = [lng[j] for j in range(0,len(lng),100)]
    h = plt.plot(lng, lat, '.')
    return h

def validator_L2(latlng_0, dst):

    def isClose(p):
        ltln = p.getGPS()
        d = sqrt((latlng_0[0] - ltln[0])**2 + (latlng_0[1] - ltln[1])**2)
        return d<dst

    return isClose


if __name__ == '__main__':
    pass
    latlng_0 = (50, 14.41)
    l2 = validator_L2((50, 14.41), 0.001)
    #plotData(fname)
    c = Crawler(latlng=latlng_0, label='test', validator=l2)
    c.run()
    del c
    pass

