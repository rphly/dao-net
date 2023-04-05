import json
import socket
from game.models.player import Player
from game.transport.packet import ConnectionEstab, ConnectionRequest, Packet, SyncReq, SyncAck, PeerSyncAck, UpdateLeader
from game.lobby.tracker import Tracker
from game.clock.sync import Sync
from game.clock.delay import Delay

from queue import Queue, Empty
import threading
import logging

import time

"""
Transport is responsible for sending and receiving data from other players.
It is also responsible for maintaining a connection pool of all players.
"""


class Transport:

    def __init__(self, myself: str, port, thread_manager, logger: logging.Logger, tracker: Tracker, host_socket: socket.socket = None):
        self.myself = myself
        self.my_player = Player(name=self.myself)
        self.thread_mgr = thread_manager
        self.queue = Queue()
        self.chunksize = 1024
        self.NUM_PLAYERS = tracker.get_player_count()
        self.lock = threading.Lock()
        self.logger = logger

        self.tracker = tracker
        self._connection_pool: dict[str, socket.socket] = {}

        self.sync = Sync(myself=self.myself,
                         tracker=self.tracker, logger=self.logger)
        self.is_sync_completed = False

        # self.delayer = Delay
        self.sent_sync = False

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
        self.logger.debug("Completely initialized transport...")

    # FOR TESTING PURPOSES ONLY
    def get_connection_pool(self):
        return self._connection_pool

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
            except:
                pass

    def make_connections(self):
        """
        Attempt to make outgoing connections to all players
        """
        while not self.all_connected():

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
                            f"[Make Conn] Sent conn req to {player_id} at {time.time()}")
                        self.logger.info(
                            f"{self.myself} sending connection request to {player_id} at {time.time()}")
                        time.sleep(1)
                    except (ConnectionRefusedError, TimeoutError):
                        pass
                self.lock.release()

    def send(self, packet: Packet, player_id):
        # self.delayer.delay(player_id)

        padded = packet.json().encode('utf-8').ljust(self.chunksize, b"\0")
        try:
            conn = self._connection_pool[player_id]
            conn.sendall(padded)
        except (ConnectionRefusedError, BrokenPipeError, OSError):
            ip, port = self.tracker.get_ip_port(
                player_id)
            conn = socket.socket(
                socket.AF_INET, socket.SOCK_STREAM)
            conn.connect((ip, port))
            conn.sendall(padded)
            self._connection_pool[player_id] = conn
        # ip, port = self.tracker.get_ip_port(
        #     player_id)
        # conn = socket.socket(
        #     socket.AF_INET, socket.SOCK_STREAM)
        # conn.connect((ip, port))
        # conn.sendall(padded)

    def send_within(self, packet: Packet, player_id, delay: float):
        now = time.time()
        time.sleep(delay)
        self.send(packet, player_id)
        self.logger.info(
            f"{self.myself} sending {packet.get_packet_type()} packet to {player_id}")
        self.logger.info(
            f"DELAY_INFO\n{self.myself} to {player_id} | send_time:{now} | delay_time: {now+delay} | packet_type: {packet.get_packet_type()}")

    def sendall(self, packet: Packet):
        wait_dict = self.sync.get_wait_times()
        if wait_dict:
            for player_id in self._connection_pool:
                wait = wait_dict[player_id]
                threading.Thread(target=self.send_within(
                    packet, player_id, delay=wait), daemon=True)

        else:
            for player_id in self._connection_pool:
                threading.Thread(target=self.send_within(
                    packet, player_id, delay=0), daemon=True)

        # for player_id in self._connection_pool:
        #     print("Sending packet", packet.get_packet_type(), "to", player_id)
        #     self.send(packet, player_id)

    def receive(self) -> str:
        """
        Drain the queue when we are ready to handle data.
        """
        try:
            data: bytes = self.queue.get_nowait()
            self.queue.task_done()
            if data:
                packet = Packet.from_json(json.loads(
                    data.decode('utf-8').rstrip("\0")))
                length = len(packet)
                rtt = time.time() - packet.get_created_at()
                throughput = length / rtt
                self.logger.info(
                    f"PACKET_INFO\nLength: {length} | Packet Type: {packet.get_packet_type()} | RTT: {rtt} | Throughput: {throughput}")
                return packet
        except Empty:
            return

    def check_if_peering_and_handle(self, data, connection):
        decoded = data.decode('utf-8').rstrip("\0")
        d = json.loads(decoded)
        packet_type = d["packet_type"]
        if packet_type == "connection_req":
            self.handle_connection_request(d, connection)
            return True
        elif packet_type == "connection_estab":
            self.handle_connection_estab(d, connection)
            return True
        else:
            return False

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
                    is_peering = self.check_if_peering_and_handle(
                        data, connection)
                    if not is_peering:
                        self.queue.put(data)
            except:
                break

    # Sync class functions
    def syncing(self):
        if self.sync.is_leader_myself() and not self.sent_sync:
            print("sending sync req")
            sync_req_pkt = SyncReq(self.my_player)
            self.sendall(sync_req_pkt)
            self.sent_sync = True
        return

    def reset_sync(self):
        self.sync.reset_sync()

    def shutdown(self):
        self.thread_mgr.shutdown()
        self.my_socket.close()
        for connection in self._connection_pool.values():
            connection.close()
