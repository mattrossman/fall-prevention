import pandas as pd
import numpy as np


# Get the entries where body tracking is true
df_raw = pd.read_csv('skeleton.csv', sep=';', header=None)
df_tracked = df_raw[df_raw.iloc[:, 334]]

# Get the chunks of joint columns
num_joints = 25
num_joint_cols = 13
df_stacked_joints = df_tracked.iloc[:, 3:3 + num_joint_cols * num_joints]

# Parse the timestamps
df_stacked_joints.index = pd.to_datetime(df_tracked.iloc[:, 2], unit='ms')
df_stacked_joints.index.name = 'time'

# Split into chunks for each joint
joint_cols = [
    'JointType',
    'TrackingState',
    'PositionX',
    'PositionY',
    'PositionZ',
    'DepthSpacePointX',
    'DepthSpacePointY',
    'ColorSpacePointX',
    'ColorSpacePointY',
    'OrientationX',
    'OrientationY',
    'OrientationZ',
    'OrientationW',
]
joint_dfs = np.split(df_stacked_joints, np.arange(num_joint_cols, num_joint_cols*num_joints, num_joint_cols), axis=1)
for df in joint_dfs:
    df.columns = joint_cols
joint_dfs_dict = {df.iloc[0, 0]: df for df in joint_dfs}
df_joints = pd.concat(joint_dfs_dict, axis=1).drop('JointType', axis=1, level=1)

# df_lleg = df_joints[['HipLeft', 'KneeLeft', 'AnkleLeft', 'FootLeft']]
