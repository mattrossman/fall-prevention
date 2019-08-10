import os
import re
from scipy import spatial
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import numpy as np
import smartfloor as sf
import cv2
directory = 'data/08-07-2019'

# Get training and testing source data paths
regex_test = re.compile(r'.*7_.*')
train_paths = np.array([f'{directory}/{filename}'
                        for filename in os.listdir(directory) if not regex_test.match(filename)])
# train_paths = train_paths[np.random.choice(len(train_paths), size=2, replace=False)]
test_paths = [f'{directory}/{filename}' for filename in os.listdir(directory) if regex_test.match(filename)]

# Extract gait cycles
train_recordings = (sf.FloorRecording.from_csv(path, trimmed=True) for path in train_paths)
train_batch = sf.FloorRecordingBatch(train_recordings)
train_cycles = train_batch.gait_cycles

recording_test = sf.FloorRecording.from_csv(f'{directory}/7_slow_1.csv', trimmed=True)
test_cycles = recording_test.gait_cycles
query_cycle = test_cycles[1]

points = query_cycle.cop_mlap.to_array().T.values


train_feats = [cycle.features for cycle in train_cycles]
tree = spatial.KDTree(train_feats)

top5 = [train_cycles[i] for i in tree.query(query_cycle.features, k=5)[1]]
sf.plot_gait_cycles([query_cycle] + top5)
