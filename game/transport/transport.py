import socket

from game.transport.packet import Packet
from game.lobby.tracker import Tracker


class Transport:
    _connection_pool: dict[str, socket.socket] = {}
    chunksize = 1024
    NUM_PLAYERS = 9

    def __init__(self, myself, port, tracker: Tracker, is_player_mode: bool = True):
        self.tracker = tracker
        self.myself = myself

        # start my socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        if is_player_mode:
            s.bind(("0.0.0.0", port))
            s.listen(self.NUM_PLAYERS)

        self.my_socket = s

        self.make_connections()

    def all_connected(self):
        return len(self._connection_pool) == self.NUM_PLAYERS - 1

    def make_connections(self):
        while len(self._connection_pool) < self.NUM_PLAYERS-1:
            for player_id in self.tracker.get_players():
                if player_id == self.myself:
                    continue
                if player_id not in self._connection_pool:
                    ip, port = self.tracker.get_ip_port(
                        player_id)
                    if ip is None or port is None:
                        continue
                    # waiting for player to start server
                    try:
                        sock = socket.socket(
                            socket.AF_INET, socket.SOCK_STREAM)
                        sock.connect((ip, port))
                        print(f"Connected to {player_id} at {ip}:{port}")
                        self._connection_pool[player_id] = sock
                    except (ConnectionRefusedError, TimeoutError):
                        pass

    def send(self, packet: Packet, player_id):
        conn = self._connection_pool[player_id]
        # pad data to 1024 bytes
        padded = packet.json().encode('utf-8').ljust(self.chunksize, b"\0")
        conn.sendall(padded)

    def sendall(self, packet: Packet):
        for conn in self._connection_pool.values():
            padded = packet.json().encode('utf-8').ljust(self.chunksize, b"\0")
            conn.sendall(padded)

    def receive(self) -> str:
        # TODO: for each connection in pool based on delay
        for connection in self._connection_pool.values():
            data = connection.recv(self.chunksize)
            if data:
                # decode
                data = data.decode('utf-8')
                return data.rstrip("\0")

    def shutdown(self):
        self.my_socket.close()
        for connection in self._connection_pool.values():
            connection.close()
