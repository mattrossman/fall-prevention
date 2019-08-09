import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.gridspec import GridSpec

from segments import time_sync as walk_segments
from smartfloor import FloorRecording

segment = walk_segments[1]

""" SET UP SOURCE DATA """
framerate_hz = 25
frame_delay = 1000/framerate_hz
floor = FloorRecording.from_csv(segment['pressure_path'], freq=pd.Timedelta(frame_delay, 'ms'), start=segment['start'], end=segment['end'])
sample_index = pd.DatetimeIndex(floor.samples.time.values)


""" CACHING SOME DATA """
cop = floor.cop
cop_speed = floor.cop_vel_mag
cop_speed_roc = floor.cop_vel_mag_roc
cycles = floor.gait_cycles
steps = floor.footstep_positions
rights = cop.sel(time=steps.dir[steps.dir == 'right'].time)
lefts = cop.sel(time=steps.dir[steps.dir == 'left'].time)
start, end = floor.walk_line


def plot_motion_similarity():
    fig = plt.figure()
    cycle = cycles[1]
    cycle_cop = cop.sel(time=slice(*cycle.date_window))
    cycle_cop_vel = floor.cop_vel.sel(time=slice(*cycle.date_window))
    cycle_cop_mlap = floor.cop_mlap.sel(time=slice(*cycle.date_window))
    cycle_cop_vel_mlap = floor.cop_vel_mlap.sel(time=slice(*cycle.date_window))
    gridspec = GridSpec(1, 2, width_ratios=[2, 1])
    ax1 = fig.add_subplot(gridspec.new_subplotspec((0, 0)))
    ax2 = fig.add_subplot(gridspec.new_subplotspec((0, 1)))


    """ LEFT PLOT """
    # ax1.scatter(cycle_cop.x, cycle_cop.y)
    ax1.plot(*zip(start.to_array(), end.to_array()), c='r', linestyle=':')
    ax1.set_xlim(cycle_cop.x.min().item(), cycle_cop.x.max().item())
    ax1.quiver(cycle_cop.x, cycle_cop.y, cycle_cop_vel.x, cycle_cop_vel.y,
               angles='xy', units='dots', width=5, pivot='mid', cmap='cool')

    """ RIGHT PLOT """
    ax2.axvline(0, c='r', linestyle=':')
    # ax2.scatter(cycle_cop_mlap.med, cycle_cop_mlap.ant)
    ax2.quiver(cycle.cop_mlap.med, cycle.cop_mlap.ant, cycle.cop_vel_mlap.med, cycle.cop_vel_mlap.ant, range(40),
               angles='xy', units='dots', width=5, pivot='mid', cmap='cool')
    ax2.set_xlim(-0.5, 0.5)


def plot_step_detection():
    """ PLOTTING SETUP """
    fig = plt.figure()
    gridspec = GridSpec(2, 1, height_ratios=[1, 1])
    ax1 = fig.add_subplot(gridspec.new_subplotspec((0, 0)))
    ax2 = fig.add_subplot(gridspec.new_subplotspec((1, 0)))

    # Set up the 2D floor
    ax1.set_ylim(0, 2)

    """ 2D FLOOR VIEW """
    # ax1.set_axis_off()
    # ax1.set_xticklabels([])
    # ax1.set_yticklabels([])
    ax1.scatter(cop.x, cop.y, c=cop.magnitude, cmap='Greys', s=5)
    ax1.scatter(rights.x, rights.y, c='red', marker='o')
    ax1.scatter(lefts.x, lefts.y, c='blue', marker='o')
    ax1.plot(*zip(start.to_array(), end.to_array()), c='r', linestyle=':')

    """ COP PARAMS SERIES """
    # ax2.set_axis_off()
    ax2.set_yticklabels([])
    ax2.set_xlim(cop_speed.time[0].values, cop_speed.time[-1].values)
    cop_speed.plot(ax=ax2)
    (cop_speed_roc / 10).plot(ax=ax2)
    for support in steps.dir:
        ax2.axvline(support.time.values, c=('r' if support.item() == 'right' else 'b'), linestyle='--')
    for strike in floor._heelstrikes.dir:
        ax2.axvline(strike.time.values, c='gray', linestyle=':')
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation='horizontal', ha='center', size=6)
