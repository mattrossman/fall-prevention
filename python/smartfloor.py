# Using NumPy style docstrings
from datetime import datetime
from typing import List, Tuple

import numpy as np
import pandas as pd
import xarray as xr
import re
from scipy.signal import argrelmin, argrelmax
import matplotlib.pyplot as plt
import time
import functools


class Descriptor(object):
    def __init__(self, func):
        self.func = func

    def __get__(self, inst, type=None):
        val = self.func(inst)
        setattr(inst, self.func.__name__, val)
        return val


def reify(func):
    return functools.wraps(func)(Descriptor(func))


def _df_from_csv(path) -> pd.DataFrame:
    columns = ['board_id', 'time', *range(48)]  # column names
    df_raw = pd.read_csv(path, engine='python', names=columns, index_col=1)
    df_raw.index = pd.to_datetime(df_raw.index, unit='ms')
    return df_raw


def _nonnegative_darray(da: xr.DataArray):
    return da.where(da > 0).fillna(0)


def plot_gait_cycles(cycles):
    fig = plt.figure(figsize=(15,7))
    n = len(cycles)
    w = 1
    for i, cycle in enumerate(cycles):
        ax = fig.add_subplot(w, n, i + 1)
        ax.axvline(0, c='r', linestyle=':')
        ax.quiver(cycle.cop_mlap.med, cycle.cop_mlap.ant, cycle.cop_vel_mlap.med, cycle.cop_vel_mlap.ant, range(len(cycle)),
                   angles='xy', units='dots', width=3, pivot='mid', cmap='cool', scale=25, scale_units='xy')
        ax.set_title(cycle.name, size=10)
        ax.set_xlim(-1, 1)


def timeit(method, custom=''):
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()
        if 'log_time' in kw:
            name = kw.get('log_name', method.__name__.upper())
            kw['log_time'][name] = int((te - ts) * 1000)
        else:
            print('%r  %2.2f ms' % (method.__name__, (te - ts) * 1000))
        return result
    return timed


class BoardRecording:
    """A single board on the SmartFloor

    Attributes
    ----------
    df : pandas.DataFrame
        Raw SmartFloor data, filtered for just this board and with the 'board_id' column removed
    id : int
        The board ID number, one of {17, 18, 19, 21}
    x : int
        Where the left-most tile of this board begins on the floor (each tile represents one unit)
    y : int
        Where the bottom-most tile of this board begins on the floor (each tile represents one unit)
    da : xarray.DataArray
        DataArray with x, y, and time dimensions, such that the time dimension can be indexed by datetime
    hz : xarray.DataArray
        The sample rate (in Hz) of the board over time
    Board.sensor_map : numpy.ndarray
        Mapping of sensor ids within the physical layout of a board
    Board.width : int
        Number of tiles a board is wide
    Board.height : int
        Number of tiles a board is high
    """
    sensor_map = [  # arrangement of sensor ids on each board
        [18, 19, 6, 7],
        [17, 16, 9, 8],
        [22, 23, 2, 3],
        [21, 20, 5, 4],
        [27, 28, 43, 44],
        [26, 25, 46, 45],
        [31, 32, 39, 40],
        [30, 29, 42, 41]
    ]
    width, height = 4, 8

    @timeit
    def __init__(self, df_floor: pd.DataFrame, board_id: int, x: int, y: int):
        """
        Parameters
        ----------
        df_floor : pandas.DataFrame
            DataFrame representing raw SmartFloor data
        board_id : int
            The board ID number, one of {17, 18, 18, 21}
        x : int
            Where the left-most tile of this board begins on the floor (each tile represents one unit)
        y : int
            Where the bottom-most tile of this board begins on the floor (each tile represents one unit)
        """
        # Extract this board's data, and remove the (now useless) board ID column
        self.df = df_floor[df_floor['board_id'] == board_id].drop(columns=['board_id'])
        self.id = board_id
        #
        self.x = x
        self.y = y
        self.da = self.get_darray()
        self.hz = self._get_hz(self.da)

    def mapped_stream_arr(self) -> np.ndarray:
        """Get pressure reading streams for each sensor in their assigned location

        Returns
        -------
        data : numpy.ndarray
            A 3D matrix of pressure streams. The axes are as follows:
            axis 0: rows of the board
            axis 1: columns of the board
            axis 2: time
        """
        return np.array([[self.df[sensor_id] for sensor_id in row] for row in BoardRecording.sensor_map])

    def get_darray(self) -> xr.DataArray:
        """Build a DataArray from the current DataFrame data

        Returns
        -------
        da : xarray.DataArray
            DataArray with x, y, and time dimensions, such that the time dimension can be indexed by datetime
        """
        return xr.DataArray(self.mapped_stream_arr(),
                            dims=['y', 'x', 'time'],
                            coords={'time': self.df.index,
                                    'x': np.arange(self.x, self.x + 4),
                                    'y': np.arange(self.y, self.y + 8)[::-1]})

    def update_darray(self):
        """Update the internal DataArray inplace based on current DataFrame data

        """
        self.da = self.get_darray()

    def resample(self, freq: str):
        """Perform linear resampling

        Parameters
        ----------
        freq

        Returns
        -------

        """
        self.df.resample(freq).mean().ffill()

    def _get_hz(self, da):
        ns_diff = (da.time - da.time.shift(time=1))
        board_hz = np.timedelta64(1, 's') / ns_diff
        return board_hz


