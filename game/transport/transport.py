import socket

from game.transport.packet import Packet
from game.lobby.tracker import Tracker
from game.thread_manager import ThreadManager

from queue import Queue, Empty
import threading


#TODO
## Modify receive function in transport.py to handle "I'm done" packet and "timer" packet.
class Transport:

    def __init__(self, myself, port, thread_manager, tracker: Tracker, host_socket: socket.socket = None):
        self.tracker = tracker
        self.myself = myself
        self.thread_mgr = thread_manager
        self.queue = Queue()
        self.chunksize = 1024
        self.NUM_PLAYERS = 2
        self._incoming_connection_pool: dict[str, socket.socket] = {}
        self._outgoing_connection_pool: dict[str, socket.socket] = {}

        # start my socket
        if not host_socket:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(("0.0.0.0", port))
            s.listen(self.NUM_PLAYERS)
            s.settimeout(0.5)
            self.my_socket = s
        else:
            host_socket.settimeout(0.5)
            self.my_socket = host_socket

        t1 = threading.Thread(target=self.accept_connections, daemon=True)
        t2 = threading.Thread(target=self.make_connections, daemon=True)

        t1.start()
        t2.start()

    def all_connected(self):
        return len(self._outgoing_connection_pool) == self.NUM_PLAYERS - 1

    def accept_connections(self):
        while True:
            try:
                connection, _ = self.my_socket.accept()
                if connection:
                    print("incoming connection")
                    # start a thread to handle incoming data
                    t = threading.Thread(target=self.handle_incoming, args=(
                        connection,), daemon=True)
                    t.start()
                    self.thread_mgr.add_thread(t)
            except socket.timeout:
                pass

    def make_connections(self):
        while True:
            for player_id in self.tracker.get_players():
                if player_id == self.myself:
                    continue
                if player_id not in self._outgoing_connection_pool:
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
                        self._outgoing_connection_pool[player_id] = conn

                    except (ConnectionRefusedError, TimeoutError):
                        pass

    def send(self, packet: Packet, player_id):
        conn = self._outgoing_connection_pool[player_id]
        # pad data to 1024 bytes
        padded = packet.json().encode('utf-8').ljust(self.chunksize, b"\0")
        conn.sendall(padded)

    def sendall(self, packet: Packet):
        for conn in self._outgoing_connection_pool.values():
            padded = packet.json().encode('utf-8').ljust(self.chunksize, b"\0")
            conn.sendall(padded)

    def receive(self) -> str:
        # TODO handle receiving of sync req
        """
        Drain the queue when we are ready to handle data.
        """
        try:
            data = self.queue.get_nowait()
            self.queue.task_done()
            if data:
                return data.decode('utf-8').rstrip("\0")
        except Empty:
            return

    def handle_incoming(self, connection: socket.socket):
        """
        Handle incoming data from a connection.
        note: queue.put is blocking,
        """
        while True:
            data = connection.recv(self.chunksize)
            if data:
                self.queue.put(data)

    def shutdown(self):
        self.my_socket.close()
        for connection in self._incoming_connection_pool.values():
            connection.close()
        for connection in self._outgoing_connection_pool.values():
            connection.close()
        self.thread_mgr.shutdown()
