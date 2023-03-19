import socket
from game.lobby.tracker import Tracker
import json
import keyboard


class Lobby():
    def __init__(self):
        self.game_started = False
        self.lobby_host_exited = False

    def start(self, host_port=9999, player_name="Host"):
        self.player_name = player_name
        self.NUM_PLAYERS = 9  # grab from config
        self.game_port = 9998  # TODO: generate game port
        self.tracker = Tracker()
        self.connections = dict()

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('0.0.0.0', host_port))
        sock.listen(self.NUM_PLAYERS)

        # register myself
        self.tracker.add(player_name, self.game_port)  # generate playerid

        keyboard.add_hotkey('space', self.attempt_start)
        try:
            while not self.game_started:
                connection, _ = sock.accept()
                buf = connection.recv(1024)
                if buf:
                    self.handle_host(buf.decode('utf-8'), connection)
            print("Exiting lobby, entering game")
        except KeyboardInterrupt:
            print("\nExiting lobby")
            # TODO: close all connections and deregister players
        finally:
            sock.close()
            keyboard.remove_all_hotkeys()
        return True

    def join(self, host_port, player_name="Player") -> Tracker:
        """Join an existing lobby."""
        self.player_name = player_name
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('0.0.0.0', host_port))

        sock.sendall(self.lobby_register_pkt())

        while True:
            try:
                while not self.game_started and not self.lobby_host_exited:
                    buf = sock.recv(1024)
                    if buf:
                        self.handle_player(buf.decode('utf-8'), sock)
                print("Exiting lobby, entering game")
                return self.tracker
            except KeyboardInterrupt:
                sock.sendall(self.lobby_deregister_pkt())
                print("\nExiting lobby")
            finally:
                sock.close()

    def handle_player(self, packet, connection):
        req = json.loads(packet)
        payload_type = req.get("payload_type")

        if payload_type == "lobby_shutdown":
            connection.close()
            self.lobby_host_exited = True
            return

        if payload_type == "lobby_start":
            # game is starting, save tracker
            data = req.get("data")
            tracker = data.get("tracker")

            if tracker is None:
                self.nak("No tracker data provided")
                return

            self.tracker = Tracker(tracker)
            self.game_started = True

    def handle_host(self, packet, connection):
        req = json.loads(packet)

        # read packet
        payload_type = req.get("payload_type")

        if (payload_type == "lobby_register"):
            data = req.get("data")
            self.lobby_register(data, connection)
        elif (payload_type == "lobby_deregister"):
            data = req.get("data")
            self.lobby_deregister(data, connection)
        else:
            self.nak("Unknown payload type: " + payload_type)

    def attempt_start(self):
        if self.tracker.get_player_count() == self.NUM_PLAYERS:
            self.lobby_start_game()
            keyboard.remove_hotkey('space')
            self.game_started = True
        else:
            print("Not enough players to start game.")
            print("Current players: " + str(self.tracker.get_players()))

    def lobby_register(self, data, connection):
        player_id = data.get("player_id")
        player_port = data.get("port")
        if not player_id:
            print("No player id")
            return
        if not player_port:
            print("No player port")
            return

        if player_id in self.connections:
            connection.send(self.ack())
            return

        if self.tracker.is_port_used(player_port):
            connection.send(self.nak("port in use by another player"))
            return

        self.connections[player_id] = connection
        self.tracker.add(player_id, player_port)
        connection.send(self.ack())

        print("Player registered: " + player_id)
        print("Current players: " + str(self.tracker.get_players()))

    def lobby_deregister(self, data, connection):
        player_id = data.get("player_id")
        player_port = data.get("port")
        if not player_id:
            print("No player id")
            return
        if not player_port:
            print("No player port")
            return

        self.connections.pop(player_id)
        self.tracker.pop(player_id)
        connection.close()
        print("Player left the lobby: " + player_id)
        print("Current players: " + str(self.tracker.get_players()))

    def lobby_start_game(self):
        for _, connection in self.connections.items():
            connection.send(self.start_pkt())
            connection.close()  # close connections to lobby host
        print("All clients notified of game start.")

    def start_pkt(self):
        return json.dumps(dict(
            data=dict(
                players=self.tracker.get_players(),
                tracker=self.tracker
            ),
            payload_type="lobby_start",
        )).encode('utf-8')

    def lobby_register_pkt(self):
        return json.dumps(dict(
            data=dict(
                player_id=self.player_name,
                port=9997
            ),
            payload_type="lobby_register",
        )).encode('utf-8')

    def lobby_deregister_pkt(self):
        return json.dumps(dict(
            data=dict(
                player_id=self.player_name,
                port=9997
            ),
            payload_type="lobby_deregister",
        )).encode('utf-8')

    def nak(self, error_msg="Error"):
        return json.dumps(dict(
            data=dict(
                message=error_msg
            ),
            payload_type="lobby_nak",
        )).encode('utf-8')

    def ack(self):
        return json.dumps(dict(
            data=dict(
                message="Success"
            ),
            payload_type="lobby_ack",
        )).encode('utf-8')