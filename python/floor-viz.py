import pandas as pd
from matplotlib import animation
import matplotlib.pyplot as plt
from smartfloor import FloorRecording
import sys


floor = FloorRecording.from_csv('data/time-sync-walk-4.csv')
lo, hi = floor.range()
safe_range = pd.date_range(start=lo, end=hi, freq='40ms')

fig = plt.figure()
quad = floor.denoise().isel(time=0).plot(vmin=0, vmax=1023)
plt.gca().set_aspect('equal', adjustable='box')  # make x and y scale equal
plt.gca().invert_yaxis()

cop = plt.plot(0, 0, 'ro')

def update_quad_data(args):
    i, dt = args
    plt.title(f'Time: {dt.strftime("%H:%M:%S")} | Frame: {i}')
    quad.set_array(floor.denoise().interp(time=dt).stack(z=('y', 'x')))
    x, y, mag = floor.cop().interp(time=dt).to_array()
    cop[0].set_data(x, y, )
    cop[0].set_markersize(20 * mag / floor.cop().magnitude.max(dim='time'))


ani = animation.FuncAnimation(fig, update_quad_data, frames=enumerate(safe_range),
                              interval=1000, save_count=sys.maxsize)


def write_animaton(path):
    Writer = animation.writers['ffmpeg']
    writer = Writer(fps=25, metadata=dict(artist='Me'), bitrate=1800)
    ani.save(path, writer=writer)
