from queue import Queue
from io import BytesIO
from io import StringIO
from itertools import product
from urllib import urlencode
from struct import Struct
import threading
import json
import re
import requests
import sys, os
import logging
import numpy as np
from PIL import Image
from numpy import array
from street_exceptions import NoSpatialNeighbours, NoTemporalNeighbours
from street_exceptions import NoCollectLinks, CustomPanoramaNotSupported
from street_exceptions import GoogleUpdating
import matplotlib as mpl
mpl.use('Agg')                  # avoid Tk window
import matplotlib.pyplot as plt
# NOTE: Tkinter a has problem with multithread. Matplotlib directive use('Agg')
# turns on non-interactive backend and avoids displaying Tk window.

# Headers for URL GET requests, can be used in the future to fool google servers:
headers = {
    'User-agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:42.0) Gecko/20100101 Firefox/42.0'      # may be used later to fool server
}

if __name__ == '__main__':
    loger = logging.getLogger('panorama')
    loger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    loger.addHandler(ch)
else:
    loger = logging.getLogger('panorama')
    loger.setLevel(logging.WARNING)

class Panorama:
    pano_id = None
    meta = None
    time_meta = None
    depthdata = None
    depthmap = None

    def __init__(self, pano_id=None, latlng=None, radius=15):
        if not pano_id and not latlng:
            return;

        self.pano_id = pano_id if pano_id else self.getPanoID(latlng, radius)
        if not self.pano_id:    #pano_id not found
            return

        self.meta = self.getMeta()
        self.time_meta = self.getTimeMeta()

    def _pano_msg(self):
        '''
        Serves for basic message in logger messages.
        '''
        return '%s %.6f %.6f\n' % (self.pano_id, self.getGPS()[0], self.getGPS()[1])

    def getPanoID(self, latlng, radius=15):
        """
        Searches the closest panorama given the latlng and retuns its panoID hash
        :param: lalng tuple - float latitude longitude
        :param: radius - search radius in meters
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
            'radius':       radius,
        }

        msg = self.requestData(url, query, headers)
        data = json.loads(msg)
        if len(data) is 0:
            return None
        return data['Location']['panoId'].encode('ascii')

    def isValid(self):
        """ Panorama without metadata is not valid """
        return self.meta is not None and len(self.meta) > 0

    def isCustom(self):
        """ Is it custom or google panorama? """
        if not self.isValid():
            return False
        aux = re.match(r'.*Google.*', self.meta['Data']['copyright'])
        return aux is None

    def hasZoom(self, zoom):
        """
        Checks if zoom level is available.
        :param zoom: int [0-5]
        :return: boolean
        """
        if not self.isValid():
            return False
        z = int(self.meta['Location']['zoomLevels'])
        return z >= zoom

    def getSpatialNeighbours(self):
        """
        Reads metadata returned from getMeta() and extracts
        links of adjacent panoramas.
        :return: list - strings of adjacent panoId hashes
        """
        pano_ids = []
        try:
            pano_ids = self._collectSpatialLinks()
        except NoSpatialNeighbours:
            loger.warning(self._pano_msg() + 'Spatial neighbours not found.')
        except Exception:
            loger.exception()
        return pano_ids

    def _collectSpatialLinks(self):
        try:
            pano_ids = []
            for x in self.meta['Links']:
                pano_ids.append(x['panoId'])
        except:
            raise NoSpatialNeighbours
        return pano_ids

    def getTemporalNeighbours(self):
        """
        Extracts temporal panorama links from
        timemachine metadata.
        :return: list of tuples (pano_id, (year, month))
        """
        #TODO: tt = (None, None)... return tt, following the same pattern
        # as e.g. getGPS
        neighbours = None
        try:
            aux = self._extractTemporalLinks()
            tstamps, pano_ids = self._collectTemporalLinks(aux)
            neighbours = zip(pano_ids, tstamps)
        except NoTemporalNeighbours:
            loger.warning(self._pano_msg() + 'Temporal neighbours not found.')
        except NoCollectLinks:
            loger.warning(self._pano_msg() + 'Can not connect links from metadata.')
        except Exception:
            loger.exception(self._pano_msg())
        return neighbours

    def _extractTemporalLinks(self):
        try:
            aux = self.time_meta[1][0][5][1]  # interesting part of the meta list
            return aux
        except:
            raise NoTemporalNeighbours('Extracting links.')


    def _collectTemporalLinks(self, aux):
        try:
            # - Get available panoID hashes that are contained in meta -
            # Sometimes the pano hash item is empty
            pano_ids=[]
            for j in range(0, len(aux[3][0])):
                if len(aux[3][0][j]) == 0:          # ...this looks ugly, should be removed
                    continue        # empty item
                pano_ids.append(aux[3][0][-j-1][0][1])  # pano_id hash string

            # - Get timestamps of available time machine panoramas -
            # Timestamsps are not always available
            # Timestamps used to be assighent tho the last n pano_ids, hence the indexes in idx=aux[8][0]
            # corresponded to the actual panorama in aux[3][0][idx]. The idx started always at the end of the array
            # aux[3][0]
            # In 2018, Google changed the policy. Indexes are not valid, timestamps corresponds to the panoramahashes
            # as folows:
            # pano_id [3][0][idx] <==> timestamp aux[8][0][-idx-1]
            tstamps = []
            if len(aux) > 9 and aux[8] is not None:
                for x in aux[8]:
                    tstamps.append(tuple(x[1]))  # year, month

            # Consider only temporal links with the time stamps
            len_ids = len(pano_ids)
            len_tst = len(tstamps)

            if len_tst == 0 or len_ids == 0:
                raise NoTemporalNeighbours('Processing temporal metadata.')

            if len_tst > 0:
                pano_ids = pano_ids[:(len_ids-len_tst)]
            else:
                tstamps = len_ids*[(None, None)]
            tstamps = tstamps[::-1]                 # last tstamp coorresponds to the first pano_id hash

            return tstamps, pano_ids
        except NoTemporalNeighbours:
            raise
        except:
            raise NoCollectLinks('Processing temporal metadata.')


    def getGPS(self):
        ll = (None, None)
        try:
            lat = self.meta['Location']['lat']
            lng = self.meta['Location']['lng']
            ll = (float(lat), float(lng))
        except Exception as e:
            msg = '%s no GPS found - %s: %s' % (
                self.pano_id, type(e).__name__, str(e)
            )
            loger.error(msg)
        return ll

    def getDate(self):
        """
        :return: tuple of two integers (year, month)
        """
        dd = (None, None)
        try:
            dates = self.meta['Data']['image_date']
            ptrn = r'(\d+)-\s*(\d+)'
            m = re.match(ptrn, dates)
            dd = (int(m.groups()[0]), int(m.groups()[1]))
        except Exception:
            loger.error(self._pano_msg())
            loger.exception()
        return dd

    def getAllNeighbours(self):
        """
        Returns a list of both spatial and temporal
        panorama neighbours.
        :return: list  - panoID hashes
        """
        sn = self.getSpatialNeighbours()
        tn = self.getTemporalNeighbours()
        if not tn and not sn:
            return []                           # no neighbours at all
        elif tn and sn:
            return (sn + [x for x,t in tn])     # both temporal and spatial
        elif sn:
            return sn                           # spatial neighbours only
        else:
            return [x for x,t in tn]            # temporal neighbours only

    def getImage(self, zoom=5, n_threads=16):
        """
        Gets panorama image at given zoom level. The image
        consists of image tiles that are fetched and stitched
        together. The resulting image is cropped in order to
        form a spherical panorama.
        :param zoom:
        :param n_threads:
        :return: Image - panorama at given zoom level
        """
        if self.isCustom():
            raise NotImplementedError('Custom panorama is not implemented')

        if not self.hasZoom(zoom):
            print 'Panorama %s has no zoom level %d' % (self.pano_id, zoom)
            return None

        tw, th = self.numTiles(zoom)
        tiles = tw*th*[None]

        n_threads = min(n_threads, tw*th)

        sentinel = object()
        global terminate
        terminate = False
        def worker(q):
            global terminate
            while True:
                item = q.get()
                if item is sentinel:
                    q.task_done()
                    break
                # Recieve terminate signal
                if terminate:
                    q.task_done()
                    continue

                # Get tile
                x,y = item
                tile = self.getTile(x, y, zoom)
                # Send terminate signal if error
                if tile is None:
                    terminate = True
                # Save tile
                tiles[y + th * x] = tile
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
        # Queueing sentinels to exit the threads
        for _ in range(n_threads):
            q.put(sentinel)
        q.join()            # all jobs finished

        # Stitching tiles together
        pano = Image.new('RGB',(512*tw, 512*th))
        grid = [xy for xy in product(range(tw), range(th))]

        for x,y in grid:
            try:
                pano.paste(tiles[y+th*x], (512*x, 512*y))
            except Exception as e:
                msg = self._pano_msg() + 'Error in tile stitching.'
                loger.error(msg)
                print msg + '\nCheck this panorama at http://maps.google.com'
                return None

        box = self.cropSize(zoom)
        return pano.crop(box)

    def getTile(self, x, y, zoom=5):
        """
        Gets panorama image tile 512x512 at position (x,y)
        :param x: int - tile coordinate horizontal
        :param y: int - tile coordinate vertical
        :param zoom: int [0-5] - zoom level
        :return: Image - panorama tile
        """
        url ='https://geo2.ggpht.com/cbk'
        query = {
                    'output':   'tile',
                    'zoom':     zoom,
                    'x':        x,
                    'y':        y,
                    'panoid':   self.pano_id
                }

        msg = self.requestData(url,query, headers=headers)
        try:
            file = BytesIO(msg)
            #file = StringIO(msg)
            img = Image.open(file)
        except:
            return None

        return img

    def getDepthData(self):
        if 'model' not in self.meta.keys() or \
           'depth_map' not in self.meta['model'].keys():
            msg = 'Panorama has no depth in meta.\n%s' % (self.pano_id)
            loger.warning(msg)
            print msg
            self.depthdata = -1
            return self.depthdata

        encoded = self.meta['model']['depth_map']
        # Decode
        encoded += '=' * (len(encoded) % 4)
        encoded = encoded.replace('-', '+').replace('_', '/')
        data = encoded.decode('base64').decode('zip')       # base64 encoded

        # Read header
        hsize = ord(data[0])                # header size in bytes
        fmt = Struct('< x 3H B')            # little endian, padding byte, 3x unsigned short int, unsigned char
        n_planes, width, height, offset = fmt.unpack(data[:hsize])

        # Read plane labels
        n = width * height
        fmt = Struct('%dB' % n)
        lbls = fmt.unpack(data[offset:offset+fmt.size])
        offset += fmt.size

        # Read planes
        fmt = Struct('< 4f')                # little endian, 4 signed floats
        planes = []
        for i in xrange(n_planes):
            unpacked = fmt.unpack(data[offset:offset+fmt.size])
            planes.append((unpacked[:3], unpacked[3]))
            offset += fmt.size

        self.depthdata = (width, height), lbls, planes
        return self.depthdata
    
    def getDepthImg(self, zoom=None):
        """
        Computes depth image from depth data given by
        getDepthData(). Default image size is 5120x256.
        If zoom is given, the the image is resized to
        correspond to the panorama image size at given
        zoom level.
        :param zoom: int [0-5], default None
        :return img - PIL Image object
        """
        if not self.depthdata:
            self.getDepthData()

        if self.depthdata == -1:
            return None

        size, lbls, planes = self.depthdata
        w, h = size
        pi = np.pi

        # Rays from camera center in spherical coordinates
        y, x = np.indices((h, w))           # grid of coordinates
        offset = pi/2                       # no idea why not pi,
        yaw = (w-1 - x) * 2*pi / (w-1) + offset
        pitch = (h-1 - y) * pi / (h-1)      # 0 down, pi/2 horizontal, pi up

        # Rays from spherical to cartesian
        v = np.array([
            np.sin(pitch) * np.cos(yaw),
            np.sin(pitch) * np.sin(yaw),
            np.cos(pitch)
        ])
        v = v.transpose(1, 2, 0)

        # w x h x 3 normal, resp. w x h x 1 distance
        n = np.array([planes[i][0] for i in lbls]).reshape((h, w, 3))
        d = np.array([planes[i][1] for i in lbls]).reshape((h, w))
        d[d == 0] = np.nan

        # distance from camera centetr, ray inersection with plane
        self.depthmap = d / np.abs(np.sum(v * n, axis=2))

        try:
            plt.imshow(self.depthmap)
        except Exception as e:
            loger.error(self._pano_msg() + 'Can not export depth as an image.')
            return Image.new('RGB', (1,1))

        buf = BytesIO()
        plt.imsave(buf, self.depthmap)
        buf.seek(0)
        img = Image.open(buf)

        if zoom:
            _, _, w, h = self.cropSize(zoom)
            img = img.resize((w,h), Image.NEAREST)
        return img

    def saveDepthData(self, fname):
        """
        Saves depth data as JSON in following format:
        data[0] - tuple (width w, height h)
        data[1] - tuple w x h plane labels
        data[2] - tuple of the length of # planes
                  item: ((n_0, n_1, n_2), d) where n_i is
                  a component of a plane normal vector and d
                  is its distance from the camera center.

        Google depth map is represented as a set of 3D planes.
        Hence data[0], data[1] represent a 2D matrix which
        corresponds to a spherical panorama. Each item of the
        matrix is a label of a plane. data[2] represents
        the plane parameters - normal vector and distance.

        :param fname - string, filename
        """
        if not self.depthdata:
            self.getDepthData()

        if self.depthdata == -1:
            msg = 'No depth data saved for panorama (data unavailable):\n%s' % (self.pano_id,)
            loger.warning(msg)
            return

        with open(fname, 'w') as f:
            json.dump(self.depthdata, f)

    def saveDepthImage(self, fname, zoom=None):
        """
        Saves the corresponding depth mpa image using the
        depth map data from getDepthData(). Default image size
        is 512x256. If zoom is given, the the image is resized
        to correspond to the panorama image size at given zoom level.

        :param fname: string file name
        :param zoom: int [0-5], default None
        """
        if not self.depthdata:
            self.getDepthData()

        if self.depthdata == -1:
            msg = 'No depth image saved for panorama (data unavailable):\n%s' % (self.pano_id,)
            loger.warning(msg)
            return

        img = self.getDepthImg(zoom)
        with open(fname, 'w') as f:
            img.save(f, 'JPEG')


    def numTiles(self, zoom):
        """
        Number of image tile for given zoom level. Reverse
        engineered using the 'utilGetNumTiles()' method
        :param zoom: int [0-5] - panorama zoom level
        :return: tuple - #of tiles (horizontally, vertically)
        """
        # Switch
        return [
            (1, 1),
            (2, 1),
            (4, 2),
            (7, 4),
            (13, 7),
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
        :return: tuple - a crop box, top left, btm right corners
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
        Gets raw metadata of the panorama.
        :return: dictionary - data from returned JSON
        """
        if not self.pano_id:
            return None

        url = 'https://cbks1.google.com/cbk'
        query = {
            'output':       'json',
            'v':            4,
            'cb_client':    'apiv3',
            'hl':           'en-US',
            'oe':           'utf-8',
            'dmz':          0,              # depth map uncompressed
            'pmz':          0,              # pano map  uncompressed
            'dm':           1,              # depth map
            'pm':           0,              # pano map
            'panoid':       self.pano_id    # panoID hash
        }

        #TODO: process uncompressed depth. Is it the same as compressed?
        #TODO: what is pano map and how to use it?

        msg = self.requestData(url, query, headers)
        if not msg:
            return None

        jsons = None
        try:
            jsons = json.loads(msg)
        except Exception as e:
            loger.warn(self._pano_msg() + 'No met JSON recieved.\n' + msg)

        return jsons

    def getTimeMeta(self):
        """
        Gets raw timemachne metadata the panorama.
        The crazy 'query' string was reverse engineered by
        listening to the network trafic.
        :return: nested list from JSON
        """
        if not self.pano_id:
            return None

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
        if not msg:
            return None

        # Handle a content of the .js file retrieved form the server
        # Here again - reverse engineered. The js file contains
        # nested arrays with some useful info. String is
        # modified such that it can be loaded as JOSN.

        # Trash the first line
        pattern  = r'.+\n(.+)'
        msg = re.match(pattern, msg).groups()[0]
        # Find '[' or ',' followed by ',' and insert 'null' in between
        pattern = r'([\[,])(?=,)'
        msg = re.sub(pattern, r'\1null', msg)

        data = None
        try:
            # Load the JSON nested list
            data = json.loads(msg);
        except Exception as e:
            loger.warn(self._pano_msg() + 'No temporal meta JSON recieved.\n' + msg)

        return data

    def saveMeta(self, fname):
        """
        Saves meta data as JSON
        :param fname: string - filename
        """
        with open(fname, 'w') as f:
            json.dump(self.meta, f)

    def saveTimeMeta(self, fname):
        """
        Saves timemachine meta data as JSON
        :param fname: string - filename
        """
        with open(fname, 'w') as f:
            json.dump(self.time_meta, f)

    def saveImage(self, fname, zoom=5, n_threads=16):
        """
        Fetches panorama image at given zoom-level
        and saves as JPEG.
        :param fname: string - filename
        :param zoom: int [0-5] - zoom-level
        """
        img = self.getImage(zoom, n_threads)
        try:
            img.save(fname, 'JPEG')
        except Exception as e:
            loger.error(self._pano_msg() + 'Panorama image corrupted.')

    def requestData(self, url, query, headers=None):
        """
        Sends GET URL request formed from a base url, a query string
        and headers. Returns whatever this request receives back.
        :param url: string - base URL
        :param query: dictionary - url query paramteres as key-value
        :param headers: dictionary - header parameters as key-value
        :return: dictionary - data from returned JSON
        """
        # URL GET request
        query_str = urlencode(query).encode('ascii')
        # Repeat HTTP request if failure (e.g. unstable internet connection)
        response = None

        max_trials = 10
        trials_remain = max_trials                  # max trials
        while not response:
            trials_remain -= 1
            try:
                response = requests.get(url + "?" + query_str, headers=headers)
                response.raise_for_status() # raises if 4xx or 5xx error code
                if response.status_code == 101:
                    raise GoogleUpdating
            except GoogleUpdating:
                loger.error('%sStatus code %d: This panorama is recently being updated. Please, try later.'\
                                % (self._pano_msg(), 101)
                            )
                return None
            except Exception:
                if trials_remain == 0:
                    loger.warning(self._pano_msg() + 'Max trials of the URL request reached.\n' \
                                  + response.url + '\nStatus code: ' + response.status_code)
                    loger.exception()
                    return None

        msg = response.content
        return msg

    def _utilGetNumTiles(self, zoom):
        maxx = 0
        maxy = 0
        for x,y in product(range(30), range(20)):
            img = self.getTile(x,y,zoom)
            try:
                h = img.histogram()
            except:
                print ''
            if not sum(h[1:]) == 0:
                maxx = x if x>maxx else maxx
                maxy = y if y>maxy else maxy
        print 'Zoom %d: #tiles - horizontally %d   vertically %d' % (zoom, maxx+1, maxy+1)
        return (maxx, maxy)

    def _utilGetCrop(self, img):
        w,h = img.size
        _, _, col, row = img.getbbox()
        a = array(img.rotate(90).convert('L')).astype('int16')

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
        if not self.isValid():
            return 'Panorama not found'

        g = self.getGPS()
        d = self.getDate()
        s = '\n'
        s+= 'latlng: %f, %f\n' % (g[0], g[1])
        s+= 'pano id: %s\n' % self.pano_id
        s+= 'date: %s, %s\n' % (d[0], d[1])
        s+= '\nSaptial neighbours [id]:\n'
        s+= '------------------------\n'

        nbhs = self.getSpatialNeighbours()
        if nbhs:
            for x in nbhs:
                s += x.__str__() + '\n'

        s+= '\nTemporal neighbours [id, year, month]:\n'
        s+= '--------------------------------------\n'
        nbhs = self.getTemporalNeighbours()
        if nbhs:
            for x,t in nbhs:
                s += x.__str__() + ', ' + t.__str__() + '\n'

        return s

