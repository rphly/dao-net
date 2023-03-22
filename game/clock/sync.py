import functools
import time
import socket
import json

from game.models.player import Player
from game.lobby.tracker import Tracker
from game.transport.transport import Transport
from game.transport.packet import SyncReq, SyncAck, PeerSyncAck

class Sync:
    """Synchronizes game actions."""
    def __init__(self, tracker: Tracker, transportLayer: Transport, myself: Player):        
        self._transport_layer = transportLayer
        self._myself = myself
        self._player_id = self._myself.id()

        self._delay_dict = {}

        self.leader_idx = 0
        self.leader_list = tracker.get_leader_list()
        self.leader = self.leader_list[self.leader_idx]

        while True:
            # you are leader
            if self._player_id == self.leader_list[self.leader_idx] \
            and self.leader_idx != len(self.leader_list)-1:
                self.measure_delays()

            # you are last to be leader, reset leader idx
            elif self._player_id == self.leader_list[self.leader_idx] \
            and self.leader_idx == len(self.leader_list)-1:
                # reset leader idx
                self.leader_idx = 0
                # send update of leader idx when round ends
                pass
            
            # you are a normal peer
            else: 
                while not self.ack_sync_req():
                    continue
                while not self.second_sync_req():
                    continue
                


    def measure_delays(self):
        self.send_sync_req(self._player_id)
        while len(self._delay_dict) < len(self.leader_list):
            try:
                data = self._transport_layer.receive()
                rcv_time = time.time()

                # update delay list
                data_dict = json.loads(data)
                peer_player_id = data_dict["player"]["id"]
                delay_to_peer = data_dict["data"]
                self._delay_dict[peer_player_id] = delay_to_peer

                # measure delay for peer
                delay = int(rcv_time) - data_dict["created_at"]
                peer_sync_ack_pkt = PeerSyncAck(delay, self._myself)
                self._transport_layer.send(peer_sync_ack_pkt, peer_player_id)
                
            except KeyboardInterrupt:
                pass
                    

    
    def send_sync_req(self, player_id: str):
        sync_req_pkt = SyncReq(None, player_id)
        self._transport_layer.sendall(sync_req_pkt, player_id)

        
    def ack_sync_req(self):

        data = self._transport_layer.receive()
        rcv_time = time.time()

        if data:
            data_dict = json.loads(data)
            if data_dict["player"]["id"] == self.leader:
                delay = int(rcv_time) - data_dict["created_at"]
                
                sync_ack_pkt = SyncAck(delay, self._myself)
                self._transport_layer.send(sync_ack_pkt, self.leader)

                return 1
        return 
        
    
    def second_sync_req(self):
        data = self._transport_layer.receive()

        if data:
            data_dict = json.loads(data)
            if data_dict["player"]["id"] == self.leader:
                delay_to_leader = data_dict["data"]
                self._delay_dict[self.leader] = delay_to_leader
                return 1
        return

    def update_delay_dict(self, delay):
        return

    def add_delay(delay=0):
        def wr(fn):
            @functools.wraps(fn)
            def w(*args, **kwargs):
                print("adding delay to function")
                time.sleep(delay)
                return fn(*args, **kwargs)
            return w
        return wr
