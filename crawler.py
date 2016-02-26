import threading
import sys
import atexit

from time import sleep
import os
import dill as pickle
from panorama import Panorama
from database2 import Database
import logging
import matplotlib.pyplot as plt

# Setting up loger
l_fmt = '%(asctime)s %(levelname)s: %(message)s'      # format
l_dfmt = '%m/%d/%Y %I:%M:%S %p'                       # date format
l_fname = 'err_panorama.log'                          # file name
logging.basicConfig(filename=l_fname, format=l_fmt, datefmt=l_dfmt)
loger = logging.getLogger('crawler')
loger.setLevel(logging.DEBUG)


class Crawler:
    t_save = 10  # backup db every 5min
    n_thr = 8
    threads = n_thr * [None]
    db = Database()
    x = []
    y = []

    def __init__(self, latlng=None, pano_id=None, label='myCity', root=r'./myData'):
        if not latlng and not pano_id:
            raise ValueError('start point latlng or pano_id not given')

        loger.info('___ Crawler starting ___')

        self.dir = os.path.join(root, label)
        self.fname = os.path.join(root, label, 'db.pickle')
        self.fname_bck = self.fname + '.bck'
        self.start_id = pano_id
        self.start_latlng = latlng
        self.exit_flag = False


        if not os.path.exists(self.dir):
            os.makedirs(self.dir)
        else:
            if not self.resume(self.fname):     # restore database
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
                db = pickle.load(f)
            if not db.processing == 0:
                raise ImportError()
            self.db = db
            loger.info('db resumed')
            return True
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

    def save(self, fname):
        """
        Saves existing database using dill package.
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
                pickle.dump(self.db, f)
                loger.info('db saved to ' + fname)
                return True

        loger.error('db unable to save!')
        raise IOError('db unable to save!')


    def clean(self):
        """
        Cleans before exit:
        let threads finish job and save databas.
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
            print 'db-size %05d\t q-size %d\t %d p/min\t avg: %.1f' % (
                n1,
                self.db.qsize(),
                v,
                avg,
            )

    def threader(self):
        while not self.exit_flag:
            pano_id = self.db.dequeue()
            self.visitPano(pano_id)
            self.db.task_done()

    def visitPano(self, pano_id):
        """
        Visits panorama, extracts meta data and adds
        info about panorama into database. Neighbour
        panoramas are added to the database queue.
        """
        if not pano_id:
            return
        p = Panorama(pano_id)
        gps = p.getGPS()
        date = p.getDate()
        neighbours = p.getAllNeighbours()
        data = {'latlng': gps, 'date': date}

        self.x.append(gps[0])
        self.y.append(gps[1])

        self.db.add(pano_id, data)
        for n in neighbours:
            self.db.enqueue(n)


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

if __name__ == '__main__':
    pass
    fname = './db.pickle'
    p = Panorama('Np6NPQCCg3ix9w_BIWqfhw')
    #plotData(fname)
    c = Crawler(latlng=(50, 14.41))
    c.run()
    pass

