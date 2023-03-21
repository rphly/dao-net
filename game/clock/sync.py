import functools
import time
import socket
import json

from game.models.player import Player
from game.lobby.tracker import Tracker
from game.transport.transport import Transport
from game.transport.packet import Packet, SyncReq, SyncAck

class Sync:
    """Synchronizes game actions."""
    def __init__(self, my_name: str, tracker: Tracker, transportLayer: Transport, myself: Player):
        self._name = my_name
        self._player_id = self._myself.id()
        self._transport_layer = transportLayer
        self._myself = myself 

        self._delay_list = {}

        self.leader_idx = 0
        self.leader_list = tracker.get_leader_list()
        self.leader = self.leader_list[self.leader_idx]

        while True:
            if self._player_id == self.leader_list[self.leader_idx] \
            and self.leader_idx != len(self.leader_list)-1:
                self.measure_delays()

            elif self._player_id == self.leader_list[self.leader_idx] \
            and self.leader_idx == len(self.leader_list)-1:
                # reset leader idx
                self.leader_idx = 0
                # send update of leader idx when round ends
                pass

            else:
                conn_pool = self._transport_layer._connection_pool
                leader_conn = conn_pool[self.leader]
                self.ack_sync_req(leader_conn)


    def measure_delays(self):
        for i in range(self.leader_idx, len(self.leader_list)):
            recv_ack = False

            peer_player_id = self.leader_list[i]
            self.send_sync_req(peer_player_id)

            while not recv_ack:
                try:
                    self._transport_layer.handle_incoming(peer_player_id, self.leader)
                    self._transport_layer.receive()

                    

    
    def send_sync_req(self, player_id: str):
        sync_req_pkt = SyncAck(None, self._myself)
        self._transport_layer.send(sync_req_pkt, player_id)

        
    def ack_sync_req(self, leader_conn: socket.socket):
        self._transport_layer.handle_incoming(leader_conn, self.leader)
        data = self._transport_layer.receive()
        rcv_time = time.time()

        if data:
            data_dict = json.loads(data)
            delay = int(rcv_time) - data_dict["created_at"]
            self._delay_list[self.leader] = delay

            sync_ack_pkt = SyncReq(None, self._myself)
            self._transport_layer.send(sync_ack_pkt, self.leader)
        return
    
    def second_sync_req(self):


    def update_delay_list(self, delay):
        

    def add_delay(delay=0):
        def wr(fn):
            @functools.wraps(fn)
            def w(*args, **kwargs):
                print("adding delay to function")
                time.sleep(delay)
                return fn(*args, **kwargs)
            return w
        return wr
