import json
import socket
from game.models.player import Player

from game.transport.packet import ConnectionEstab, ConnectionRequest, Packet
from game.lobby.tracker import Tracker

from queue import Queue, Empty
import threading

import time


class Transport:

    def __init__(self, myself, port, thread_manager, tracker: Tracker, host_socket: socket.socket = None):
        self.myself = myself
        self.thread_mgr = thread_manager
        self.queue = Queue()
        self.chunksize = 1024
        self.NUM_PLAYERS = 4

        self.tracker = tracker
        self._connection_pool: dict[str, socket.socket] = {}

        # start my socket
        if not host_socket:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(("0.0.0.0", port))
            s.listen(self.NUM_PLAYERS)
            self.my_socket = s
        else:
            self.my_socket = host_socket

        self.my_socket.settimeout(0.5)

        t1 = threading.Thread(target=self.accept_connections, daemon=True)
        t2 = threading.Thread(target=self.make_connections, daemon=True)
        t1.start()
        t2.start()

    def all_connected(self):
        return len(self._connection_pool) == self.NUM_PLAYERS - 1

    def accept_connections(self):
        """
        Accept all incoming connections 
        """
        while True:
            try:
                connection, _ = self.my_socket.accept()
                if connection:
                    # start a thread to handle incoming data
                    t = threading.Thread(target=self.handle_incoming, args=(
                        connection,), daemon=True)
                    t.start()
                    self.thread_mgr.add_thread(t)
            except socket.timeout:
                pass

    def make_connections(self):
        """
        Attempt to make outgoing connections to all players
        """
        while not self.all_connected():
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
                        # send a player my conn request
                        sock.sendall(ConnectionRequest(Player(self.myself)).json().encode(
                            'utf-8').ljust(self.chunksize, b"\0"))
                        print("[Make Conn] Sent conn req")
                        time.sleep(1)
                    except (ConnectionRefusedError, TimeoutError):
                        pass

    def send(self, packet: Packet, player_id):

        ip, port = self.tracker.get_ip_port(
            player_id)
        conn = socket.socket(
            socket.AF_INET, socket.SOCK_STREAM)
        conn.connect((ip, port))

        # pad data to 1024 bytes
        padded = packet.json().encode('utf-8').ljust(self.chunksize, b"\0")
        conn.sendall(padded)

    def sendall(self, packet: Packet):
        for player_id in self._connection_pool:
            self.send(packet, player_id)

    def receive(self) -> str:
        """
        Drain the queue when we are ready to handle data.
        """
        try:
            data: bytes = self.queue.get_nowait()
            self.queue.task_done()
            if data:
                return data.decode('utf-8').rstrip("\0")
        except Empty:
            return

    def check_if_peering_and_handle(self, data, connection):
        decoded = data.decode('utf-8').rstrip("\0")
        d = json.loads(decoded)
        packet_type = d["payload_type"]
        if packet_type == "connection_req":
            self.handle_connection_request(d, connection)
        elif packet_type == "connection_estab":
            self.handle_connection_estab(d, connection)
        else:
            self.queue.put(data)

    def handle_connection_request(self, data, connection):
        player: Player = Player(data["player"]["name"])
        player_name = player.get_name()
        if not player_name in self._connection_pool:
            # add player to connection pool
            self._connection_pool[player_name] = connection
        # send estab and trigger the other player to add back same conn
        print(f"[Receive Conn Request] Sending conn estab to {player_name}")
        self.send(ConnectionEstab(Player(self.myself)), player_name)

    def handle_connection_estab(self, data, connection):
        player: Player = Player(data["player"]["name"])
        player_name = player.get_name()
        if not player_name in self._connection_pool:
            # only add player to connection pool if not already inside
            print("[Receive Conn Estab] Saving conn")
            self._connection_pool[player_name] = connection

    def handle_incoming(self, connection: socket.socket):
        """
        Handle incoming data from a connection.
        note: queue.put is blocking,
        """
        while True:
            try:
                data = connection.recv(self.chunksize)
                if data and self.all_connected():
                    self.queue.put(data)
                else:
                    if data:
                        # for peering
                        self.check_if_peering_and_handle(data, connection)
            except:
                break

    def shutdown(self):
        self.my_socket.close()
        for connection in self._connection_pool.values():
            connection.close()
        self.thread_mgr.shutdown()
