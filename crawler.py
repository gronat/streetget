import threading
import sys

from time import sleep
import os
import dill as pickle
from panorama import Panorama
from database2 import Database
import logging

logging.basicConfig(filename='err_panorama.log')
loger = logging.getLogger('crawler')
loger.setLevel(logging.DEBUG)

class Crawler:
    def __init__(self, latlng=None, pano_id=None, label='myCity', root=r'./myData'):
        if not latlng and not pano_id:
            raise ValueError('start point latlng or pano_id not given')


        self.dir = os.path.join(root, label)
        self.fname = os.path.join(root, label, 'db.pickle')
        self.start_id = pano_id
        self.start_latlng = latlng
        self.db = Database()
        self.x = []
        self.y = []
        self.exit_flag = False
        self.t_save = 10       # backup db every 5min
        self.n_thr = 32
        self.threads = self.n_thr*[None]

        if not os.path.exists(self.dir):
            os.makedirs(self.dir)
        else:
            self.resume()



    def resume(self):
        """
        Resumes existing serialized database.
        """
        if not os.path.isfile(self.fname):
            loger.warning('No file: '+ self.fname)
            return
        loger.info('Resuming db')
        with open(self.fname) as f:
            try:
                db = pickle.load(f)
                if db.processing > 0:
                    raise ImportError()
            except ImportError:
                loger.error('db corrupted: q contains unfinished jobs')
            except Exception as e:
                loger.error('db resume failed:' + str(e))
            else:
                self.db = db
                loger.info('db resumed')


    def save(self):
        """
        Saves existing database using dill package.
        Notice that pickle package can't handle objects
        with mutex lock. Hence, dill is used instead of pickle
        :return:
        """
        with open(self.fname,'wb') as f:
            loger.info('Saving db')
            pickle.dump(self.db, f)
            loger.info('db saved')
            if self.db.processing >0:
                loger.error('db integrity corrupted, proc > 0')

    def clean(self):
        loger.debug('Cleaning')
        self.stopThreads()
        self.save()

    def backup(self):
        loger.debug('Backup')
        self.stopThreads()
        self.save()
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
            print 'db-size %05d\t q-size %d\t %d p/min\t\t avg: %.1f' % (
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

        # Enqueueing the first job
        p = Panorama(self.start_id, self.start_latlng)
        self.db.enqueue(p.pano_id)

        try:
            while self.db.q.unfinished_tasks > 0:
                sleep(1)
            self.db.q.join()
        except (KeyboardInterrupt, SystemExit):
            self.clean()
        except:
            pass

        print('All panporama collected')




if __name__ == '__main__':
    c = Crawler(latlng=(50, 14.41))
    c.run()

