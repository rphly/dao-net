import json
import socket
from game.models.player import Player
from game.transport.packet import ConnectionEstab, ConnectionRequest, Packet
from game.lobby.tracker import Tracker

from config import NUM_PLAYERS

from queue import Queue, Empty
import threading

import time


class Transport:

    def __init__(self, myself, port, thread_manager, tracker: Tracker, host_socket: socket.socket = None):
        self.myself = myself
        self.thread_mgr = thread_manager
        self.queue = Queue()
        self.chunksize = 1024
        self.NUM_PLAYERS = NUM_PLAYERS
        self.lock = threading.Lock()

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
        time.sleep(2)

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

        for player_id in self.tracker.get_players():
            if player_id == self.myself:
                continue
            self.lock.acquire()
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
                    print(
                        f"{time.time()} [Make Conn] Sent conn req to {player_id}")
                    time.sleep(1)
                except (ConnectionRefusedError, TimeoutError):
                    pass
            self.lock.release()

    def send(self, packet: Packet, player_id):
        padded = packet.json().encode('utf-8').ljust(self.chunksize, b"\0")
        # try:
        #     print("old")
        #     conn = self._connection_pool[player_id]
        #     conn.sendall(padded)
        # except (BrokenPipeError, OSError):
        #     print("new")
        #     ip, port = self.tracker.get_ip_port(
        #         player_id)
        #     conn = socket.socket(
        #         socket.AF_INET, socket.SOCK_STREAM)
        #     conn.connect((ip, port))
        #     conn.sendall(padded)
        #     self._connection_pool[player_id] = conn
        ip, port = self.tracker.get_ip_port(
            player_id)
        conn = socket.socket(
            socket.AF_INET, socket.SOCK_STREAM)
        conn.connect((ip, port))
        conn.sendall(padded)

    def sendall(self, packet: Packet):
        for player_id in self._connection_pool:
            print("Sending packet", packet, "to", player_id)
            self.send(packet, player_id)

    def receive(self) -> str:
        """
        Drain the queue when we are ready to handle data.
        """
        try:
            data: bytes = self.queue.get_nowait()
            self.queue.task_done()
            if data:
                return Packet.from_json(json.loads(data.decode('utf-8').rstrip("\0")))
        except Empty:
            return

    def check_if_peering_and_handle(self, data, connection):
        decoded = data.decode('utf-8').rstrip("\0")
        d = json.loads(decoded)
        packet_type = d["packet_type"]
        if packet_type == "connection_req":
            self.handle_connection_request(d, connection)
        elif packet_type == "connection_estab":
            self.handle_connection_estab(d, connection)
        else:
            self.queue.put(data)

    def handle_connection_request(self, data, connection):
        player: Player = Player(data["player"]["name"])
        player_name = player.get_name()
        self.lock.acquire()
        if not player_name in self._connection_pool:
            # add player to connection pool
            self._connection_pool[player_name] = connection

        # send estab and trigger the other player to add back same conn
        print(
            f"{time.time()} [Receive Conn Request] Sending conn estab to {player_name}")
        self.send(ConnectionEstab(Player(self.myself)), player_name)
        self.lock.release()

    def handle_connection_estab(self, data, connection):
        player: Player = Player(data["player"]["name"])
        player_name = player.get_name()
        self.lock.acquire()
        if not player_name in self._connection_pool:
            # only add player to connection pool if not already inside
            print(f"{time.time()} [Receive Conn Estab] Saving connection")
            self._connection_pool[player_name] = connection
        self.lock.release()

    def handle_incoming(self, connection: socket.socket):
        """
        Handle incoming data from a connection.
        note: queue.put is blocking,
        """
        while True:
            try:
                data = connection.recv(self.chunksize)
                if data:
                    if not self.all_connected():
                        self.check_if_peering_and_handle(data, connection)
                        continue
                    self.queue.put(data)
            except:
                break

    def shutdown(self):
        self.my_socket.close()
        for connection in self._connection_pool.values():
            connection.close()
        self.thread_mgr.shutdown()
