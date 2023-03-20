import socket

from game.transport.packet import Packet
from game.lobby.tracker import Tracker
from game.thread_manager import ThreadManager

from queue import Queue, Empty
import threading


class Transport:
    _connection_pool: dict[str, socket.socket] = {}
    chunksize = 1024
    NUM_PLAYERS = 2

    def __init__(self, myself, port, tracker: Tracker, is_player_mode: bool = True):
        self.tracker = tracker
        self.myself = myself
        self.thread_mgr = ThreadManager()
        self.queue = Queue()

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
                        conn = socket.socket(
                            socket.AF_INET, socket.SOCK_STREAM)
                        conn.connect((ip, port))
                        print(f"Connected to {player_id} at {ip}:{port}")
                        self._connection_pool[player_id] = conn

                        t = threading.Thread(
                            target=self.handle_incoming, args=(conn, player_id,), daemon=True)
                        t.start()
                        self.thread_mgr.add_thread(t)

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
        """
        Drain the queue when we are ready to handle data.
        """
        print("[QUEUE] Draining...")
        try:
            data = self.queue.get_nowait()
            self.queue.task_done()
            if data:
                print("[QUEUE] data received")
                return data.decode('utf-8').rstrip("\0")
        except Empty:
            return

    def handle_incoming(self, connection: socket.socket, player_id):
        """
        Handle incoming data from a connection.
        note: queue.put is blocking,
        """
        while player_id in self._connection_pool:
            data = connection.recv(self.chunksize)
            if data:
                self.queue.put(data)

    def shutdown(self):
        self.my_socket.close()
        for connection in self._connection_pool.values():
            connection.close()
        self.thread_mgr.shutdown()
