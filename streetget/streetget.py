#! /usr/bin/python
"""
Usage:
    streetget circle ( (LAT LNG) | PID) R [-tid -D DIR -z ZOOM] LABEL
    streetget box ( (LAT LNG) | PID) W H [-tid -D DIR -z ZOOM] LABEL
    streetget gpsbox LAT LNG LAT_TL LNG_TL LAT_BR LNG_BR [-tid -D DIR -z ZOOM] LABEL
    streetget resume [-D DIR] LABEL
    streetget info ( (LAT LNG) | PID)
    streetget show PID

Commands:
    circle              Downloads street-view inside circular area
                        centered at LAT, LNG and radius R meters.
    box                 Downloads street-view in rectangular area
                        of the width W and height H meters centered
                        at LAT, LNG
    gpsbox              Downloads street-view inside GPS rectangle
                        defined by top-left corner LAT_TL, LNG_TL
                        and bottom-right corner LAT_BR, LNG_BR. Download
                        starts at location LAT, LNG
    resume              Resumes interrupted downloading. Only
                        directory flag -D DIR is allowed. Other
                        flags will be restored from the interrupted
                        session.
    info                Prints info about the closest panorama at LAT,
                        LNG position or info about panorama id PID.
    show                Shows panorama image at zoom level 2 in default
                        python image browser.
Arguments:
    LABEL               Data set label. Will be used as a directory name.
    LAT, LNG            Starting point latitude and longitude.
    LAT_TL, LNG_TL      Top-left corner latitude, longitude.
    LAT_BR, LNG_BR      Bottom-right corner latitude, longitude.
    PID                 Panorama id hash code.
    W, H                Width and height in meters.
    R                   Radius in meters.

NOTE:
    A MINUS sign (dash) is NOT allowed for negative numbers. Instead use letter
    n to indicate negative number. E.g. use n1.23 instead -1.23.

Options:
    -t          Time machine, include temporal panorama neighbours.
    -i          Save images, if unset only metadata are fetched and saved.
    -d          Save depth data and depth map thumbnails at zoom level 0.
    -z ZOOM     Comma separated panorama zoom levels [0-5] to be
                download [default: 0,5]
    -D DIR      Root directory. Data will be saved in DIR/LABEL/
                [default: ./]
    -h, --help  Prints this screen.

"""
import pickle
import validator
import os
import sys
import logging
from docopt import docopt
from crawler import Crawler
from panorama import Panorama


class Arguments:
    cmds = None
    label = None
    root = None
    time = None
    images = None
    depth = None
    zoom = None
    latlng = None
    panoid = None
    topleft = None
    btmright = None
    circle = None
    box = None
    gpsbox = None
    resume = None
    info = None
    show = None
    pvalid = None

def tofloat(s):
    """
    String to float, negative floats are indicated with
    prepended character 'n'. If input is None it returns None.
    :param s:
    :return: float or None
    """
    if not s:
        return None
    if s[0] is not 'n':
        return float(s)
    return -float(s[1:])

def parse(a):
    # Info command
    if a.info:
        # pano_id has priority over latlng
        print Panorama(pano_id=a.panoid, latlng=a.latlng)
        return

    # Show command
    if a.show:
        Panorama(pano_id=a.panoid).getImage(2).show()
        return

    # Setting up loger
    fdir = os.path.join(a.root, a.label)
    if not os.path.exists(fdir):
        os.makedirs(fdir)
    l_fmt = '%(asctime)s %(levelname)s: %(message)s'        # format
    l_dfmt = '%m/%d/%Y %I:%M:%S %p'                         # date format
    l_fname = os.path.join(a.root, a.label, 'crawler.log')  # filepath
    logging.basicConfig(filename=l_fname, format=l_fmt, datefmt=l_dfmt)

    # Filename for command restore
    fname = os.path.join(a.root, a.label, 'crawlerArgs.pickle')

    # Handling resuem command a existing crawler
    if a.resume:
        with open(fname) as f:
            a = pickle.load(f)
        print '\nResuming command:'
        print a.cmds + '\n'
    else:
        if os.path.exists(fname):
            msg = '\n"%s" already crawled. Use "resume" (see --help) to continue crawling.' % (a.label,)
            raise AssertionError(msg)

    # Create area validator for crawler
    if a.circle:
        pvalid = validator.circle(a.latlng, a.r)
    elif a.box:
        pvalid = validator.box(a.latlng, a.w, a.h)
    elif a.gpsbox:
        pvalid = validator.gpsbox(a.topleft, a.btmright)
    else:
        raise NotImplementedError('Unknown validator')

    with open(fname, 'w') as f:
        pickle.dump(a, f)
    launch(a, pvalid)

def launch(a, pvalid):
    c = Crawler(pano_id=a.panoid, latlng=a.latlng, validator=pvalid,
                label=a.label, root=a.root, zoom=a.zoom,
                images=a.images, depth=a.depth, time=a.time
                )
    c.run()

def main():
    s = sys.argv

    args = docopt(__doc__, version='0.2.1')
    a = Arguments()

    # CLI command
    s[0] = os.path.basename(s[0])
    a.cmds = " ".join(s)            # command string

    # Path stuff
    a.label = args['LABEL']
    a.root = args['-D']

    # Image related stuff
    a.time = args['-t']
    a.images = args['-i']
    a.zoom = map(lambda x: int(x), args['-z'].split(','))
    a.depth = args['-d']

    # Area downloading stuff
    a.circle = args['circle']
    a.box = args['box']
    a.gpsbox = args['gpsbox']

    # Auxiliary commands
    a.resume = args['resume']
    a.info = args['info']
    a.show = args['show']

    # Params of area
    a.r = tofloat(args['R'])
    a.w,a.h = tofloat(args['W']), tofloat(args['H'])

    # GPS stuff
    a.latlng = (tofloat(args['LAT']), tofloat(args['LNG']))
    a.latlng = None if a.latlng[0] is None else a.latlng
    a.panoid = args['PID']
    a.topleft = tofloat(args['LAT_TL']), tofloat(args['LNG_TL'])
    a.btmright = tofloat(args['LAT_BR']), tofloat(args['LNG_BR'])

    parse(a)

if __name__ == '__main__':
    main()