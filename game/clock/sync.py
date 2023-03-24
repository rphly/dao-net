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
    def __init__(self, tracker: Tracker, transportLayer: Transport, myself: Player):
        self._transport_layer = transportLayer # Add the Transport Layer to handle recieve packets
        self._myself = myself
        self._player_id = self._myself.get_name()

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
                self.ack_sync_req() #Checks if non host gets the packet, and if it is true
                self.peer_sync_ack() #Check if non host gets the peer sync ack packet
            return

    def measure_delays(self):
        """
        @Leader_function
        Leader sends a packet to everyone in the network and waits for a response 
        that indicates the delay between itself and the peer.
        The leader then sends a packet to the peer with the delay between peer
        and itself. (Other way around)
        """
        self.send_sync_req(self._player_id)
        while len(self._delay_dict) < len(self.leader_list):
            try:
                data = self._transport_layer.receive()
                rcv_time = time.time()

                # update delay list
                data_dict = json.loads(data)
                peer_player_id = self.update_delay_dict(data_dict)

                # measure delay for peer
                delay = (self.add_delay(float(rcv_time))) - data_dict["created_at"]
                peer_sync_ack_pkt = PeerSyncAck(delay, self._myself)
                self._transport_layer.send(peer_sync_ack_pkt, peer_player_id)

                # checking for last leader
                if len(self._delay_dict) == len(self.leader_list) ** 2: # If there are (n-1)**2 delays already measured, then you are the last leader
                    self.leader_idx = 0

            except KeyboardInterrupt:
                pass


    def send_update_leader(self, player_id: str):
        """
        @Leader_function
        Once it's done measuring the delays, it sends an update_leader packet to
        everyone in the network.
        """
        self.leader_idx += 1
        update_leader_pkt = UpdateLeader(None, player_id)
        self._transport_layer.sendall(update_leader_pkt, player_id)


    def recieve_update_leader(self):
        """
        @Receiver_function
        Updates leader index by one
        """
        pkt: Packet = self._transportLayer.receive()

        if pkt:
            if pkt.get_packet_type() == "update_leader":
                self.leader_idx += 1
                return True
        else:
            return False


    def send_sync_req(self, player_id: str):
        """
        @Leader_function
        The host sends sync request to all the peers that it has a connection with.
        """
        sync_req_pkt = SyncReq(player_id)
        self._transport_layer.sendall(sync_req_pkt)


    def ack_sync_req(self):
        """
        @Receiver_function
        Receiver receives this from the host, and then calculates the delay and sends 
        back the difference, along with its own timestamp
        """
        pkt: Packet = self._transportLayer.receive()
        if pkt:
            if pkt.get_packet_type() == "sync_req":
                rcv_time = time.time()
                if pkt:
                    data_dict = json.loads(pkt)
                    if data_dict["player"]["id"] == self.leader:
                        delay = (self.add_delay(float(rcv_time))) - data_dict["created_at"]
                        sync_ack_pkt = SyncAck(delay, self._myself)
                        self._transport_layer.send(sync_ack_pkt, self.leader)
        return


    def peer_sync_ack(self):
        """
        @Receiver_function
        The receiver receives an ACK packet from host that tells it the delay between 
        the host and itself
        """
        pkt: Packet = self._transportLayer.receive()
        if pkt:
            if pkt.get_packet_type() == "peer_sync_ack":
                data_dict = json.loads(pkt)
                if data_dict["player"]["id"] == self.leader:
                    delay_to_leader = data_dict["data"]
                    self._delay_dict[self.leader] = delay_to_leader
        return

    def update_delay_dict(self, data_dict: dict):
        peer_player_id = data_dict["player"]["id"]
        self._delay_dict[peer_player_id] = data_dict["data"]
        return peer_player_id

    def add_delay(rcv_time: float):
        """
        Adds a random delay at first and second hops of the measure delay. 
        This value returned by this function + measured difference will serve
        as the sample RTT on the game client.
        """
        return rcv_time + 0.1 * randrange(1, 9)
