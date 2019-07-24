# Using NumPy style docstrings
import pandas as pd
import numpy as np
import xarray as xr
from datetime import datetime
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

    def __init__(self, df: pd.DataFrame):
        """
        Parameters
        ----------
        df : pandas.DataFrame
            Raw SmartFloor recording
        """
        self.df = df
        self.boards = [Board(df, board_id, x * Board.width, 0)
                       for (x, board_id) in enumerate(Floor.board_map)]
        self.da = self._get_darray()
        self.noise = self.da.isel(time=0)
        self.cop = self._get_cop_dataset(self.denoise())

    @staticmethod
    def from_csv(path):
        columns = ['board_id', 'time', *range(48)]  # column names
        df_raw = pd.read_csv(path, engine='python', names=columns, index_col=1)
        df_raw.index = pd.to_datetime(df_raw.index, unit='ms')
        return Floor(df_raw)

    def range(self) -> Tuple[datetime, datetime]:
        """Get the interpolatable range for the floor

        Returns
        -------
        low : datetime
            The first time at which all boards are recording
        high : datetime
            The last time at which all boards are recording
        """
        lo = max(board.df.index[0] for board in self.boards)
        hi = min(board.df.index[-1] for board in self.boards)
        return lo, hi

    def _get_darray(self) -> xr.DataArray:
        """Get a DataArray mapping of all the boards

        Returns
        -------
        darray : xarray.DataArray
            Readings for the entire floor with x, y, and time dimensions
        """
        da = xr.DataArray(xr.concat([board.da for board in self.boards], dim='x'))
        return da.interpolate_na(dim='time', method='spline').dropna(dim='time')

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

    def denoise(self):
        return self._masked_by_max(self.da - self.noise, 2)
