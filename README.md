#Usage:
    streetget circle ( (LAT LNG) | PID) R [-tid -D DIR -z ZOOM] LABEL
    streetget box ( (LAT LNG) | PID) W H [-tid -D DIR -z ZOOM] LABEL
    streetget gpsbox LAT LNG LAT_TL LNG_TL LAT_BR LNG_BR [options] LABEL
    streetget resume [-D DIR] LABEL
    streetget info ( (LAT LNG) | PID)
    streetget show PID

#Commands:
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
#Arguments:
    LABEL               Data set label. Will be used as a directory name.
    LAT, LNG            Starting point latitude and longitude.
    LAT_TL, LNG_TL      Top-left corner latitude, longitude.
    LAT_BR, LNG_BR      Bottom-right corner latitude, longitude.
    PID                 Panorama id hash code.
    W, H                Width and height in meters.
    R                   Radius in meters.

#NOTE:
    A MINUS sign (dash) is NOT allowed for negative numbers. Instead use letter
    n to indicate negative number. E.g. use n1.23 instead -1.23.

#Options:
    -t          Time machine, include temporal panorama neighbours.
    -i          Save images, if unset only metadata are fetched and saved.
    -d          Save depth data and depth map thumbnails at zoom level 0.
    -z ZOOM     Comma separated panorama zoom levels [0-5] to be
                download [default: 0,5]
    -D DIR      Root directory. Data will be saved in DIR/LABEL/
                [default: ./]
    -h, --help  Prints this screen.
