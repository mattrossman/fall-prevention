import os
import re
from scipy import spatial
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from sklearn.neighbors import KDTree
import numpy as np
import smartfloor as sf
import cv2
directory = 'data/08-07-2019'

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
