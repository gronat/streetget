from urllib import urlencode
import json
import re
import sys
import requests

# Headers for URL GET requests, can be used later to fool
# google servers
from numpy import random

headers = {
    'User-agent': 'custom browser'      # may be used later to fool server
}

class Panorama:
    pano_id = None
    meta = None
    time_meta = None
    url_spatial = None
    url_time = None

    def __init__(self, pano_id = None, latlng = None):
        if not pano_id and not latlng:
            raise ValueError('pano_id or latlng mus be given')


        self.pano_id = pano_id if pano_id else self.getPanoID(latlng)
        self.meta = self.getMeta()
        self.time_meta = self.getTimeMeta()


    def getSpatialNeighbours(self):
        """
        Reads metadata returned from getMeta() and extracts
        links of adjacent panoramas.
        :return: list - strings of adjacent panoId hashes
        """
        pano_ids = [];
        for x in self.meta['Links']:
            pano_ids.append(x['panoId'])

        return pano_ids


    def getTemporalNeighbours(self):
        """
        Extracts temporal panorama links from
        timemachine metadata.
        :return: list of tuples (pano_id, 'year, month')
        """
        aux = self.time_meta[1][0][5][1]  # interesting part of the meta list

        # Get timestamps of available timemachine
        tstamps = []
        for x in aux[8]:
            tstamps.append('%d, %d' % tuple(x[1]))  # year, month

        # Get corresponding panoID hashes
        pano_ids = ['' for x in range(len(tstamps))]  # empty string list alloc
        for j in range(1, len(tstamps) + 1):
            pano_ids[-j] = aux[3][0][-j][0][1]  # pano_id hash string

        return zip(pano_ids, tstamps)


    def getAllNeighbours(self):

        return self.getSpatialNeighbours() + [x for x, t in self.getTemporalNeighbours()]


    def getMeta(self):
        """
        Gets metadata for given panorama
        :param pano_id: string -  panoID hash
        :return: dictionary - data from returned JSON
        """
        url = 'https://cbks1.google.com/cbk'
        query = {
            'output':       'json',
            'v':            4,
            'cb_client':    'apiv3',
            'hl':           'en-US',
            'oe':           'utf-8',
            'dmz':          1,              # depth map uncompressed
            'pmz':          1,              # pano map  uncompressed
            'dm':           1,              # depth map
            'pm':           1,              # pano map
            'panoid':       self.pano_id    # panoID hash
        }

        msg = self.requestData(url, query, headers)
        try:
            return json.loads(msg)
        except Exception as e:
            print e
            pass

    def getTimeMeta(self):
        """
        Gets timemachne metadata for a given panorama.
        The crazy query string was reverse engineered by
        listening to the network trafic.
        :return: nested list from JSON
        """
        url = 'https://www.google.fr/maps/photometa/v1'
        query = {
            'authuser': 0,
            'hl': 'en',
            'pb':   '!1m1!1smaps_sv.tactile!2m2!1sen!2sfr!3m3!1m2!1e2!2s'
                    + self.pano_id + '!4m17!1e1!1e2!1e3!1e4!1e5!1e6'
                    '!1e8!4m1!1i48!5m1!1e1!5m1!1e2!6m1!1e1!6m1!1e2',
            'output': 'json'
        }

        msg = self.requestData(url, query, headers)      # .js file as string

        """
        Handle a content of the .js file retrieved form the server
        Here again - reverse engineerd. The js file contains
        nested arrays with some useful info. String is
        modified such that it can be loaded as JOSN.
        """
        # Trash the first line
        pattern  = r'.+\n(.+)'
        msg = re.match(pattern, msg).groups()[0]
        # Find [ or , followed by , and insert null in between
        pattern = r'([\[,])(?=,)'
        msg = re.sub(pattern, r'\1null', msg)
        # Load the JSON nested list
        data = json.loads(msg);

        return data


    def requestData(self, url, query, headers=None):
        """
        Sends GET URL request formed from base url, query string
        and headers. Returns whatever this request receives back.

        :param url: string - base URL
        :param query: dictionary - url qury paramteres as key-value
        :param headers: dictionary - header parameters as key-value
        :return: dictionary - data from returned JSON
        """
        # URL GET request
        query_str = urlencode(query).encode('ascii')
        u = requests.get(url + "?" + query_str, headers=headers)
        msg = u.text

        return msg





    def getPanoID(self, latlng):
        """
        Searches the closes panorama given the latlng and retuns its panoID hash
        :argument tuple - float latitude longitude
        :returns string - pano_id hash
        """
        # Base URL and headers
        url = 'https://geo0.ggpht.com/cbk'

        # Query parameters (reverse engineered by googling)
        query = {
            'cb_client':    'maps_sv.tactile',
            'authuser':     '0',
            'hl':           'en',
            'output':       'json',
            'll':           '%.6f,%.6f' % latlng,
        }

        msg = self.requestData(url, query, headers)
        data = json.loads(msg)

        return data['Location']['panoId'].encode('ascii')


    def __str__(self):
        s = ''
        s+= 'panoID %s\n' % self.pano_id
        s+= 'neoghbours:\n'
        for x in self.getSpatialNeighbours():
            s+= x.__str__() + '\n'
        for x,t in self.getTemporalNeighbours():
            s+= x.__str__() + ', ' + t.__str__() + '\n'

        return s


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



if __name__ == '__main__':
    runThreads()
    randomCrawl()



    pass

