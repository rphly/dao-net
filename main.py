from game.lobby.lobby import Lobby
import sys
import petname

if __name__ == "__main__":
    host_port = None
    player_name = petname.Generate(2)

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
        print(host_port)
        Lobby().start(host_port=9999, player_name=player_name)
    else:
        print("Starting in player mode.")
        print(host_port)
        tracker = Lobby().join(host_port, player_name)
