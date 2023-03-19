import socket

from game.transport.packet import Packet


class Transport:
    _connection_pool: dict[str, socket.socket] = {}
    chunksize = 1024

    def __init__(self):
        pass

    def add_connection(self, player_id, connection):
        self._connection_pool[player_id] = connection

    def send(self, packet: Packet, player_id):
        conn = self._connection_pool[player_id]
        # pad data to 1024 bytes
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
