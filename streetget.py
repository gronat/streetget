#! /usr/bin/python
"""
Usage:
    streetget circle LAT LNG R [-i -d DIR -z ZOOM] LABEL
    streetget box LAT LNG W H [-i -d DIR -z ZOOM] LABEL
    streetget gpsbox LAT LNG LAT_TL LNG_TL LAT_BR LNG_BR [options] LABEL
    streetget resume [-d DIR] LABEL

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
                        directory flag -d DIR is allowed. Other
                        flags will be restored from the interrupted
                        session.

Arguments:
    LABEL               Data set label. Will be used as directory name.
    LAT, LNG            Starting point latitude and longitude.
    LAT_TL, LNG_TL      Top-left corner latitude, longitude.
    LAT_BR, LNG_BR      Top-left corner latitude, longitude.
    W, H                Width and height in meters.
    R                   Radius in meters.

NOTE:
    A MINUS sign (dash) is NOT allowed for negative numbers. Instead use letter
    n to indicate negative number. E.g. use n1.23 instead -1.23.

Options:
    -i          Download images, if not set only metadata are fetched.
    -z ZOOM     Comma separated panorama zoom levels [0-5] to be
                download [default: 0,5]
    -d DIR      Root directory. Data will be saved in DIR/LABEL/
                [default: ./]
    -h, --help  Prints this screen.

"""
import pickle
import validator
import os
from docopt import docopt
from crawler import Crawler

class Arguments:
    label = None
    root = None
    images = None
    zoom = None
    latlng = None
    topleft = None
    btmright = None
    circle = None
    box = None
    gpsbox = None
    pvalid = None

def tofloat(s):
    if not s:
        return None
    if s[0] is not 'n':
        return float(s)
    return -float(s[1:])

def parse(a):

    # Filename for command restore
    fname = os.path.join(a.root, a.label, 'crawlerArgs.pickle')

    # Load options for crawler
    if args['resume']:
        with open(fname) as f:
            a = pickle.load(f)
    else:
        if os.path.exists(fname):
            msg = '\n"%s" already crawled. Use resume to continue crawling.' % (a.label,)
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

    if not os.path.exists(os.path.dirname(fname)):
        os.makedirs(os.path.dirname(fname))

    with open(fname, 'w') as f:
        pickle.dump(a, f)
    launch(a, pvalid)

def launch(a, pvalid):
    c = Crawler(latlng=a.latlng, validator=pvalid, label=a.label, root=a.root, zoom=a.zoom, images=a.images)
    c.run()

if __name__ == '__main__':
    args = docopt(__doc__, version='0.0.1')
    a = Arguments()

    # Path stuff
    a.label = args['LABEL']
    a.root = args['-d']

    # Image related stuff
    a.images = args['-i']
    a.zoom = map(lambda x: int(x), args['-z'].split(','))

    # Area downloading stuff
    a.circle = args['circle']
    a.box = args['box']
    a.gpsbox = args['gpsbox']

    # Params of area
    a.r = tofloat(args['R'])
    a.w,a.h = tofloat(args['W']), tofloat(args['H'])

    # GPS stuff
    a.latlng = (tofloat(args['LAT']), tofloat(args['LNG']))
    a.topleft = tofloat(args['LAT_TL']), tofloat(args['LNG_TL'])
    a.btmright = tofloat(args['LAT_BR']), tofloat(args['LNG_BR'])

    parse(a)


