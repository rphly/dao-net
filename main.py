from game.lobby.lobby import Lobby
from game.client import Client as GameClient
import sys
import petname

if __name__ == "__main__":
    host_ip = None
    player_port = None
    host_port = None
    player_ip = None
    is_player_mode = True
    player_name = petname.Generate(2)
    tracker = None

    for i in range(0, len(sys.argv)):
        if sys.argv[i] == "-ip":
            host_ip = sys.argv[i+1]

        if sys.argv[i] == "-pip":
            player_ip = sys.argv[i+1]

        if sys.argv[i] == "-hp":
            try:
                host_port = int(sys.argv[i+1])
            except (ValueError, TypeError):
                print("Invalid host port number.")
                exit(1)

        if sys.argv[i] == "-pp":
            try:
                player_port = int(sys.argv[i+1])
            except (ValueError, TypeError):
                print("Invalid player_port number.")
                exit(1)

        if sys.argv[i] == "-m":
            if sys.argv[i+1] == "host":
                is_player_mode = False

        if sys.argv[i] == "-n":
            player_name = sys.argv[i+1]

    if (is_player_mode) and ((player_ip is None) or (player_port is None) or (host_port is None) or (host_ip is None)):
        print("Require an ip address and port number to connect to host.")
        exit(1)

    if not is_player_mode:
        host_port = host_port or 9999
        print(f"Starting host mode on port {host_port}.")
        tracker = Lobby().start(ip="127.0.0.1",
                                host_port=host_port or 9999, player_name=player_name)
    else:
        print("Starting in player mode.")
        tracker = Lobby().join(host_ip, player_ip, host_port, player_port, player_name)

    if tracker is None:
        print("Failed to start game.")
        exit(1)

    print("Entering game...")
    GameClient(player_name, tracker, is_player_mode=is_player_mode).start()
    print("Hope you had fun!")
