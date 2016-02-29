import dill
import logging
import os


# Setting up loger
l_fmt = '%(asctime)s %(levelname)s: %(message)s'      # format
l_dfmt = '%m/%d/%Y %I:%M:%S %p'                       # date format
l_fname = 'err_testFname.log'                          # file name
logging.basicConfig(filename=l_fname, format=l_fmt, datefmt=l_dfmt)
loger = logging.getLogger('crawler')
loger.setLevel(logging.ERROR)


fname  = 'myData/paris/db.pickle'
with open(fname) as f:
    print 'Loading ...'
    db = dill.load(f)
    print  'done'

for key in db.d:
    fname = key+'.tmp'
    #print fname
    try:
        with open(fname, 'w'):
            pass
    except Exception as e:
        msg = 'can\'t create a file'+type(e).__name__+str(e)
        loger.error(msg)
        print fname
        break

    try:
        os.remove(fname)
    except Exception as e:
        msg = 'can\'t remove a file' + type(e).__name__ + str(e)
        loger.error(msg)
        print fname
        break
else:
    print 'All filenames can be created :) '



for key in db.d:
    dname = key[0:2:]
    #print dname
    try:
        os.mkdir(dname)
    except Exception as e:
        msg = 'can\'t create a directory'+type(e).__name__+str(e)
        loger.error(msg)
        print dname
        break

    try:
        os.rmdir(dname)
    except Exception as e:
        msg = 'can\'t remove a directory' + type(e).__name__ + str(e)
        loger.error(msg)
        print dname
        break
else:
    print 'All directories can be created :) '