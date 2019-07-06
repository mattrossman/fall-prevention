import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import mpl_toolkits.mplot3d.axes3d as p3
from matplotlib import animation


df_skeleton = pd.read_csv('jumping-jacks.csv', engine='python', index_col=0)
df_pos_x = df_skeleton.filter(regex="PositionX")
df_pos_y = df_skeleton.filter(regex="PositionY")
df_pos_z = df_skeleton.filter(regex="PositionZ")

# Attaching 3D axis to the figure
fig = plt.figure()
ax = p3.Axes3D(fig)


# Setting the axes properties
ax.set_xlim3d([-1, 1])
ax.set_xlabel('X')

ax.set_ylim3d([-1, 1])
ax.set_ylabel('Y')

ax.set_zlim3d([-1, 1])
ax.set_zlabel('Z')

title = ax.set_title('3D Test')

start_frame = 100
points, = plt.plot(df_pos_x.iloc[start_frame], df_pos_z.iloc[start_frame]-2, df_pos_y.iloc[start_frame], linestyle="", marker="o")


def update_graph(num):
    points.set_data(df_pos_x.iloc[num], df_pos_z.iloc[num]-2)
    points.set_3d_properties(df_pos_y.iloc[num])
    title.set_text('3D Test, time={}'.format(num))


ani = animation.FuncAnimation(fig, update_graph, len(df_skeleton),
                              interval=10, blit=False)
Writer = animation.writers['ffmpeg']
writer = Writer(fps=24, metadata=dict(artist='Me'), bitrate=1800)
ani.save('skeleton.mp4', writer=writer)
plt.show()
