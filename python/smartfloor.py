# Using NumPy style docstrings
import pandas as pd
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
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
        self.ds = self.get_dataset()
        self.da = self.get_darray()
        self.cop = self.get_cop_dataset()

    def get_dataset(self):
        ds = xr.Dataset({f'board{board.id}': board.da for board in self.boards})
        return ds.interpolate_na(dim='time', method='linear').dropna(dim='time')

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

    def get_darray(self):
        """Get a DataArray mapping of the entire floor from the current DataSet

        Returns
        -------
        darray : xarray.DataArray
            Readings for the entire floor with x, y, and time dimensions

        Notes
        -----
        This might be a better approach for later:
        http://xarray.pydata.org/en/stable/generated/xarray.combine_by_coords.html
        """
        return xr.concat(self.ds.data_vars.values(), dim='x')

    def get_cop_dataset(self):
        """Get a dataset containing the x,y coordinates of the center of pressure over time

        Returns
        -------
        ds : xarray.Dataset
            Contains x and y data variables along a time dimension
        """
        x_cop = (self.da * self.da.x).sum(dim=('x', 'y')) / self.da.sum(dim=('x', 'y'))
        y_cop = (self.da * self.da.y).sum(dim=('x', 'y')) / self.da.sum(dim=('x', 'y'))
        return xr.Dataset({'x': x_cop, 'y': y_cop})


# Import the raw pressure data, use timestamps as index, and parse them as Unix milliseconds
columns = ['board_id', 'time', *range(48)]  # column names
df_raw = pd.read_csv('1_131.2lbs.csv', engine='python', names=columns, index_col=1)
df_raw.index = pd.to_datetime(df_raw.index, unit='ms')

floor = Floor(df_raw)
lo, hi = floor.range()
safe_range = pd.date_range(start=lo, end=hi, freq='40ms')
da = floor.da