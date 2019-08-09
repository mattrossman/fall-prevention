import os
import re
from scipy import spatial
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from smartfloor import FloorRecording, FloorRecordingBatch
directory = 'data/08-07-2019'

# Get training and testing source data paths
regex_test = re.compile(r'.*7_.*')
train_paths = [f'{directory}/{filename}' for filename in os.listdir(directory) if not regex_test.match(filename)]
test_paths = [f'{directory}/{filename}' for filename in os.listdir(directory) if regex_test.match(filename)]

# Extract gait cycles
train_recordings = [FloorRecording.from_csv(path, trimmed=True) for path in train_paths]
train_batch = FloorRecordingBatch(train_recordings)
train_cycles = train_batch.gait_cycles

recording_test = FloorRecording.from_csv(f'{directory}/7_slow_1.csv', trimmed=True)
test_cycles = recording_test.gait_cycles

train_feats = [cycle.features for cycle in train_cycles]
tree = spatial.KDTree(train_feats)

top5 = [train_cycles[i] for i in tree.query(test_cycles[0].features, k=5)[1]]


def plot_motion_similarity():
    fig = plt.figure()
    cycle = test_cycles[0]
    start, end = cycle.floor.walk_line
    cycle_cop = cycle.floor.cop.sel(time=slice(*cycle.date_window))
    cycle_cop_vel = cycle.floor.cop_vel.sel(time=slice(*cycle.date_window))
    cycle_cop_mlap = cycle.floor.cop_mlap.sel(time=slice(*cycle.date_window))
    cycle_cop_vel_mlap = cycle.floor.cop_vel_mlap.sel(time=slice(*cycle.date_window))
    gridspec = GridSpec(1, 2, width_ratios=[2, 1])
    ax1 = fig.add_subplot(gridspec.new_subplotspec((0, 0)))
    ax2 = fig.add_subplot(gridspec.new_subplotspec((0, 1)))


    """ LEFT PLOT """
    ax1.plot(*zip(start.to_array(), end.to_array()), c='r', linestyle=':')
    ax1.set_xlim(cycle_cop.x.min().item(), cycle_cop.x.max().item())
    ax1.quiver(cycle_cop.x, cycle_cop.y, cycle_cop_vel.x, cycle_cop_vel.y,
               angles='xy', units='dots', width=5, pivot='mid', cmap='cool')

    """ RIGHT PLOT """
    ax2.axvline(0, c='r', linestyle=':')
    ax2.quiver(cycle.cop_mlap.med, cycle.cop_mlap.ant, cycle.cop_vel_mlap.med, cycle.cop_vel_mlap.ant, range(40),
               angles='xy', units='dots', width=5, pivot='mid', cmap='cool')
    # ax2.set_xlim(-0.5, 0.5)

plot_motion_similarity()
