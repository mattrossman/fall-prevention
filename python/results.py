import os
import re
import pickle
import numpy as np
import smartfloor as sf
directory = 'data/08-07-2019'
num_subjects = 7

"""
# Get training and testing source data paths
regex_test = re.compile(r'.*5_.*')
train_paths = np.array([f'{directory}/{filename}'
                        for filename in os.listdir(directory) if not regex_test.match(filename)])
# train_paths = train_paths[np.random.choice(len(train_paths), size=6, replace=False)]
test_paths = [f'{directory}/{filename}' for filename in os.listdir(directory) if regex_test.match(filename)]

# Extract gait cycles
train_recordings = (sf.FloorRecording.from_csv(path, trimmed=True) for path in train_paths)
train_batch = sf.FloorRecordingBatch(train_recordings)
train_cycles = train_batch.gait_cycles

recording_test = sf.FloorRecording.from_csv(f'{directory}/5_normal_1.csv', trimmed=True)
test_cycles = recording_test.gait_cycles
query_cycle = test_cycles[1]
distances = np.array([query_cycle.dist(cycle) for cycle in train_cycles])
neighbors = train_cycles[distances.argsort()]
points = query_cycle.cop_mlap.to_array().T.values


sf.plot_gait_cycles(np.concatenate(([query_cycle], neighbors[:5])))
"""

def calculate_accuracy(i):
    # Get training and testing source data paths
    regex_test = re.compile(r'.*' + str(i) + '_.*')
    train_paths = [f'{directory}/{filename}' for filename in os.listdir(directory) if not regex_test.match(filename)]
    # test_paths = [f'{directory}/{filename}' for filename in os.listdir(directory) if regex_test.match(filename)]

    # Extract gait cycles
    train_recordings = [sf.FloorRecording.from_csv(path, trimmed=True) for path in train_paths]
    train_batch = sf.FloorRecordingBatch(train_recordings)
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
            recording_test = sf.FloorRecording.from_csv(f'{directory}/' + file_string, trimmed=True)
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


def total_style_accuracy(style):
    d = {}
    d.update({'style': style})
    total = 0
    correct = 0
    for participant in participants:
        total = total + participant[style][1]['total']
        correct = correct + participant[style][1]['total_correct']
    d.update({'total': total})
    d.update({'total_correct': correct})
    d.update({'accuracy': str((correct / total) * 100) + '%'})
    return d


def total_accuracy(styles_a):
    total = 0
    correct = 0
    for style in styles_a:
        total = total + style['total']
        correct = correct + style['total_correct']
    return correct / total


# plot_motion_similarity()
# participants = [calculate_accuracy(i) for i in range(1, num_subjects + 1)]
# pickle.dump(participants, open('accuracy.p', 'wb'))
a = open('accuracy.p', 'rb')
participants = pickle.load(a)
a.close()

with open('accuracy.p', 'rb') as a:
    styles = ['normal','slow','hunch','steppage','left_hobble','right_hobble']
    style_accuracy = [total_style_accuracy(style) for style in styles]

    overall_accuracy = total_accuracy(style_accuracy)


def pickle_cycle_batch():
    """ Make a batch of all data and save to binary """
    paths = [f'{directory}/{filename}' for filename in os.listdir(directory)]
    floor_batch = sf.FloorRecordingBatch.from_csv(paths, trimmed=True)
    with open('cycle_batch.p', 'wb') as f:
        pickle.dump(floor_batch.gait_cycle_batch, f)


def unpickle_cycle_batch() -> sf.GaitCycleBatch:
    """ Load the saved data batch """
    with open('cycle_batch.p', 'rb') as f:
        return pickle.load(f)


def cycle_style(cycle) -> str:
    """Extract the gait style string (e.g 'normal', 'lhob') from a data file path"""
    return re.match(r'^\d_([^_]*)_.*', cycle.name).groups()[0]


def cycles_with_style(cycles: sf.GaitCycleBatch, style: str) -> sf.GaitCycleBatch:
    """Filter a batch of cycles by a gait style string"""
    return sf.GaitCycleBatch([cycle for cycle in cycles if cycle_style(cycle) == style])


batch = unpickle_cycle_batch()
train, test = batch.partition_names(r'7_.*', reverse=True)
test_slow = cycles_with_style(test, 'slow')