def str_bistr(data):
    buf = []
    for c in data:
        aux = format(ord(c), '08b')
        buf.append(aux[4:])
        buf.append(aux[:4])
    return buf

if __name__ == '__main__':
    pid = 'flIERJS9Lk4AAAQJKfjPkQ'
    pid = 'UP64cyOZX-nnzPSJx10gEg' # Aki, stitching error
    pid = 'SxOmGwcXGt9IFQxfhFbMdg' # no temporal neighbours, but can see it on web streetview
    pid = 'QsgZVIrMVYQAAAQIt4hsCQ'
    pid = 'WaYEbC0CoYLMJZXJrixo6w'
    pid = 'dEVgj2uhGgcAAAQYPMlnig'
    pid = 'T_flse8CPJRvIIFXhmt4xA'

    #faliure case from Jan Tomesek
    pid = 'vlnAwMU9HmslxyM-dvdlVw'
    pid = 'Xyska6QRCAb29RQuAPT48Q'
    p = Panorama(pid);
    # p.getImage()
    # p.getDepthData()
    p.getTemporalNeighbours()
    print p
    print ''
    # ll0 = (50, 14.41)
    # p = Panorama(latlng=ll0)
    # p.getDepthData()
    # p.getTemporalNeighbours()
    # #ll0 = (49.503569,13.544345)
    # #p = Panorama
    # pid = 'KzDzUS3ub-yrzbOLNomavw'
    # p = Panorama(pano_id=pid)
    # p.getDepthData()
    # p.getDepthImg()
    # p.getImage(0)
    # pass