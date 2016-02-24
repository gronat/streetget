import threading
import sys

from time import sleep
import os
import dill as pickle
from pip.utils import logging
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
        self.threads = []
        self.t_save = 10       # backup db every 5min

        if not os.path.exists(self.dir):
            os.makedirs(self.dir)
        else:
            self.resume()



    def resume(self):
        """
        Resumes existing serialized database.
        """
        try:
            if os.path.isfile(self.fname):
                with open(self.fname) as f:
                    loger.info('Resuming db')
                    db = pickle.load(f)
                self.db = db
                loger.info('db resumed')

        except:
            loger.error('resuming db failed')


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

    def clean(self):
        loger.debug('Waiting for threads to finish')
        self.exit_flag = True
        for t in self.threads:
            t.join()
        loger.debug('All threads finished')

    def printStatus(self):
        """
        Prints some info about current state of downloading.
        """
        while True:
            dt = 2
            n0 = self.db.dsize()
            sleep(dt)
            n1 = self.db.dsize()
            with self.db.q.mutex:
                print 'size %05d \t %0.1f pano/min' % (n1, (n1 - n0) /dt*60,)

    def saver(self):
        while True:
            sleep(self.t_save)
            self.save()

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

        # with self.db.q.mutex:
        #     print 'Visited %s \t %d-%d \t %.6f %.6f' % ((pano_id,)+date+gps)

    def run(self):

        # Starting threads
        for j in range(64):
            t = threading.Thread(target=self.threader)
            t.start()
            self.threads.append(t)

        # Thread that prints a progress
        t = threading.Thread(target=self.printStatus)
        t.daemon = True
        t.start()

        # Thread that saves db every t_save sec
        t = threading.Thread(target=self.saver)
        t.daemon = True
        t.start()

        # Enqueueing the first job
        p = Panorama(self.start_id, self.start_latlng)
        self.db.enqueue(p.pano_id)

        try:
            while self.db.q.unfinished_tasks > 0:
                sleep(1)
        except (KeyboardInterrupt, SystemExit):
            self.clean()
        except:
            pass




if __name__ == '__main__':
    c = Crawler(latlng=(50, 14.41))
    c.run()

