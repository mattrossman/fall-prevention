import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr

from scipy import spatial
from smartfloor import FloorRecording
from segments import test_run as walk_segments
from segments import time_sync

old_recordings = [FloorRecording.from_csv(segment['pressure_path'], freq='40ms', start=segment['start'], end=segment['end'])
                  for segment in time_sync]
recordings = [FloorRecording.from_csv(segment['pressure_path'], freq='40ms', start=segment['start'], end=segment['end'])
              for segment in walk_segments]


def plot():
    color_cycle = ['blue', 'red', 'green', 'purple']
    for rec, color in zip(recordings, color_cycle):
        for cycle in rec.gait_cycles:
            plt.plot(cycle.cop_mlap.time, cycle.cop_vel_mlap.ant, color=color)


train = recordings[3:]
train_segments = walk_segments[3:]
all_cycles = [(train_segments[i]['name'], cycle) for i, rec in enumerate(train) for cycle in rec.gait_cycles]
all_feats = [cycle.features for _, cycle in all_cycles]
tree = spatial.KDTree(all_feats)
query_cycle = recordings[2].gait_cycles[0]
query_feats = [cycle.features for cycle in recordings[2].gait_cycles]
res = tree.query(query_feats)
matches = [(all_cycles[i][0], dist) for dist, i in zip(*res)]
