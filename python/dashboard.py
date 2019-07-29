import pandas as pd
import numpy as np
from matplotlib import animation
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from smartfloor import Floor
from kinect import KinectRecording
import sys
from scipy.signal import argrelmin

walk_segments = [
    {
        'pressure_path': 'data/time-sync-walk-1/smartfloor.csv',
        'rgb_path': 'data/time-sync-walk-1/rgb',
        'start': '2019-07-19T22:53:00',
        'end': '2019-07-19T22:53:04'
    },
    {
        'pressure_path': 'data/time-sync-walk-2.csv',
        'rgb_path': '',
        'start': '2019-07-19T22:53:43',
        'end': '2019-07-19T22:53:49'
    },
    {
        'pressure_path': 'data/time-sync-walk-4/smartfloor.csv',
        'rgb_path': 'data/time-sync-walk-4/Color',
        'start': '2019-07-19 22:56:10',
        'end': '2019-07-19 22:56:21'
    }
]
segment = walk_segments[0]

""" SET UP SOURCE DATA """
framerate_hz = 25
smoothing = 3
frame_delay = 1000/framerate_hz
window = int(framerate_hz / 25 * smoothing)
kr = KinectRecording(segment['rgb_path'])
floor = Floor.from_csv(segment['pressure_path'])
samples = pd.date_range(segment['start'], segment['end'], freq=pd.Timedelta(frame_delay, 'ms'))
pressure = floor.denoise().interp(time=samples)
cop = floor.cop().interp(time=samples)
speed = floor.cop_speed().interp(time=samples).rolling(time=window, center=True).mean()
accel = (speed - speed.shift(time=1)).rolling(time=window, center=True).mean()


def update_fig(i):
    dt = samples[i]
    fig.suptitle(f'Time: {dt.strftime("%H:%M:%S:%f")}')
    """ TOP PLOT """
    if img is not None:
        img.set_data(kr.imread(dt))

    """ MIDDLE PLOT """
    quad.set_array(pressure.isel(time=i).stack(z=('y', 'x')))

    """ BOTTOM PLOT """
    x, y, mag = cop.isel(time=i).to_array()
    scrub_line.set_data([dt, dt], [0, 1])
    cop_dot[0].set_data(x, y)
    cop_dot[0].set_markersize(10 * mag / cop.magnitude.max(dim='time'))


""" SET UP GRID LAYOUT """
fig = plt.figure()
ax1 = plt.subplot2grid((2, 2), (0, 0))
ax2 = plt.subplot2grid((2, 2), (0, 1))
ax3 = plt.subplot2grid((2, 2), (1, 0), colspan=2)

""" INIT PLOTS """
try:
    img = ax1.imshow(kr.imread(samples[0]))
except FileNotFoundError:
    img = None
quad = pressure.isel(time=0).plot(ax=ax2, vmin=0, vmax=1023, add_colorbar=False)
speed.rolling(time=1, center=True).mean().plot(ax=ax3)
accel.plot()
(cop.magnitude / 1024 * 20).plot()
scrub_line = ax3.axvline(samples[0], c='r')
cop_dot = ax2.plot(0, 0, 'ro')
ax1.set_axis_off()
ax2.set_axis_off()
ax2.set_title('')
ax2.invert_yaxis()
ax2.set_aspect('equal', adjustable='box')
plt.xticks(size=6, rotation='horizontal', ha='center')  # Smaller timestamp labels
plt.tight_layout(pad=0.4, w_pad=0.5)
update_fig(0)


def onclick(event):
    if event.inaxes is not None:
        ax = event.inaxes
        if ax is ax3:
            dt = mdates.num2date(event.xdata)
            i = samples.get_loc(dt, method='nearest')
            update_fig(i)


cid = fig.canvas.mpl_connect('button_press_event', onclick)


def update_frame(i):
    print(f'\rProgress: {i}/{samples.size}')
    update_fig(i)


def animate(path=None):
    print()
    ani = animation.FuncAnimation(fig, update_frame, frames=samples.size,
                                  interval=1000, save_count=sys.maxsize)
    if path is not None:
        Writer = animation.writers['ffmpeg']
        writer = Writer(fps=framerate_hz, metadata=dict(artist='Me'), bitrate=1800)
        ani.save(path, writer=writer)


""" LOCAL MIN IN COP SPEED """
_i_local_min = argrelmin(speed.values)[0]
local_min = speed.isel(time=_i_local_min)
ax3.scatter(local_min.time.values, local_min, c='r')
local_min_cop = cop.isel(time=_i_local_min)
ax2.scatter(local_min_cop.x, local_min_cop.y, c='y')
