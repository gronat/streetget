import utm
from math import sqrt

def circle(latlng_0, r):
    """
    Returns a validator function of Panorama that returns True is
    the Panorama is inside a circle of the radius r around the center
    point latlng_0.
    :param latlng_0: tuple (lat, lng) - center GPS
    :param r: float - radius in meters
    :return: validator(panorama) - given Panorama it returns True
             if the Panorama is inside the circle
    """
    (easting, northing, z_number, z_letter) = utm.from_latlon(latlng_0[0], latlng_0[1])

    def isClose(p):
        ll = p.getGPS()
        (est, nth, zn, zl) = utm.from_latlon(ll[0], ll[1], force_zone_number=z_number)
        x, y = est-easting, nth-northing
        d = sqrt(x**2+y**2)
        return d < r
    return isClose


def box(latlng_0, w, h=None):
    """
    Returns a validator function of Panorama that returns True is
    the Panorama is inside a box of the size w,h around center
    point latlng_0.
    :param latlng_0: tuple (lat, lng) - center GPS
    :param w: float - width in meters
    :param h: float - height in meters
    :return: validator(Panorama) - given a Panorama it returns True
             if the panorama is inside the box
    """
    if not h:
        h = w

    (easting, northing, z_number, z_letter) = utm.from_latlon(latlng_0[0], latlng_0[1])

    def isClose(p):
        ll = p.getGPS()
        (est, nth, zn, zl) = utm.from_latlon(ll[0], ll[1], force_zone_number=z_number)
        x, y = est-easting, nth-northing
        return abs(x) < w/2 and abs(y) < h/2
    return isClose

def gpsbox(topleft, btmright):
    """
    GPS box validator.
    :param topleft: tuple (lat,lng) - top left corner
    :param btmright: tuple (lat, lng) - bottom right
    :return: validator(Panorama) - given a Panorama it returns True
             if the Panorama is inside the gps box.
    """
    def isClose(p):
        lt,ln = p.getGPS()
        return lt<=topleft[0] and lt>btmright[0] and ln>=topleft[1] and ln<btmright[1]
    return isClose



