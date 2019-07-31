# Using NumPy style docstrings
import pandas as pd
import numpy as np
import xarray as xr
import xarray.ufuncs as xu
from datetime import datetime
from scipy.signal import argrelmin, argrelmax
from typing import List, Tuple


class Board:
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
        Where the top-most tile of this board begins on the floor (each tile represents one unit)
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
            Where the top-most tile of this board begins on the floor (each tile represents one unit)
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
        return np.array([[self.df[sensor_id] for sensor_id in row] for row in Board.sensor_map])

    def get_darray(self) -> xr.DataArray:
        """Build a DataArray from the current DataFrame data

        Returns
        -------
        da : xarray.DataArray
            DataArray with x, y, and time dimensions, such that the time dimension can be indexed by datetime
        """
        return xr.DataArray(self.mapped_stream_arr(),
                            dims=['y', 'x', 'time'],
                            coords={'time': self.df.index})

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


class Floor:
    """A strip of SmartFloor boards

    Attributes
    ----------
    df : pandas.DataFrame
        Raw SmartFloor recording
    boards : List[Board]
        Board objects that make up the floor, in left to right order
    da : xarray.DataArray
        Interpolated mapping of all sensor readings with x, y, and time dimensions
    noise : xarray.DataArray
        Base pressure readings on the floor over the x, y plane
    cop : xarray.Dataset
        Center of pressure over time containing x, y, and magnitude variables
    Floor.board_map : List[int]
        List of board IDs in the order they appear left to right on the floor
    """

    board_map = [19, 17, 21, 18]

    def __init__(self, df: pd.DataFrame, freq='40ms', start=None, end=None):
        """
        Parameters
        ----------
        df : pandas.DataFrame
            Raw SmartFloor recording
        """
        self.df = df
        self.boards = [Board(df, board_id, x * Board.width, 0)
                       for (x, board_id) in enumerate(Floor.board_map)]
        all_start, all_end = Floor._range(self.boards)
        self.freq = pd.Timedelta(freq)
        start = start or all_start
        end = end or all_end
        sample_times = pd.date_range(start, end, freq=pd.Timedelta(freq))
        self.da = self._get_darray()
        self.noise = self.da.isel(time=0)
        self.samples = self.da.interp(time=sample_times)

    @staticmethod
    def from_csv(path, *args,**kwargs):
        return Floor(_df_from_csv(path), *args, **kwargs)

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
        da = xr.DataArray(xr.concat([board.da for board in self.boards], dim='x'))
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

    @property
    def pressure(self):
        return self._denoise(self.samples)

    @property
    def _cop_abs(self):
        return self._get_cop_dataset(self.pressure)

    @property
    def cop_vel(self):
        cop = self._cop_abs
        return (cop - cop.shift(time=1)) / (self.freq / pd.Timedelta('1s'))

    @property
    def cop_speed(self):
        vel = self.cop_vel
        return xu.sqrt(xu.square(vel.x) + xu.square(vel.y))

    @property
    def cop_delta_speed(self):
        speed = self.cop_speed
        return (speed - speed.shift(time=1)) / (self.freq / pd.Timedelta('1s'))

    @property
    def cop_accel(self):
        vel = self.cop_vel
        return (vel - vel.shift(time=1)) / (self.freq / pd.Timedelta('1s'))
    
    @property
    def cop_accel_scalar(self):
        accel = self.cop_accel
        return xu.sqrt(xu.square(accel.x) + xu.square(accel.y))

    @property
    def _anchors(self):
        """Points along COP trajectory with minimal motion, good for marking a foot position
        """
        cop_speed = self.cop_speed.rolling(time=10, center=True).mean().dropna('time')
        ixs = argrelmin(cop_speed.values, order=3)[0]
        return cop_speed.isel(time=ixs)

    @property
    def _weight_shifts(self):
        """ Points of highest velocity increase
        """
        cop_delta_speed = self.cop_delta_speed.rolling(time=10, center=True).mean().dropna('time')
        ixs = argrelmax(cop_delta_speed.values, order=3)[0]
        return cop_delta_speed.isel(time=ixs)

    @property
    def footsteps(self):
        """Positions of valid foot anchors along with their left/right labeling
        """
        ds = xr.Dataset({'anchors': self._anchors, 'motions': self._weight_shifts[self._weight_shifts > 3]})
        valid_anchors = xu.logical_and(ds.anchors.notnull(), ds.motions.shift(time=-1).notnull())
        steps = self._cop_abs.sel(time=ds.anchors[valid_anchors].time)
        return steps.assign(dir=self._step_dirs(steps))

    @staticmethod
    def _step_dirs(steps: xr.Dataset):
        gait_cycles = steps.rolling(time=3).construct('window').dropna('time').groupby('time')
        feet = xr.DataArray([Floor._starting_foot(sl) for _, sl in gait_cycles], dims='time',
                            coords={'time': steps.time[1:-1]})
        # Assume first and last steps follow typical alternation
        feet = feet.reindex_like(steps)
        feet[0] = 'left' if feet[1].item() == 'right' else 'right'
        feet[-1] = 'left' if feet[-2].item() == 'right' else 'right'
        return feet

    @staticmethod
    def _starting_foot(cycle: xr.Dataset):
        """Determine whether the middle foot in the cycle is a right or left foot
        """
        step1 = cycle.isel(window=0)
        step2 = cycle.isel(window=1)
        step3 = cycle.isel(window=2)
        v_step = np.array([step2.x - step1.x, step2.y - step1.y])
        v_stride = np.array([step3.x - step1.x, step3.y - step1.y])
        # Dot product of v_step and 90CCW rotation of v_stride
        dir = v_step[0] * -v_stride[1] + v_step[1] * v_stride[0]
        return 'right' if dir > 0 else 'left'

    @property
    def gait_cycles(self):
        """Groups of 3 footsteps, starting and ending on the right foot
        """
        footsteps = self.footsteps
        gait_cycles = footsteps.rolling(time=3).construct('window').dropna('time').groupby('time')
        return filter(lambda tup: tup[1].dir[0] == 'right', gait_cycles)

    @property
    def walk_line(self):
        """The overall straight trajectory of the subject

        Returns
        -------
        start: xarray.Dataset
        end: xarray.Dataset
        """
        footsteps = self.footsteps
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
        v_line = end - start
        line_length = np.linalg.norm((end - start).to_array())
        line_norm = v_line / line_length
        rot_matrix = np.array([[(-line_norm.y).item(), (-line_norm.x).item()],
                               [line_norm.x.item(), (-line_norm.y).item()]])
        rotated = ds[['x', 'y']].to_array().values.T @ rot_matrix.T
        med, ant = rotated.T
        return xr.Dataset({'med': (['time'], med), 'ant': (['time'], ant)},  {'time': ds.time})



    def trim(self, start, end):
        """[DEPRECATED] Trim the time dimension of the data array

        Parameters
        ----------
        start : str, datetime
        end : str, datetime
            The bounds to slice between, can be formatted as a string for pandas to parse
        """
        self.da = self.da.sel(time=slice(pd.Timestamp(start), pd.Timestamp(end)))


def _df_from_csv(path) -> pd.DataFrame:
    columns = ['board_id', 'time', *range(48)]  # column names
    df_raw = pd.read_csv(path, engine='python', names=columns, index_col=1)
    df_raw.index = pd.to_datetime(df_raw.index, unit='ms')
    return df_raw


def _nonnegative_darray(da: xr.DataArray):
    return da.where(da > 0).fillna(0)
