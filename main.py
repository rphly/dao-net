from game.lobby.lobby import Lobby
from game.client import Client as GameClient
import sys
import petname

if __name__ == "__main__":
    host_port = None
    player_name = petname.Generate(2)
    tracker = None

    for i in range(0, len(sys.argv)):
        if sys.argv[i] == "-h":
            try:
                host_port = int(sys.argv[i+1])
            except (ValueError, TypeError):
                print("Invalid port number.")
                exit(1)

        if sys.argv[i] == "-pn":
            player_name = sys.argv[i+1]

    if host_port is None:
        print("Starting in host mode.")
        tracker = Lobby().start(host_port=9999, player_name=player_name)
    else:
        print("Starting in player mode.")
        tracker = Lobby().join(host_port, player_name)

    if tracker is None:
        print("Failed to start game.")
        exit(1)

    print("Entering game...")
    GameClient(player_name, tracker).start()
    print("Hope you had fun!")
