import threading
from time import sleep

from panorama import Panorama
from database import Database


class Crawler:
    def __init__(self):
        self.db = Database()
        self.lock = threading.Lock()

    def threader(self):
        while True:
            self.visitPano()

    def visitPano(self):
        with self.lock:
            if not self.db.qempty():
                pano_id = self.db.dequeue()
            else:
                return

        p = Panorama(pano_id)
        gps = p.getGPS()
        date = p.getDate()
        neighbours = p.getAllNeighbours()
        data = {'latlng': gps, 'date': date}


        with self.lock:
            self.db.add(pano_id, data)

            for x in neighbours:
                if not self.db.has(x):
                    self.db.enqueue(x)
            #print 'Visited %s \t %d-%d \t %.6f %.6f' % ((pano_id,)+date+gps)


    def run(self):
        p = Panorama(latlng=(50, 14.41))
        self.db.enqueue(p.pano_id)

        for j in range(32):
            t = threading.Thread(target=self.threader)
            t.daemon = True
            t.start()

        while True:
            n0 = self.db.dsize()
            sleep(5)
            n1 = self.db.dsize()
            print '%0.1f pano/sec' % ((n1-n0)/5.0,)



if __name__ == '__main__':
    c = Crawler()
    c.run()