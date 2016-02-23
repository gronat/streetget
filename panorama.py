#
from Queue import Queue
from io import BytesIO
from itertools import product
from urllib import urlencode
import threading
import json
import re
import requests
import sys
from PIL import Image
from matplotlib.pyplot import plot
from numpy import array


# Headers for URL GET requests, can be used later to fool
# google servers
import time



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

    def getPanoID(self, latlng):
        """
        Searches the closest panorama given the latlng and retuns its panoID hash
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

    def getSpatialNeighbours(self):
        """
        Reads metadata returned from getMeta() and extracts
        links of adjacent panoramas.
        :return: list - strings of adjacent panoId hashes
        """
        pano_ids = []
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
        """
        Returns a list of both spatial and temporal
        panorama neighbours.
        :return: list  - panoID ahshes
        """
        return self.getSpatialNeighbours() + [x for x, t in self.getTemporalNeighbours()]


    def getImage(self, zoom = 5, n_threads = 16):
        tw, th = self.numTiles(zoom)
        tiles = tw*th*[None]

        def worker(q):
            while True:
                x,y = q.get()
                tiles[y+th*x] = self.getTile(x,y,zoom)
                q.task_done()

        # Starting threads
        q = Queue()

        for x in range(n_threads):
            t = threading.Thread(target=worker, args=(q,))
            t.setDaemon(True)
            t.start()

        # Queueing jobs
        for xy in product(range(tw), range(th)):
            q.put(xy)

        q.join()            # all jobs finished

        # Stitching tiles together
        pano = Image.new('RGB',(512*tw, 512*th))
        grid = [xy for xy in product(range(tw), range(th))]

        for x,y in grid:
            pano.paste(tiles[y+th*x], (512*x, 512*y))

        box = self.cropSize(zoom)
        return pano.crop(box)

    def getTile(self, x, y, zoom = 5):
        url ='https://geo2.ggpht.com/cbk'
        query = {
                    'output':   'tile',
                    'zoom':     zoom,
                    'x':        x,
                    'y':        y,
                    'panoid':   self.pano_id
                }

        msg = self.requestData(url,query, headers=headers)
        file = BytesIO(msg)
        img = Image.open(file)
        return img

    def numTiles(self, zoom):
        """
        Number of image tile for given zoom level.
        :param zoom: int [0-5] - panorama zoom level
        :return: tuple - #of tiles (horizontally, vertically)
        """
        # Switch
        return [
            (1,1),
            (2,1),
            (4,2),
            (7,4),
            (13,7),
            (26, 13)
        ][zoom]


    def cropSize(self, zoom):
        """
        Gives corners of the panorama image crop for given zoom-level.
        Panoramas are composed of 512x512 tiles. After a stitching at some
        zoom levels the bottom is padded by black or the right most edge of
        panorama overlaps the left edge (pano image wraps itself). Hence a
        crop is necessary to be done. The values were reverse-engineered.
        :param zoom: int [0-5] - current zoom level
        :return: tuple - bottom right corner for crop
        """
        return [
            (0, 0, 417, 208),
            (0, 0, 833, 416),
            (0, 0, 1665, 832),
            (0, 0, 3329, 1664),
            (0, 0, 6656, 3328),
            (0, 0, 13312, 6656)
        ][zoom]

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
        :param query: dictionary - url query paramteres as key-value
        :param headers: dictionary - header parameters as key-value
        :return: dictionary - data from returned JSON
        """
        # URL GET request
        query_str = urlencode(query).encode('ascii')
        u = requests.get(url + "?" + query_str, headers=headers)
        msg = u.content
        #print 'req: '+ url + "?" + query_str
        return msg

    def utilGetNumTiles(self, zoom):
        maxx = 0
        maxy = 0
        for x,y in product(range(30), range(20)):
            img = self.getTile(x,y,zoom)
            h = img.histogram()
            if not sum(h[1:]) == 0:
                maxx = x if x>maxx else maxx
                maxy = y if y>maxy else maxy
        print 'Zoom %d: #tiles - horizontally %d   vertically %d' % (zoom, maxx+1, maxy+1)
        return (maxx, maxy)

    def utilGetCrop(self, pano):
        w,h = pano.size
        _, _, col, row = pano.getbbox()
        a = array(pano.rotate(90).convert('L')).astype('int16')

        x = a[0]
        j = w
        val = sys.maxint
        aux = []
        for y in a[-1:int(w*.7):-1]:
            v = sum(abs(x-y))
            aux.append(v)
            if v<val:
                val = v
                col = j
            j -= 1

        print  "Original size: \t\t\t%d \t%d" % (w, h)
        print  "Estimated crop size: \t%d \t%d" % (col, row)
        print '_______________________________________'





    def __str__(self):
        s = ''
        s+= 'panoID %s\n' % self.pano_id
        s+= 'neoghbours:\n'
        for x in self.getSpatialNeighbours():
            s+= x.__str__() + '\n'
        for x,t in self.getTemporalNeighbours():
            s+= x.__str__() + ', ' + t.__str__() + '\n'

        return s