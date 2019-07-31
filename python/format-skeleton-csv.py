import pandas as pd
import csv
import numpy as np

# ''''''
# AnimationClip {
#     duration: #
#     name: "string"
#     tracks: [
#
#         ...
#
#         VectorKeyframeTrack {
#             name: "<bone_name>.position",
#             times: Float32Array(duration * hertz),
#             values: Float32Array(duration * hertz * dimension(3)),
#             createInterpolant: ƒ
#
#         QuaternionKeyframeTrack {
#             name: "<bone_name>.quaternion",
#             times: Float32Array(duration * hertz),
#             values: Float32Array(duration * hertz * dimension(4)),
#             createInterpolant: ƒ
#
#         VectorKeyframeTrack {
#             name: "<bone_name>.scale",
#             times: Float32Array(duration * hertz),
#             values: Float32Array(duration * hertz * dimension(3)),
#             createInterpolant: ƒ
#
#         ...
#
#     ] <-- length of tracks array = #bones * #types of keyframes
#     uuid: "D4D1457B-B140-47C4-9549-F61553B1CB7B"
# ''''''


def isolate_tracked_data(path):
    with open(path) as csv_file:
        start_line = 0
        end_line = 0
        csv_reader = csv.reader(csv_file, delimiter='\n')
        csv_list = list(csv_reader)
        for i, line in enumerate(csv_list, 0):
            if line[0].find('SpineBase;Tracked') != -1:
                start_line = i
                break

        for j, row in enumerate(csv_list[start_line::6]):
            if row[0].find('SpineBase;NotTracked') != -1 or row[0].find('SpineBase;Inferred') != -1:
                end_line = (start_line + ((j - 1) * 6) + 1)
                break

        return csv_list[start_line: end_line: 6]


def parse_data(path):
    csv_list = isolate_tracked_data(path)
    time: str
    for i, time in enumerate(csv_list):
        csv_list[i] = time[0].split(';')
    return csv_list


def check_tracked(string):
    return string == "Tracked"


def floatify(n):
    return float(n)


def create_time_array(data):
    time_array = []
    start_time = float(data[0][2])
    for time in data:
        time_array.append((float(time[2]) - start_time) / 1000)
    return time_array


def write_to_json(df):
    with open('walk_segment_1.json', 'w') as f:
        f.write(df.to_json())


data = parse_data('data/skeleton.csv')
kf_array = []
for time in data:
    kf = dict(names=time[3:328:13], tracked=list(map(check_tracked, time[4:329:13])),
              x_pos=list(map(floatify, time[5:329:13])), y_pos=list(map(floatify, time[6:329:13])),
              z_pos=list(map(floatify, time[7:329:13])), w_quat=list(map(floatify, time[12:329:13])),
              x_quat=list(map(floatify, time[13:329:13])), y_quat=list(map(floatify, time[14:329:13])),
              z_quat=list(map(floatify, time[15:329:13])))
    kf_array.append(kf)

num_bones = 25
num_kfs = 3
num_kf_params = 3
t_array = create_time_array(data)
tracks = [[[0 for k in range(num_kf_params)] for j in range(num_kfs)] for i in range(num_bones)]
for i in range(num_bones):
    tracks[i][0][0] = kf_array[0]['names'][i] + '.position'
    tracks[i][1][0] = kf_array[0]['names'][i] + '.quaternion'
    tracks[i][2][0] = kf_array[0]['names'][i] + '.scale'
    for j in range(num_kfs):
        tracks[i][j][1] = t_array
        if j == 0:  # position vector
            x_pos = [time['x_pos'][i] for time in kf_array]
            y_pos = [time['y_pos'][i] for time in kf_array]
            z_pos = [time['z_pos'][i] for time in kf_array]
            tracks[i][j][2] = [x_pos, y_pos, z_pos]
        elif j == 1:  # quaternion
            w_quat = [time['x_quat'][i] for time in kf_array]
            x_quat = [time['x_quat'][i] for time in kf_array]
            y_quat = [time['y_quat'][i] for time in kf_array]
            z_quat = [time['z_quat'][i] for time in kf_array]
            tracks[i][j][2] = [w_quat, x_quat, y_quat, z_quat]
        else:  # scale
            tracks[i][j][2] = [[1 for m in kf_array], [1 for m in kf_array], [1 for m in kf_array]]
            # pretty sure the scale is always 1 or close to 1


ac = pd.DataFrame(tracks)  # ac = AnimationClip

# ac['duration'] = (float(data[len(data) - 1][2]) - float(data[0][2])) / 1000.00  # seconds
# ac['name'] = 'walk_segment_1'
# ac['bones'] = tracks
# ac['uuid'] = '???'

write_to_json(ac)


