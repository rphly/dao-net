import functools
import time
import socket
import json

from game.models.player import Player
from game.lobby.tracker import Tracker
from game.transport.transport import Transport
from game.transport.packet import SyncReq, SyncAck, PeerSyncAck, UpdateLeader, Packet
## TODO Modify Sync Function Based on New FSM
class Sync:
    """Synchronizes game actions."""
    def __init__(self, tracker: Tracker, transportLayer: Transport, myself: Player):
        self._transport_layer = transportLayer # Add the Transport Layer to handle recieve packets
        self._myself = myself
        self._player_id = self._myself.id()

        self._delay_dict = {}

        self.leader_idx = 0
        self.leader_list = tracker.get_leader_list()
        self.leader = self.leader_list[self.leader_idx] # What is this for?

    # Control Flow from Client to Sync_State_Checker
    def sync_state_checker(self):
        # If you are the leader
        if self._player_id == self.leader_list[self.leader_idx] and self.leader_idx != len(self.leader_list)- 1:
                self.measure_delays() # Measures Delay
                self.send_update_leader() # Updates Leader
                return
        #If you are a normal peer
        else:
            #You keep on looping until you get update_leader
            while not self.recieve_update_leader():
                self.ack_sync_req() #Checks if we get the packet, and if it is true
                self.peer_sync_ack() #Check if we get the peer sync ack packet
            return

    #TODO @Fauzaan
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


    def send_update_leader(self, player_id: str):
        self.leader_idx += 1
        update_leader_pkt = UpdateLeader(None, player_id)
        self._transport_layer.sendall(update_leader_pkt, player_id)


    def recieve_update_leader(self, player_id: str):
        pkt: Packet = self._transportLayer.receive()

        if pkt:
            if pkt.get_packet_type() == "update_leader":
                self.leader_idx += 1
                return True
        else:
            return False


    def send_sync_req(self, player_id: str):
        sync_req_pkt = SyncReq(None, player_id)
        self._transport_layer.sendall(sync_req_pkt, player_id)


    def ack_sync_req(self):
        pkt: Packet = self._transportLayer.receive()
        if pkt:
            if pkt.get_packet_type() == "sync_req":
                rcv_time = time.time()
                if pkt:
                    data_dict = json.loads(pkt)
                    if data_dict["player"]["id"] == self.leader:
                        delay = int(rcv_time) - data_dict["created_at"]
                        sync_ack_pkt = SyncAck(delay, self._myself)
                        self._transport_layer.send(sync_ack_pkt, self.leader)
        return


    def peer_sync_ack(self):
        pkt: Packet = self._transportLayer.receive()

        if pkt:
            if pkt.get_packet_type() == "peer_sync_ack":
                if pkt:
                    data_dict = json.loads(pkt)
                    if data_dict["player"]["id"] == self.leader:
                        delay_to_leader = data_dict["data"]
                        self._delay_dict[self.leader] = delay_to_leader
        return

    #TODO @Fauzaan
    def update_delay_dict(self, delay):
        return

    #TODO @Fauzaan
    def add_delay(delay=0):
        def wr(fn):
            @functools.wraps(fn)
            def w(*args, **kwargs):
                print("adding delay to function")
                time.sleep(delay)
                return fn(*args, **kwargs)
            return w
        return wr
