import os

relevant_tags = {
    "DELAY_INFO",
    "PACKET_INFO",
    "KEYPRESS_TIME",
    "ACTION_PACKET"
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
        print("\n", filename)
        logs = read_file(folder_path + "/" + filename)
        lines = logs.split("\n")
        # print(lines)
        for line in lines:
            Information = line.split(" ")
            if len(Information) > 1:
                if Information[3] in relevant_tags: print(Information[3])
                # Code get json information, once @visshal finishes log format.




if __name__ == "__main__":
    loop_folder("./logs_parse")
    pass