import sys

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import animation
from matplotlib.gridspec import GridSpec

from kinect import KinectRecording
from smartfloor import FloorRecording
from segments import time_sync as walk_segments

segment = walk_segments[1]

""" SET UP SOURCE DATA """
framerate_hz = 25
smoothing = 10
frame_delay = 1000/framerate_hz
window = int(framerate_hz / 25 * smoothing)
kr = KinectRecording(segment['rgb_path'])
floor = FloorRecording.from_csv(segment['pressure_path'], freq=pd.Timedelta(frame_delay, 'ms')) # start=segment['start'], end=segment['end']
load_start, load_end = floor.loaded_window
floor.trim(load_start, load_end)
samples = pd.DatetimeIndex(floor.samples.time.values)

""" CACHE SOME VARIABLES """
pressure = floor.pressure
cop = floor.cop
mag = cop.magnitude
speed = floor.cop_vel_mag.rolling(time=window, center=True).mean()
delta_speed = floor.cop_vel_mag_roc.rolling(time=window, center=True).mean()
steps = floor.footstep_positions
cop_mlap = floor.cop_mlap
cop_vel_mlap = floor.cop_vel_mlap


def update_fig(i):
    dt = samples[i]
    fig.suptitle(f'Time: {dt.strftime("%H:%M:%S:%f")}')
    # TOP LEFT
    if img is not None:
        img.set_data(kr.imread(dt))

    # TOP RIGHT
    quad.set_array(pressure.isel(time=i).stack(z=('y', 'x')))

    # BOTTOM
    x, y, mag = cop.isel(time=i).to_array()
    scrub_line.set_data([dt, dt], [0, 1])
    cop_dot[0].set_data(x, y)
    cop_dot[0].set_markersize(10 * mag / cop.magnitude.max(dim='time'))

    # VERTICAL
    scrub_line_v.set_data([0, 1], [dt, dt])


""" SET UP GRID LAYOUT """
fig = plt.figure(figsize=(15, 7))
gridspec = GridSpec(2, 3, width_ratios=[3, 3, 1], height_ratios=[2, 1])
ax1 = fig.add_subplot(gridspec.new_subplotspec((0, 0), rowspan=1, colspan=1))
ax2 = fig.add_subplot(gridspec.new_subplotspec((0, 1), rowspan=1, colspan=1))
ax3 = fig.add_subplot(gridspec.new_subplotspec((1, 0), rowspan=1, colspan=2))
ax4 = fig.add_subplot(gridspec.new_subplotspec((0, 2), rowspan=2, colspan=1))

""" INIT PLOTS """

# TOP LEFT
ax1.set_axis_off()
try:
    img = ax1.imshow(kr.imread(samples[0]))
except FileNotFoundError:
    img = None

# TOP RIGHT
ax2.set_axis_off()
ax2.set_title('')
ax2.set_aspect('equal', adjustable='box')
quad = pressure.isel(time=0).plot(ax=ax2, vmin=0, vmax=1023, add_colorbar=False)
cop_dot = ax2.plot(0, 0, 'ro')

rights = cop.sel(time=steps.dir[steps.dir == 'right'].time)
lefts = cop.sel(time=steps.dir[steps.dir == 'left'].time)
ax2.scatter(rights.x, rights.y, c='yellow')
ax2.scatter(lefts.x, lefts.y, c='green')

start_mid, end_mid = floor.walk_line
ax2.plot([start_mid.x, end_mid.x], [start_mid.y, end_mid.y], c='r')

# BOTTOM
floor.cop_vel_mag.plot(ax=ax3)
(floor.cop_vel_mag_roc / 20).plot(ax=ax3)
(floor.cop_accel_mag_roc / 100).rolling(time=10).mean().plot(ax=ax3)
scrub_line = ax3.axvline(samples[0], c='k')
for step_time in steps.time.values:
    ax3.axvline(step_time, c='gray', linestyle=':')
for strike in floor._heelstrikes.dir:
    ax3.axvline(strike.time.values, c=('r' if strike.item() == 'right' else 'b'), linestyle='--')
plt.setp(ax3.xaxis.get_majorticklabels(), rotation='horizontal', ha='center', size=6)

# VERTICAL
ax4.plot(cop_mlap.med, cop_mlap.time.values)
ax4.plot(cop_vel_mlap.med / 5, cop_vel_mlap.time.values)
ax4.axvline(0, c='k')
ax4.axis(ymin=samples[0], ymax=samples[-1])
plt.setp(ax4.yaxis.get_majorticklabels(), rotation='vertical', va='center', size=6)
# ax4.set_axis_off()
scrub_line_v = ax4.axhline(samples[0], c='k')

for step_time in steps.time.values:
    ax4.axhline(step_time, c='gray', linestyle=':')


plt.tight_layout(pad=0, w_pad=0.4)

""" HANDLERS """


def onclick(event):
    if event.inaxes is not None:
        ax = event.inaxes
        if ax is ax3:
            dt = mdates.num2date(event.xdata)
            i = samples.get_loc(dt, method='nearest')
            update_fig(i)


def onkeypress(event):
    dt = scrub_line.get_data()[0][0]
    i = samples.get_loc(dt, method='nearest')
    if event.key == "left":
        update_fig(i - 1)
    elif event.key == "right":
        update_fig(i + 1)


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


key_event_id = fig.canvas.mpl_connect('key_press_event', onkeypress)
click_event_id = fig.canvas.mpl_connect('button_press_event', onclick)
update_fig(0)
