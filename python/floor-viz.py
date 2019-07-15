import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import animation
from functools import reduce

columns = ['board_id', 'time', *range(48)]  # column names

# Import the raw pressure data, use timestamps as index, and parse them as Unix milliseconds
df_raw = pd.read_csv('1_131.2lbs.csv', engine='python', names=columns, index_col=1)
df_raw.index = pd.to_datetime(df_raw.index, unit='ms')

# Separate out the data for each panel
df_board_19 = df_raw[df_raw['board_id'] == 19].drop(columns=['board_id'])
df_board_17 = df_raw[df_raw['board_id'] == 17].drop(columns=['board_id'])
df_board_21 = df_raw[df_raw['board_id'] == 21].drop(columns=['board_id'])
df_board_18 = df_raw[df_raw['board_id'] == 18].drop(columns=['board_id'])

# Resample the boards at constant 25 Hz (40 ms^-1) frequency
df_board_19 = df_board_19.resample('40ms').mean().ffill()
df_board_17 = df_board_17.resample('40ms').mean().ffill()
df_board_21 = df_board_21.resample('40ms').mean().ffill()
df_board_18 = df_board_18.resample('40ms').mean().ffill()

# Get all boards on the same indices
common_indices = reduce(lambda acc, ix: acc.intersection(ix), [df_board_19.index, df_board_17.index, df_board_21.index, df_board_18.index])
df_board_19 = df_board_19.loc[common_indices]
df_board_17 = df_board_17.loc[common_indices]
df_board_21 = df_board_21.loc[common_indices]
df_board_18 = df_board_18.loc[common_indices]

# Calibrate for initial noise
df_board_19 = df_board_19 - df_board_19.iloc[0:10].min()
df_board_17 = df_board_17 - df_board_17.iloc[0:10].min()
df_board_21 = df_board_21 - df_board_21.iloc[0:10].min()
df_board_18 = df_board_18 - df_board_18.iloc[0:10].min()


# Misc. floor information for future reference
floor_board_map = [19, 17, 21, 18]  # order of board ids
board_w = 4  # how many tiles each board is wide
board_h = 8  # how many tiles each board is high


def board_entry_to_array(s_board: pd.Series) -> np.array:
    # given a raw data entry (row), return an array of readings with sensors in their proper positions
    return np.array([[s_board.iloc[sensor_id] for sensor_id in row] for row in board_sensor_map])


board_sensor_map = [  # arrangement of sensor ids on each board
    [18, 19, 6, 7],
    [17, 16, 9, 8],
    [22, 23, 2, 3],
    [21, 20, 5, 4],
    [27, 28, 43, 44],
    [26, 25, 46, 45],
    [31, 32, 39, 40],
    [30, 29, 42, 41]
]

class Board:
    floor_board_map = [19, 17, 21, 18]  # order of board ids

    def __init__(self, df_floor, board_id):
        self.df_floor = df_floor
        self.df = df_floor[df_floor['board_id'] == board_id].drop(columns=['board_id'])
        self.id = board_id
        self.x_offset = floor_board_map.index(board_id) * board_w
        self.points = None

    def get_mapped_entry_array(self, entry):
        # given a raw data entry (row), return an array of readings with sensors in their proper positions
        return np.array([[self.df.iloc[entry][sensor_id] for sensor_id in row] for row in board_sensor_map])

    def init_plot(self):
        # The order is important! you must complete each x sequence (row) before incrementing y
        coordinates = list((x, y) for y in range(board_h) for x in range(board_w))
        xs, ys = zip(*coordinates)
        xs = np.array(xs) + self.x_offset
        rough_max = self.df_floor.iloc[:, 1:].quantile(0.95).quantile(0.95)
        vals = self.get_mapped_entry_array(0).flatten()
        self.points = plt.scatter(xs, ys[::-1], c=vals, cmap='Greys', vmin=5, vmax=rough_max)
        plt.text(self.x_offset, 5, f'Panel {self.id}', color='red')

    def update_plot(self, frame):
        vals = self.get_mapped_entry_array(frame).flatten()
        self.points.set_array(vals)


fig = plt.figure()
plt.gca().set_aspect('equal', adjustable='box')  # make x and y scale equal
plt.title('Frame: N/A')
board_19 = Board(df_raw, 19)
board_17 = Board(df_raw, 17)
board_21 = Board(df_raw, 21)
board_18 = Board(df_raw, 18)
board_19.init_plot()
board_17.init_plot()
board_21.init_plot()
board_18.init_plot()


def update_plot(i):
    plt.title(f'Frame: {i}')
    board_19.update_plot(i)
    board_17.update_plot(i)
    board_21.update_plot(i)
    board_18.update_plot(i)


ani = animation.FuncAnimation(fig, update_plot, len(common_indices),
                              interval=40, blit=False)


def write_animaton():
    Writer = animation.writers['ffmpeg']
    writer = Writer(fps=25, metadata=dict(artist='Me'), bitrate=1800)
    ani.save('walk.mp4', writer=writer)

