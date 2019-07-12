import pandas as pd
import numpy as np


avgSpeed = 94.25
strideLength = 111.5
supportTime = 0.29
strideLengthCOV = 2.63
stepWidthCOV = 19.6
stepLengthVar = 0.69

avgSpeedSD = 22.53
strideLengthSD = 23.60
supportTimeSD = 0.07
strideLengthCOVSD = 1.62
stepWidthCOVSD = 16.6
stepLengthVarSD = 0.157


df = pd.DataFrame()
df['time'] = pd.date_range(start='7/1/2019', end='7/8/2019', periods=21)
df['avgSpeed'] = np.random.normal(avgSpeed, avgSpeedSD, 21)
df['supportTime'] = np.random.normal(supportTime, supportTimeSD, 21)
df['strideLengthCOV'] = np.random.normal(strideLengthCOV, strideLengthCOVSD, 21)
df['stepWidthCOV'] = np.random.normal(stepWidthCOV, stepWidthCOVSD, 21)
df['strideLength'] = np.random.normal(strideLength, strideLengthSD, 21)
df['stepLengthVar'] = np.random.normal(stepLengthVar, stepLengthVarSD, 21)


def write_to_json():
    with open('dummy-segments.json', 'w') as f:
        f.write(df.to_json(orient='records'))
