# Using NumPy style docstrings
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime


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
        Numbed of tiles a board is high
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

    def mapped_entry_arr(self, ix: datetime):
        """Get an entry from this board with readings mapped to their correct array positions

        Parameters
        ----------
        ix : datetime
            The entry index to look up

        Returns
        -------
        arr : numpy.ndarray
            A 2D array of readings at this index, where each root element is a row on the board
        """
        return np.array([[self.df.loc[ix][sensor_id] for sensor_id in row] for row in Board.sensor_map])

    def mapped_entry_df(self, ix: datetime):
        """Get an entry from this board as a DataFrame containing the appropriate coordinates of each entry

        Parameters
        ----------
        ix : datetime
            The entry index to look up

        Returns
        -------
        df : pandas.DataFrame
            Contains columns for [value, x, y]
        """
        arr = self.mapped_entry_arr(ix=ix)
        data = [{'value': val, 'x': x, 'y': y} for (y, row) in enumerate(arr) for (x, val) in enumerate(row)]
        return pd.DataFrame(data)


columns = ['board_id', 'time', *range(48)]  # column names

# Import the raw pressure data, use timestamps as index, and parse them as Unix milliseconds
df_raw = pd.read_csv('1_131.2lbs.csv', engine='python', names=columns, index_col=1)
df_raw.index = pd.to_datetime(df_raw.index, unit='ms')
b17 = Board(df_raw, board_id=17, x=0, y=0)
dt = b17.df.index[0]