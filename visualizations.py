import os
import json

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
    for filename in os.listdir(folder_path):
        print("\n"+filename)
        logs = read_file(folder_path + "/" + filename)
        lines = logs.split("\n")
        # print(lines)
        for line in lines:
            print(line)
            # print(logs)
            # print(json.loads(log))



if __name__ == "__main__":
    loop_folder("./logs_parse")
    pass