class FloorRecording:
    """A strip of SmartFloor boards

    Attributes
    ----------
    df : pandas.DataFrame
        Raw SmartFloor recording
    boards : List[BoardRecording]
        Board objects that make up the floor, in left to right order
    da : xarray.DataArray
        Interpolated mapping of all sensor readings with x, y, and time dimensions
        Note that (0, 0) is located at the bottom left of the floor
    noise : xarray.DataArray
        Base pressure readings on the floor over the x, y plane
    Floor.board_map : List[int]
        List of board IDs in the order they appear left to right on the floor
    """

    board_map = [19, 17, 21, 18]

    @timeit
    def __init__(self, df: pd.DataFrame, freq='40ms', start=None, end=None, name=None, trimmed=False):
        """
        Parameters
        ----------
        df : pandas.DataFrame
            Raw SmartFloor recording
        """
        self.df = df
        self.boards = [BoardRecording(df, board_id, x * BoardRecording.width, 0)
                       for (x, board_id) in enumerate(FloorRecording.board_map)]
        all_start, all_end = FloorRecording._range(self.boards)
        self.freq = pd.Timedelta(freq)
        self.name = name
        self.da = self._get_darray()
        self.noise = self.da.isel(time=0)
        start = start or all_start
        end = end or all_end
        if trimmed:
            start, end = self.loaded_window
        sample_times = pd.date_range(start, end, freq=pd.Timedelta(freq))
        self.samples = self.da.interp(time=sample_times)

    @staticmethod
    def from_csv(path, name=None, *args, **kwargs):
        name = name or re.match(r'.*/(.*)\.csv', path).groups()[0]  # By default use the csv file name
        return FloorRecording(_df_from_csv(path), name=name, *args, **kwargs)

    def __repr__(self):
        return f'<FloorRecording {self.name}>'

    @staticmethod
    def _range(boards) -> Tuple[datetime, datetime]:
        """Get the interpolatable range for the floor

        Returns
        -------
        low : datetime
            The first time at which all boards are recording
        high : datetime
            The last time at which all boards are recording
        """
        lo = max(board.df.index[0] for board in boards)
        hi = min(board.df.index[-1] for board in boards)
        return lo, hi

    def _get_darray(self) -> xr.DataArray:
        """Get a DataArray mapping of all the boards

        Returns
        -------
        darray : xarray.DataArray
            Readings for the entire floor with x, y, and time dimensions
        """
        da = xr.concat([board.da for board in self.boards], dim='x')
        da = da.assign_coords(y=np.arange(0, 8)[::-1], x=np.arange(0, 16))
        return _nonnegative_darray(da.interpolate_na(dim='time', method='linear').dropna(dim='time'))

    @staticmethod
    def _get_cop_dataset(da: xr.DataArray) -> xr.Dataset:
        """Get a dataset containing the x,y coordinates of the center of pressure over time

        Parameters
        ----------
        da : xarray.DataArray
            Full mapping of the floor data

        Returns
        -------
        ds : xarray.Dataset
            Contains x, y, and magnitude data variables along a time dimension
        """
        x_cop = (da * da.x).sum(dim=('x', 'y')) / da.sum(dim=('x', 'y'))
        y_cop = (da * da.y).sum(dim=('x', 'y')) / da.sum(dim=('x', 'y'))
        magnitude = da.sum(dim=('x', 'y'))
        return xr.Dataset({'x': x_cop, 'y': y_cop, 'magnitude': magnitude})

    def _masked_by_max(self, da: xr.DataArray, dist: int) -> xr.DataArray:
        """Mask away values that are a certain distance away from the point of maximum pressure

        Parameters
        ----------
        da : xarray.DataArray
            Full mapping of the floor data
        dist : int
            Maximum permitted distance from the point of highest pressure

        Returns
        -------
        mask : xarray.DataArray
            Like the input, but values outside the desired square are set to zero
        """
        stacked = da.stack(tile=('x', 'y'))
        coords_max = stacked.tile.isel(tile=stacked.argmax('tile'))
        x_max, y_max = zip(*coords_max.data)
        ds = xr.Dataset({'x': (['time'], list(x_max)), 'y': (['time'], list(y_max))}, coords={'time': stacked.time})
        masked = (da.where((abs(da.x - ds.x) <= dist)).where(abs(da.y - ds.y) <= dist))
        return masked

    def _denoise(self, da: xr.DataArray):
        init_pass = _nonnegative_darray(da - self.noise)
        return self._masked_by_max(init_pass, 2).fillna(0)

    @reify
    def pressure(self):
        return self._denoise(self.samples)

    @reify
    def cop(self):
        return self._get_cop_dataset(self.pressure)

    @reify
    def cop_vel(self):
        cop = self.cop
        return (cop.shift(time=-1) - cop).rolling(time=2).mean() / (self.freq / pd.Timedelta('1s'))

    @reify
    def cop_vel_mag(self):
        vel = self.cop_vel
        return np.sqrt(np.square(vel.x) + np.square(vel.y))

    @reify
    def cop_vel_mag_roc(self):
        """Rate of change of velocity magnitude (change in speed, change in acceleration in direction of motion"""
        speed = self.cop_vel_mag
        return (speed.shift(time=-1) - speed).rolling(time=2).mean() / (self.freq / pd.Timedelta('1s'))

    @reify
    def cop_accel(self):
        vel = self.cop_vel
        return (vel.shift(time=-1) - vel).rolling(time=2).mean() / (self.freq / pd.Timedelta('1s'))

    @reify
    def cop_accel_mag(self):
        """Magnitude of the COP acceleration vector"""
        accel = self.cop_accel
        return np.sqrt(np.square(accel.x) + np.square(accel.y))

    @reify
    def cop_accel_mag_roc(self):
        """Rate of change of velocity magnitude (change in speed, change in acceleration in direction of motion"""
        accel_mag = self.cop_accel_mag
        return (accel_mag.shift(time=-1) - accel_mag).rolling(time=2).mean() / (self.freq / pd.Timedelta('1s'))

    @reify
    def cop_jerk(self):
        vel = self.cop_vel
        return (vel.shift(time=-1) - vel).rolling(time=2).mean() / (self.freq / pd.Timedelta('1s'))

    @reify
    def cop_jerk_mag(self):
        jerk = self.cop_jerk
        return np.sqrt(np.square(jerk.x) + np.square(jerk.y))

    @reify
    def _anchors(self):
        """Points along COP trajectory with minimal motion, good for marking a foot position
        """
        cop_speed = self.cop_vel_mag.rolling(time=10, center=True).mean().dropna('time')
        ixs = argrelmin(cop_speed.values, order=3)[0]
        return cop_speed.isel(time=ixs)

    @reify
    def _weight_shifts(self):
        """ Points of highest speed increase
        """
        cop_delta_speed = self.cop_vel_mag_roc.rolling(time=3, center=True).mean().dropna('time')
        ixs = argrelmax(cop_delta_speed.values, order=3)[0]
        speed_shifts = cop_delta_speed.isel(time=ixs)
        return speed_shifts[speed_shifts > 3]

    @reify
    def _heelstrikes(self):
        heel_dir = self.footstep_positions.reindex_like(self._weight_shifts, method='bfill')
        heel_dir = heel_dir.fillna(heel_dir.shift(time=2))  # Assume feet alternation
        return heel_dir.where(heel_dir != heel_dir.shift(time=1)).dropna('time')  # Disallow repeated values

    @reify
    def footstep_positions(self):
        """Positions of valid foot anchors along with their left/right labeling
        """
        ds = xr.Dataset({'anchors': self._anchors, 'heels': self._weight_shifts})
        valid_anchors = np.logical_and(ds.anchors.notnull(), ds.heels.shift(time=-1).notnull())
        steps = self.cop.sel(time=ds.anchors[valid_anchors].time)
        return steps.assign(dir=FloorRecording._step_dirs(steps))

    @staticmethod
    def _step_dirs(steps: xr.Dataset):
        gait_cycles = steps.rolling(time=3).construct('window').dropna('time').groupby('time')
        feet = xr.DataArray([FloorRecording._middle_foot_dir(sl) for _, sl in gait_cycles], dims='time',
                            coords={'time': steps.time[1:-1]})
        # Assume first and last steps follow typical alternation
        feet = feet.reindex_like(steps)
        return feet.fillna(feet.shift(time=2)).fillna(feet.shift(time=-2))

    @staticmethod
    def _middle_foot_dir(cycle: xr.Dataset):
        """Determine whether the middle foot in the cycle is a right or left foot
        """
        step1 = cycle.isel(window=0)
        step2 = cycle.isel(window=1)
        step3 = cycle.isel(window=2)
        v_step = np.array([step2.x - step1.x, step2.y - step1.y])
        v_stride = np.array([step3.x - step1.x, step3.y - step1.y])
        # Dot product of v_stride and 90CCW rotation of v_step
        dir = v_stride.dot([-v_step[1], v_step[0]])
        return 'right' if dir > 0 else 'left'

    @reify
    def footstep_cycles(self):
        """Groups of 3 footsteps, starting and ending on the right foot
        """
        footsteps = self.footstep_positions
        cycle_groups = footsteps.rolling(time=3).construct('window').dropna('time').groupby('time')
        cycles = xr.concat(np.array(list(cycle_groups))[:, 1], 'cycle')
        return cycles.where(cycles.isel(window=0).dir == 'right').dropna('cycle')

    @reify
    def step_triplets(self):
        """Groups of 3 footsteps, starting and ending on the right foot
        """
        heels = self._heelstrikes
        heels = heels.assign(step_time=heels.time)  # The time coordinates will not be so useful later
        cycle_groups = heels.rolling(time=3).construct('window').dropna('time').groupby('time')
        cycles = xr.concat(np.array(list(cycle_groups))[:, 1], 'cycle')
        return cycles.where(cycles.isel(window=0).dir == 'right').dropna('cycle')

    @reify
    def step_triplet_windows(self):
        return [(cycle.step_time[0].values, cycle.step_time[-1].values)
                for _, cycle in self.step_triplets.groupby('cycle')]

    @reify
    def walk_line(self):
        """The overall straight trajectory of the subject

        Returns
        -------
        start: xarray.Dataset
        end: xarray.Dataset
        """
        footsteps = self.footstep_positions
        start = footsteps.isel(time=slice(None,2)).mean('time')
        end = footsteps.isel(time=slice(-2,None)).mean('time')
        return start[['x', 'y']], end[['x', 'y']]

    def _to_mlap(self, ds: xr.Dataset):
        """Convert x, y positions to mediolateral, anteroposterior positions along walk line

        Returns
        -------
        ds: xr.Dataset
            Dataset containing (med, ant) data variables, with the origin at the start of the walk line
        """
        start, end = self.walk_line
        v_line = (end - start).to_array()
        v_rot = np.array([v_line[1], -v_line[0]])  # Rotate v_line 90 degrees clockwise
        c, s = v_rot / np.linalg.norm(v_rot)  # Cosine and sine from unit vector
        rot_matrix = np.array([[c, s], [-s, c]])  # Clockwise rotation matrix
        med, ant = rot_matrix.dot(ds[['x', 'y']].to_array().values)
        return xr.Dataset({'med': (['time'], med), 'ant': (['time'], ant)},  {'time': ds.time})

    @reify
    def cop_mlap(self):
        start, end = self.walk_line
        return self._to_mlap(self.cop - start)

    @reify
    def cop_mlap_cycles(self):
        ds = self.cop_mlap
        return [ds.sel(time=slice(*w)) for w in self.step_triplet_windows]

    @reify
    def cop_vel_mlap(self):
        return self._to_mlap(self.cop_vel)

    @reify
    def cop_vel_mlap_cycles(self):
        ds = self.cop_vel_mlap
        return [ds.sel(time=slice(*w)) for w in self.step_triplet_windows]

    @reify
    def gait_cycles(self):
        return np.array([GaitCycle(self, window, name=f'{self.name}_c{i}')
                         for i, window in enumerate(self.step_triplet_windows)])

    @reify
    def loaded_window(self):
        mag = self._denoise(self.da).sum(('x', 'y'))
        loaded_range = mag.where(mag > mag.mean(), drop=True).time.values
        return loaded_range[0], loaded_range[-1]


