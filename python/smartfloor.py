# Using NumPy style docstrings
import pandas as pd
import numpy as np
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
        The board ID number, one of {17, 18, 18, 21}
    x : int
        Where the left-most tile of this board begins on the floor (each tile represents one unit)
    y : int
        Where the top-most tile of this board begins on the floor (each tile represents one unit)
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

    def lookup(self, dt: datetime) -> pd.Series:
        """Lookup an entry on the board, and interpolate if it doesn't exist

        Parameters
        ----------
        dt : datetime
            Timestamp to lookup

        Raises
        ------
        KeyError
            When the lookup key is outside of the interpolatable range

        Returns
        -------
        data : pandas.Series
            Either the exact entry at the given timestamp, or an interpolated estimate
        """
        try:  # Exact match
            return self.df.loc[dt]
        except KeyError:  # Perform interpolation
            prev_iloc = self.df.index.get_loc(dt, method='ffill')
            s_prev = self.df.iloc[prev_iloc]
            s_next = self.df.iloc[prev_iloc + 1]
            progress = (dt - s_prev.name) / (s_next.name - s_prev.name)
            s_interpolate = s_prev + progress * (s_next - s_prev)
            s_interpolate.name = dt
            return s_interpolate

    def lookup_mapped_arr(self, dt: datetime) -> np.ndarray:
        """Get an entry from this board with readings mapped to their correct array positions

        Parameters
        ----------
        dt : datetime
            The entry index to look up

        Returns
        -------
        arr : numpy.ndarray
            A 2D array of readings at this index, where each root element is a row on the board
        """
        return np.array([[self.lookup(dt)[sensor_id] for sensor_id in row] for row in Board.sensor_map])

    def lookup_mapped_df(self, dt: datetime) -> pd.DataFrame:
        """Get an entry from this board as a DataFrame containing the appropriate coordinates of each entry

        Parameters
        ----------
        dt : datetime
            The entry index to look up

        Returns
        -------
        df : pandas.DataFrame
            Contains columns for [value, x, y]
        """
        arr = self.lookup_mapped_arr(dt=dt)
        data = [{'x': x + self.x, 'y': y + self.y, 'value': val}
                for (y, row) in enumerate(arr) for (x, val) in enumerate(row)]
        return pd.DataFrame(data)


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

    def range(self) -> Tuple[datetime, datetime]:
        """Get the interpolatable range for the floor

        Returns
        -------
        low : datetime
            The first time at which all boards are recording
        high : datetime
            The last time at which all boards are recording
        """
        lo = min(board.df.index[0] for board in self.boards)
        hi = max(board.df.index[-1] for board in self.boards)
        return lo, hi

    def lookup_mapped_arr(self, dt: datetime) -> np.ndarray:
        """Get an entry from the floor with readings mapped to their correct array positions

        Parameters
        ----------
        dt : datetime
            The entry index to look up

        Returns
        -------
        data : numpy.ndarray
            A 2D array of readings at this timestamp, where each root element is a row on the floor
        """
        arrays = [board.lookup_mapped_arr(dt) for board in self.boards]
        return np.concatenate(arrays, axis=1)

    def lookup_mapped_df(self, dt: datetime) -> pd.DataFrame:
        """Get an entry from the floor as a DataFrame containing the appropriate coordinates of each entry

        Parameters
        ----------
        dt : datetime
            The entry index to look up

        Returns
        -------
        data : pandas.DataFrame
            Contains columns for [value, x, y]
        """
        arr = self.lookup_mapped_arr(dt=dt)
        data = [{'x': x, 'y': y, 'value': val}
                for (y, row) in enumerate(arr) for (x, val) in enumerate(row)]
        return pd.DataFrame(data)

    def cop(self, dt: datetime) -> Tuple[float, float]:
        """Get the center of pressure on the floor at a given time

        Parameters
        ----------
        dt : timestamp to lookup

        Raises
        ------
        KeyError
            When the lookup key is outside of the interpolatable range

        Returns
        -------
        x_cop : float
        y_cop : float
        """
        df_mapped = self.lookup_mapped_df(dt)
        x_cop = (df_mapped['x'] * df_mapped['value']).sum() / df_mapped['value'].sum()
        y_cop = (df_mapped['y'] * df_mapped['value']).sum() / df_mapped['value'].sum()
        return x_cop, y_cop


columns = ['board_id', 'time', *range(48)]  # column names

# Import the raw pressure data, use timestamps as index, and parse them as Unix milliseconds
df_raw = pd.read_csv('1_131.2lbs.csv', engine='python', names=columns, index_col=1)
df_raw.index = pd.to_datetime(df_raw.index, unit='ms')
b17 = Board(df_raw, board_id=17, x=0, y=0)
dt = b17.df.index[0]
dt2 = b17.df.index[5]
dt_in = pd.Timestamp('2018-11-11 01:40:46')
floor = Floor(df_raw)
