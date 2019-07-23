import pandas as pd
from matplotlib import animation
import matplotlib.pyplot as plt
from smartfloor import Floor


floor = Floor.from_csv('1_131.2lbs.csv')
lo, hi = floor.range()
safe_range = pd.date_range(start=lo, end=hi, freq='40ms')

fig = plt.figure()
quad = floor.da.isel(time=100).plot(vmin=0, vmax=1023)
plt.gca().set_aspect('equal', adjustable='box')  # make x and y scale equal
plt.gca().invert_yaxis()


def update_quad_data(args):
    i, dt = args
    plt.title(f'Time: {dt.strftime("%H:%M:%S")} | Frame: {i}')
    quad.set_array(floor.da.interp(time=dt).stack(z=('y', 'x')))


ani = animation.FuncAnimation(fig, update_quad_data, frames=enumerate(safe_range[100:]),
                              interval=40)