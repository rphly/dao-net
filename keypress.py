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
    keypress_times = {}
    info_receive = {}
    delay_list = {}
    wait_list = {}
    for filename in os.listdir(folder_path):
        if not (filename.startswith("PLAYER") or filename.startswith("HOST")):
            continue
        player_name = filename.split("_")[1]
        print("Player name: ", filename.split("_")[1])
        logs = read_file(folder_path + "/" + filename)
        lines = logs.split("\n")[:-1]
        for line in lines:
            jsonlog = json.loads(line)
            # print(jsonlog)
            if "Logger Name" in jsonlog['message']:
                thejsonyouneeded = json.loads(jsonlog['message'])
                # print(thejsonyouneeded)
                if thejsonyouneeded['Logger Name'] == "KEYPRESS TIME":
                    if player_name not in keypress_times:  
                        keypress_times[player_name] = []                  
                    keypress_times[player_name].append((thejsonyouneeded['Seat Selected'], thejsonyouneeded["Round"], thejsonyouneeded['Time']))

                if thejsonyouneeded['Logger Name'] == "ACTION PACKET INFO-RECEIVE":
                    round_number = thejsonyouneeded["Round"]
                    if round_number not in info_receive:
                        info_receive[round_number] = []
                    info_receive[round_number].append((thejsonyouneeded['Data'], thejsonyouneeded['From']))
                if thejsonyouneeded['Logger Name'] == "UNORDERED DELAYLIST":
                    if player_name not in delay_list:
                        delay_list[player_name] = {}
                    delay_list[player_name] = thejsonyouneeded['Logging Data']
                if thejsonyouneeded["Logger Name"] == "WAIT LIST":
                    if player_name not in wait_list:
                        wait_list[player_name] = {}
                    wait_list[player_name] = thejsonyouneeded['Logging Data']
                    


    return keypress_times, delay_list, info_receive, wait_list


if __name__ == "__main__":
    keypress_times, delay_list, info_receive, wait_list = loop_folder("./logs_parse")
    print("\n\nKeypress times\n", keypress_times,
          "\n\nDelay list\n", delay_list,
          "\n\ninfo_receive\n", info_receive,
          "\n\nWait_list\n", wait_list
          )