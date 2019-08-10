import os
import re
import pickle
from scipy import spatial
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from smartfloor import FloorRecording, FloorRecordingBatch
directory = 'data/08-07-2019'
num_subjects = 7


def calculate_accuracy(i):
    # Get training and testing source data paths
    regex_test = re.compile(r'.*' + str(i) + '_.*')
    train_paths = [f'{directory}/{filename}' for filename in os.listdir(directory) if not regex_test.match(filename)]
    # test_paths = [f'{directory}/{filename}' for filename in os.listdir(directory) if regex_test.match(filename)]

    # Extract gait cycles
    train_recordings = [FloorRecording.from_csv(path, trimmed=True) for path in train_paths]
    train_batch = FloorRecordingBatch(train_recordings)
    train_cycles = train_batch.gait_cycles
    gait_styles = {
        'normal': ['normal', {}],
        'slow': ['slow', {}],
        'hunch': ['hunch', {}],
        'steppage': ['stppg', {}],
        'left_hobble': ['lhob', {}],
        'right_hobble': ['rhob', {}]
    }

    with open('tree' + str(i) + '.p', 'rb') as file:
        tree = pickle.load(file)

        for style in gait_styles.values():
            file_string = str(i) + '_' + style[0] + '_1.csv'
            recording_test = FloorRecording.from_csv(f'{directory}/' + file_string, trimmed=True)
            test_cycles = recording_test.gait_cycles

            count_style_total = 0
            count_style_correct = 0
            for j in range(len(test_cycles)):
                count_style_total = count_style_total + 1
                top5 = [train_cycles[l] for l in tree.query(test_cycles[j].features, k=5)[1]]
                top1 = top5[0].name[2:]
                top1_type = top1[:top1.find('_')]
                if style[0] == top1_type:
                    count_style_correct = count_style_correct + 1
            style[1].update({'total': count_style_total})
            style[1].update({'total_correct': count_style_correct})
            style[1].update({'accuracy': str((count_style_correct / count_style_total) * 100) + '%'})
    return gait_styles


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


# plot_motion_similarity()
participants = [calculate_accuracy(i) for i in range(1, num_subjects + 1)]
