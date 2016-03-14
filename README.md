#Welcome to `streetget` BETA

`streetget` is a small python package for StreetView image downloading. It allows to you to crawl and download the StreetView panoramas along with its metadata and **depth maps**. It also allows you to download the StreetView **time-machine**, historical panoramas.

### Quick start:
**Example 1:** _Prague_ is a beautiful city! Download panoramas inside a rectangle of the with 1.5 _km_ and height 1 _km_ centered at 50.0833° N, 14.4167°E. Download panoramas of the zoom levels 0, 3 and 5, store metadata, depth-map data and the depth-map thumbnails. Download also historical panoramas, save the data to `/local/myData` and name the dataset 'Prague_all'.

`streetget box 50.0833°N, 14.4167°N 300 -itd -z 0,3,5 -D /local/myData  Prague_all`

**Example 2:** Restore previous _Prague_ download after **Ctrl-c** keyboard interrupt or forced computer shutdown.

`streetget resume -D /local/myData    Prague_all`

**Example 3:** Fetch only StreetView metadata from circular area of the radius _300m_ starting at GPS location 48.8567°N 2.3508°N,  label of the data as 'Paris' and save it into `~/datasets` directory:  

`streetget circle 48.8567 2.3508 300 -D ~/datasets Paris`

**Example 4:** Get info about available panoramas at location 50.0833°N, 14.4167°N.  
`streetget info 50.0833 14.4167`
#####Output:
	latlng: 50.083470, 14.416540
	pano id: b5KMHLrX55jsWzsDZ_z0bg
	date: 2014, 4
	Saptial neighbours [id]:
	------------------------
	NIsq7Xg-HztpzjA2H_IGoA
	L-p2EeOaJZewg8ZXAYwFAw
	j3DbvTldnlsAAAQfCOywVw

	Temporal neighbours [id year, month]:
	-------------------------------------
	YX3qsOxeKkxehNr8qQ59Vg 2009, 5
	6llp-LT4nAtCfs1SsyNyYA 2009, 9
	rkQFq5F8JgdTbfBEt1pbBQ 2011, 8
	c4JXOQ0o1QkdEBMdSWgBwA 2012, 3

**Example 6:** Show the panorama image given by panorama hash id 6llp-LT4nAtCfs1SsyNyYA:  
`streetget show 6llp-LT4nAtCfs1SsyNyYA`

### Installation:
The package is tested with Python 2.7  and requires several packages such as _utm, matplotlib, numpy, docopt, pickle, PIL, Queue_. No installation is needed fot the script itself. Just clone the 'streetget' to any directory e.g. `/home/user/streetget/` and inside the directory do `chmod 755 streetget.py`. Create a symbolic link `sudo ln -s  /home/user/streetget/streetget.py /usr/bin/streetget` or add alias to your `.bash_aliases`.  You can also run the script directly calling the `streetget.py` with arguments.

###Usage:
	 streetget circle ( (LAT LNG) | PID) R [-tid -D DIR -z ZOOM] LABEL
	 streetget box ( (LAT LNG) | PID) W H [-tid -D DIR -z ZOOM] LABEL
	 streetget gpsbox LAT LNG LAT_TL LNG_TL LAT_BR LNG_BR [options] LABEL
	 streetget resume [-D DIR] LABEL
	 streetget info ( (LAT LNG) | PID)
	 streetget show PID



###Commands:
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
###Arguments:
    LABEL               Data set label. Will be used as a directory name.
    LAT, LNG            Starting point latitude and longitude.
    LAT_TL, LNG_TL      Top-left corner latitude, longitude.
    LAT_BR, LNG_BR      Bottom-right corner latitude, longitude.
    PID                 Panorama id hash code.
    W, H                Width and height in meters.
    R                   Radius in meters.

>**Note**: A MINUS sign (dash) is NOT allowed for negative numbers. Instead use letter 'n' to indicate negative value. E.g. use n1.23 instead -1.23.

###Options:
    -t          Time machine, include temporal panorama neighbours.
    -i          Save images, if unset only metadata are fetched and saved.
    -d          Save depth data and depth map thumbnails at zoom level 0.
    -z ZOOM     Comma separated panorama zoom levels [0-5] to be
                downloaded [default: 0,5]
    -D DIR      Root directory. Data will be saved in DIR/LABEL/
                [default: ./]
    -h, --help  Prints this screen.