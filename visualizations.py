import os
import json
import matplotlib.pyplot as plt
import plotly.graph_objs as go
from plotly.subplots import make_subplots

relevant_tags = {
    "ORDERED DELAYLIST",
    "WAIT LIST",
    "KEYPRESS_TIME",
    "ACTION PACKET INFO-send",
    "ACTION PACKET INFO-RECEIVE"
}

def read_file(filename):
    """
    Returns string value of everything in that file
    """
    with open(filename, "r") as f:
        return f.read()

def loop_folder(folder_path):
    """
    Loops through all log files in the logs_parse folder
    """
    keypress_times = []
    throughputs = []
    frames = {}
    special_frames = {}
    special_times = {}
    for filename in os.listdir(folder_path):
        print("\n"+filename)
        player_name = filename.split("_")[1]
        print("Player name: ", filename.split("_")[1])
        logs = read_file(folder_path + "/" + filename)
        lines = logs.split("\n")[:-1]
        for line in lines:
            jsonlog = json.loads(line)
            # print(jsonlog)
            if "Logger Name"  in jsonlog['message']:
                thejsonyouneeded = json.loads(jsonlog['message'])
                # print(thejsonyouneeded)
                if thejsonyouneeded['Logger Name'] == "KEYPRESS TIME":
                    keypress_times.append(thejsonyouneeded['Time'])
                if thejsonyouneeded['Logger Name'] == "ACTION PACKET INFO-RECEIVE":
                    throughputs.append(thejsonyouneeded['Throughput'])
                if thejsonyouneeded['Logger Name'] == "FRAME COUNT":
                    if player_name not in frames:
                        frames[player_name] = []
                    frames[player_name].append(thejsonyouneeded["Time"])
                if thejsonyouneeded['Logger Name'] == "FRAME SLOWING-BEFORE":
                    # frames[thejsonyouneeded["Frame Count"]] = thejsonyouneeded["Time"]
                    pass
                if thejsonyouneeded['Logger Name'] == "FRAME SYNCING":
                    if player_name not in special_frames:
                        special_frames[player_name] = []
                    special_frames[player_name].append([thejsonyouneeded["Frame Count"],thejsonyouneeded["Time"]])

    return keypress_times, throughputs, frames, special_frames





if __name__ == "__main__":
    keypress_times, throughputs, frames, special_frames = loop_folder("./logs_parse")
    print("Average throughputs: ", sum(throughputs)/len(throughputs))
    print(frames)
    name_list = frames.keys()
    # fig, ax = plt.subplots()
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    for name, value in frames.items():
        # ax.plot(value, label=name)
        fig.add_trace(go.Scatter(x=list(range(0,len(value))), y=value, name=name), secondary_y=False)
        print(special_frames[name][0][0])
        fig.add_trace(go.Scatter(x=[special_frames[name][0][0]], y=[value[special_frames[name][0][0]]],name="Syncing Frame"), secondary_y=False)

    fig.update_layout(title=str(frames.keys()), xaxis_title='Frame number', yaxis_title='Time')

    fig.show()
    pass