class GaitCycle:
    """Gait cycle normalized to a fixed number of samples"""
    def __init__(self, floor, window, name=None):
        self.floor = floor
        self.date_window = window
        self.date_range = pd.date_range(*window, periods=len(self))
        self.name = name

    def __len__(self):
        return 40

    def __repr__(self):
        return f'<GaitCycle {self.name}>'

    def _pos_dist(self, other):
        pos_diff = self.cop_mlap - other.cop_mlap
        return np.sqrt(np.square(pos_diff).med + np.square(pos_diff).ant)

    def _vel_dist(self, other):
        vel_diff = self.cop_vel_mlap - other.cop_vel_mlap
        return np.sqrt(np.square(vel_diff).med + np.square(vel_diff).ant)

    def dist(self, other):
        return self._pos_dist(other).sum() + self._vel_dist(other).mean()

    @reify
    def ant_scale(self):
        pos_i = self.floor.cop_mlap.interp(time=self.date_window[0])
        pos_f = self.floor.cop_mlap.interp(time=self.date_window[1])
        dist = pos_f - pos_i
        return dist.ant.item()

    @reify
    def med_scale(self):
        pos = self.floor.cop_mlap.interp(time=self.date_range)
        pos_left = pos.med.min()
        pos_right = pos.med.max()
        return max(abs(pos_left), abs(pos_right)) * 2

    @reify
    def ant_offset(self):
        pos_i = self.floor.cop_mlap.interp(time=self.date_window[0])
        return pos_i.ant.item()

    @reify
    def cop_mlap(self):
        pos = self.floor.cop_mlap.interp(time=self.date_range).drop('time')
        pos['med'] = pos.med / self.med_scale
        pos['ant'] = pos.ant - self.ant_offset
        pos['ant'] = pos.ant / self.ant_scale
        return pos

    @reify
    def cop_vel_mlap(self):
        vel_mlap = self.floor.cop_vel_mlap.interp(time=self.date_range).drop('time')
        vel_mlap['med'] = vel_mlap.med / self.med_scale
        vel_mlap['ant'] = vel_mlap.ant / self.ant_scale
        return vel_mlap

    @reify
    def duration(self):
        return self.date_range[-1] - self.date_range[0]

    @reify
    def features(self):
        """ DEPRECATED """
        vel_mlap = self.cop_vel_mlap
        pos_mlap = self.cop_mlap
        return np.concatenate((pos_mlap.med, pos_mlap.ant, vel_mlap.med, vel_mlap.ant))


