import functools
import time
import socket
import json
from random import randrange

from game.models.player import Player
from game.lobby.tracker import Tracker
from game.transport.transport import Transport
from game.transport.packet import SyncReq, SyncAck, PeerSyncAck, UpdateLeader, Packet
## TODO Modify Sync Function Based on New FSM
class Sync:
    """
    Synchronizes game actions.
    """
    def __init__(self, myself: Player, tracker: Tracker, ):
        print("Sync Initiated")
        self._myself = myself
        self._player_id = self._myself.get_name()

        self._delay_dict = {}

        self.leader_idx = 0
        self.leader_list = tracker.get_leader_list()
        self.leader = self.leader_list[self.leader_idx] 


    def send_update_leader(self, player_id: str):
        """
        @Leader_function
        Once it's done measuring the delays, it sends an update_leader packet to
        everyone in the network.
        """
        self.leader_idx += 1
        update_leader_pkt = UpdateLeader(None, player_id)
        self._transport_layer.sendall(update_leader_pkt, player_id)


    def receive_update_leader(self):
        """
        @Receiver_function
        Updates leader index by one
        """
        pkt: Packet = self._transport_layer.receive()

        if pkt:
            if pkt.get_packet_type() == "update_leader":
                self.leader_idx += 1
                return True
        else:
            return False


    def update_delay_dict(self, pkt: Packet):
        peer_player_id = pkt.get_player()
        self._delay_dict[peer_player_id] = pkt.get_data()


    def add_delay(self, rcv_time: float):
        """
        Adds a random delay at first and second hops of the measure delay.
        This value returned by this function + measured difference will serve
        as the sample RTT on the game client.
        """
        return rcv_time + 0.1 * randrange(1, 9)
