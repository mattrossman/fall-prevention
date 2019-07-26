import pandas as pd
import numpy as np
from matplotlib import animation
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.pyplot as plt
from smartfloor import Floor
from kinect import KinectRecording
import sys

walk_segments = [
    {
        'pressure_path': 'data/time-sync-walk-1/smartfloor.csv',
        'rgb_path': 'data/time-sync-walk-1/rgb',
        'start': '2019-07-19T22:53:00',
        'end': '2019-07-19T22:53:04'
    },
    {
        'floor_path': 'data/time-sync-walk-2.csv',
        'start': '2019-07-19T22:53:43',
        'end': '2019-07-19T22:53:49'
    }
]
segment = walk_segments[0]

""" SET UP SOURCE DATA """
kr = KinectRecording(segment['rgb_path'])
floor = Floor.from_csv(segment['pressure_path'])
samples = pd.date_range(segment['start'], segment['end'], freq='40ms')
pressure = floor.denoise().interp(time=samples)
cop = floor.cop().interp(time=samples)
speed = floor.cop_speed().interp(time=samples)


def update_frame(i):
    dt = samples[i]
    fig.suptitle(f'Time: {dt.strftime("%H:%M:%S:%f")}')
    """ TOP PLOT """
    img.set_data(kr.imread(dt))

    """ MIDDLE PLOT """
    quad.set_array(pressure.isel(time=i).stack(z=('y', 'x')))

    """ BOTTOM PLOT """
    x, y, mag = cop.isel(time=i).to_array()
    scrub_line.set_data([dt, dt], [0, 1])
    cop_dot[0].set_data(x, y)
    cop_dot[0].set_markersize(10 * mag / cop.magnitude.max(dim='time'))
    print(f'Progress: {i}/{samples.size}')


""" SET UP GRID LAYOUT """
fig = plt.figure()
ax1 = plt.subplot2grid((2, 2), (0, 0))
ax2 = plt.subplot2grid((2, 2), (0, 1))
ax3 = plt.subplot2grid((2, 2), (1, 0), colspan=2)

""" INIT PLOTS """
img = ax1.imshow(kr.imread(samples[0]))
quad = pressure.isel(time=0).plot(ax=ax2, vmin=0, vmax=1023, add_colorbar=False)
speed.rolling(time=2, center=True).mean().plot(ax=ax3)
(speed - speed.shift(time=1)).rolling(time=2).mean().plot()
scrub_line = ax3.axvline(samples[0], c='r')
cop_dot = ax2.plot(0, 0, 'ro')
ax1.set_axis_off()
ax2.set_axis_off()
ax2.set_title('')
ax2.set_aspect('equal', adjustable='box')
plt.xticks(size=6, rotation='horizontal', ha='center')  # Smaller timestamp labels
plt.tight_layout(pad=0.4, w_pad=0.5)
update_frame(0)

ani = animation.FuncAnimation(fig, update_frame, frames=samples.size,
                              interval=1000, save_count=sys.maxsize)

def write_animaton(path):
    Writer = animation.writers['ffmpeg']
    writer = Writer(fps=25, metadata=dict(artist='Me'), bitrate=1800)
    ani.save(path, writer=writer)
