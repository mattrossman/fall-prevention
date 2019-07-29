import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime


class KinectRecording:
    def __init__(self, dir_path):
        self.dir_path = dir_path
        self.df = pd.read_csv(f'{dir_path}/colorData.csv', sep=';',
                              names=('frame', 'time_rel', 'time_abs'),
                              index_col='time_abs')
        self.df.index = pd.to_datetime(self.df.index, unit='ms')
        self.df.sort_index(inplace=True)

    def imread(self, dt: datetime, reversed=True):
        index = self.df.index.get_loc(dt, method='ffill')
        entry = self.df.iloc[index]
        filename = f'{entry["time_rel"]}_{entry["frame"]}.jpg'
        img = plt.imread(f'{self.dir_path}/{filename}')
        img = np.flip(img, axis=1) if reversed else img
        return img
