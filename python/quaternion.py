import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import mpl_toolkits.mplot3d.axes3d as p3
from mpl_toolkits.mplot3d import proj3d
from matplotlib.patches import FancyArrowPatch
from pyquaternion import Quaternion


# Get the entries where body tracking is true
df_raw = pd.read_csv('data/poses.csv', sep=';', header=None)
df_tracked = df_raw[df_raw.iloc[:, 334]]  # Column 334 holds a boolean for body tracking
plane = [-0.003449774, 0.9992383, 0.03886962, 0.9575303]  # Floor clip plane

# Get the chunks of joint columns
num_joints = 25
num_joint_cols = 13
df_stacked_joints = df_tracked.iloc[:, 3:3 + num_joint_cols * num_joints]

# Parse the timestamps
df_stacked_joints.index = pd.to_datetime(df_tracked.iloc[:, 2], unit='ms')
df_stacked_joints.index.name = 'Time'

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
df_joints.columns.names = ['Joint', 'Property']
all_joints = df_joints.columns.levels[0]
df_orientations = df_joints.filter(regex='Orientation')
df_positions = df_joints.filter(regex='Position')

# Some useful reference frames from the poses recording
frame_toes = 72785
frame_tpose = 72851
frame_up = 72910


def frame_to_timestamp(frame):
    return pd.Timestamp(df_raw[df_raw[0] == frame].iloc[0][2], unit='ms')


def pos_at_frame(frame):
    """All of the joint position values at the given frame number

    Parameters
    ----------
    frame : int
        Relative frame number (from Kinect2Streams)

    Returns
    -------
    pandas.DataFrame
        Axis 0: Joint
        Axis 1: Dimension (X, Y, Z)
    """
    time = frame_to_timestamp(frame)
    return df_positions.loc[time].unstack()


def orientation_at_frame(frame):
    """All of the joint orientation values at the given frame number

    Parameters
    ----------
    frame : int
        Relative frame number (from Kinect2Streams)

    Returns
    -------
    pandas.DataFrame
        Axis 0: Joint
        Axis 1: Dimension (X, Y, Z, W)
    """
    time = frame_to_timestamp(frame)
    return df_orientations.loc[time].unstack()


def plot_pos(df_pos):
    """ Plot all the joint positions at a certain time in 3D

    df_pos : pandas.DataFrame
        Axis 0: Joints
        Axis 1: Dimension (X, Y, Z)
    """
    xs, ys, zs = df_pos.values.T
    points, = plt.plot(xs, ys, zs, linestyle="", marker="o")
    return points


# Attaching 3D axis to the figure
fig = plt.figure()
ax = p3.Axes3D(fig)

# Setting the axes properties
center = (0, 0, 3.5)
center_x, center_y, center_z = center
lim = 1

ax.set_xlim3d([center_x - lim, center_x + lim])
ax.set_xlabel('X')

ax.set_ylim3d([center_y - lim, center_y + lim])
ax.set_ylabel('Y')

ax.set_zlim3d([center_z - lim, center_z + lim])
ax.set_zlabel('Z')


class Arrow3D(FancyArrowPatch):
    """Found online, used for making 3D arrows"""
    def __init__(self, xs, ys, zs, *args, **kwargs):
        FancyArrowPatch.__init__(self, (0,0), (0,0), *args, **kwargs)
        self._verts3d = xs, ys, zs

    def draw(self, renderer):
        xs3d, ys3d, zs3d = self._verts3d
        xs, ys, zs = proj3d.proj_transform(xs3d, ys3d, zs3d, renderer.M)
        self.set_positions((xs[0],ys[0]),(xs[1],ys[1]))
        FancyArrowPatch.draw(self, renderer)


def plot_vec(vec, pos, **kwargs):
    """Plot a vector as an arrow at the given position"""
    vec_x, vec_y, vec_z = vec
    x0, y0, z0 = pos
    vec = Arrow3D([x0, x0 + vec_x], [y0, y0 + vec_y],
                  [z0, z0 + vec_z], **kwargs)
    ax.add_artist(vec)


def plot_axes():
    """Plot some helper axes at the center"""
    plot_vec((1, 0, 0), center, mutation_scale=10, lw=2, arrowstyle="-|>", color="r")
    plot_vec((0, 1, 0), center, mutation_scale=10, lw=2, arrowstyle="-|>", color="g")
    plot_vec((0, 0, 1), center, mutation_scale=10, lw=2, arrowstyle="-|>", color="b")


def plot_joint_quaternion_axis(joint, **kwargs):
    """Not really used, I don't think the quaternion axis of rotation is much help """
    joint_pos = df_pos.loc[joint]
    q_joint = Quaternion(df_ori.loc[joint])
    plot_vec(q_joint.axis / 5, joint_pos, **kwargs)


def plot_joint_vec(joint, vec, **kwargs):
    """Plot a vector placed at the given joint's position rotated according to the joint quaternion"""
    joint_pos = df_pos.loc[joint]
    q_joint = Quaternion(df_ori.loc[joint])
    plot_vec(q_joint.rotate(vec), joint_pos, **kwargs)


df_pos = pos_at_frame(frame_tpose)
df_ori = orientation_at_frame(frame_tpose)

# Plot the joint positions and a little coordinate system at each joint
plot_pos(df_pos)
for joint in all_joints:
    plot_joint_vec(joint, [0.2, 0, 0], mutation_scale=5, lw=1, arrowstyle="-|>", color='r')
    plot_joint_vec(joint, [0, 0.2, 0], mutation_scale=5, lw=1, arrowstyle="-|>", color='g')
    plot_joint_vec(joint, [0, 0, 0.2], mutation_scale=5, lw=1, arrowstyle="-|>", color='b')

