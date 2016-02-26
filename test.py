from time import sleep

import plotly
print plotly.__version__  # version >1.9.4 required
from plotly.graph_objs import Scatter, Layout
plotly.offline.plot({
"data": [
    Scatter(x=[1, 2, 3, 4], y=[4, 1, 3, 7])
],
"layout": Layout(
    title="hello world"
)
})

def a():
    try:
        while True:
            sleep(2)
    except KeyboardInterrupt:
        print 'maybe keyboard interrupt?'
        raise KeyboardInterrupt
def b():
    try:
        a()
    except:
        print 'something worng with a'
        raise KeyboardInterrupt
def main():
    try:
        b()
    except:
        print 'something worng with b'

if __name__ == '__main__':
    main()