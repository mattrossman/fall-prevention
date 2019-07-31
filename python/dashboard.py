import pandas as pd
import numpy as np
from numpy import linalg as LA
from matplotlib import animation
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from smartfloor import Floor
from kinect import KinectRecording
import sys
from scipy.signal import argrelmin, argrelmax
import xarray.ufuncs as xu
import xarray as xr

walk_segments = [
    {
        'pressure_path': 'data/time-sync-walk-1/smartfloor.csv',
        'rgb_path': 'data/time-sync-walk-1/rgb',
        'start': '2019-07-19T22:53:00',
        'end': '2019-07-19T22:53:04'
    },
    {
        'pressure_path': 'data/time-sync-walk-2/smartfloor.csv',
        'rgb_path': 'data/time-sync-walk-2/Color',
        'start': '2019-07-19T22:53:43',
        'end': '2019-07-19T22:53:49'
    },
    {
        'pressure_path': 'data/time-sync-walk-3.csv',
        'rgb_path': '',
        'start': '2019-07-19T22:54:17.36',
        'end': '2019-07-19T22:54:24.28'
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
smoothing = 10
frame_delay = 1000/framerate_hz
window = int(framerate_hz / 25 * smoothing)
kr = KinectRecording(segment['rgb_path'])
floor = Floor.from_csv(segment['pressure_path'], freq=pd.Timedelta(frame_delay, 'ms'), start=segment['start'], end=segment['end'])
samples = pd.DatetimeIndex(floor.samples.time.values)
pressure = floor.pressure
cop = floor._cop_abs
speed = floor.cop_speed.rolling(time=window, center=True).mean()
delta_speed = floor.cop_delta_speed.rolling(time=window, center=True).mean()

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
floor.cop_speed.plot(ax=ax3)

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
    print(f'\rProgress: {i}/{samples.size}', end='')
    update_fig(i)


def animate(path=None):
    print()
    ani = animation.FuncAnimation(fig, update_frame, frames=samples.size,
                                  interval=1000, save_count=sys.maxsize)
    if path is not None:
        Writer = animation.writers['ffmpeg']
        writer = Writer(fps=framerate_hz, metadata=dict(artist='Me'), bitrate=1800)
        ani.save(path, writer=writer)


""" PLOT THE FOOTSTEP MARKERS """
steps = floor.footsteps

for step_time in steps.time.values:
    ax3.axvline(step_time, c='k', linestyle='--')

rights = cop.sel(time=steps.dir[steps.dir == 'right'].time)
lefts = cop.sel(time=steps.dir[steps.dir == 'left'].time)

ax2.scatter(rights.x, rights.y, c='yellow')
ax2.scatter(lefts.x, lefts.y, c='green')

""" PLOT THE WALK LINE """
start_mid, end_mid = floor.walk_line
ax2.plot([start_mid.x, end_mid.x], [start_mid.y, end_mid.y], c='r')
walk_length = LA.norm((end_mid - start_mid).to_array())
norm_walk = (end_mid - start_mid) / walk_length

rot_matrix = np.array([[norm_walk.x.item(), (-norm_walk.y).item()],
                       [norm_walk.y.item(), norm_walk.x.item()]])

rot_matrix2 = np.array([[(-norm_walk.y).item(), (-norm_walk.x).item()],
                       [norm_walk.x.item(), (-norm_walk.y).item()]])

reoriented = (floor.footsteps[['x', 'y']] - start_mid).to_array().values.T @ rot_matrix2.T
v_midline = (end_mid - start_mid).to_array()
reoriented2 = np.cross(v_midline, floor.footsteps[['x','y']].to_array().T - start_mid.to_array()) / walk_length