class FloorRecordingBatch:
    def __init__(self, floors):
        self.floors = floors

    @staticmethod
    def from_csv(paths: List[str], *args, **kwargs):
        """Create a batch of floor recordings from a list of .csv file paths

        Parameters
        ----------
        paths : List[str]
            File paths to the raw smartfloor .csv recordings
        *args, **kwargs:
            Arguments to be passed to FloorRecording constructor for each path

        Returns
        -------
        FloorRecordingBatch
        """
        return FloorRecordingBatch(floors=[FloorRecording.from_csv(path, *args, **kwargs)
                                           for path in paths])

    @reify
    def gait_cycles(self):
        return np.hstack([floor.gait_cycles for floor in self.floors])

    @reify
    def gait_cycle_batch(self):
        return GaitCycleBatch(self.gait_cycles)


class GaitCycleBatch:
    def __init__(self, cycles):
        self.cycles = np.array(cycles)

    def __len__(self):
        return len(self.cycles)

    def __getitem__(self, index):
        return self.cycles[index]

    def __iter__(self):
        return self.cycles.__iter__()

    def query_cycle(self, other: 'GaitCycle'):
        """ Order the gait cycles by their similarity to a query cycle

        Parameters
        ----------
        other : GaitCycle
            Cycle to lookup

        Returns
        -------
        distances : List[int]
            Distances of each neighbor from the query
        neighbors : GaitCycleBatch
            Cycles in this batch in ascending order of distance from the query
        """
        distances = np.array([cycle.dist(other) for cycle in self.cycles])
        neighbors = self.cycles[distances.argsort()]
        return np.sort(distances), GaitCycleBatch(neighbors)

    def query_batch(self, other: 'GaitCycleBatch'):
        return np.moveaxis(np.array([self.query_cycle(cycle) for cycle in other]), 1, 0)

    def partition_names(self, pattern, reverse=False):
        """Split the batch into two batches based on a naming pattern

        Parameters
        ----------
        pattern : str
            Regex string pattern to match as hits

        Returns
        -------
        hits : GaitCycleBatch
            Cycles whose name matches the pattern
        misses : GaitCycleBatch
            Cycles whose name doesn't match the pattern
        """
        regex_hit = re.compile(pattern)
        hits = GaitCycleBatch([cycle for cycle in self.cycles if regex_hit.match(cycle.name)])
        misses = GaitCycleBatch([cycle for cycle in self.cycles if not regex_hit.match(cycle.name)])
        return (hits, misses) if not reverse else (misses, hits)
