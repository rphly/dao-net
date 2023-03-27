import functools
import time
import socket
import json
from random import randrange

from game.models.player import Player
from game.lobby.tracker import Tracker
from game.transport.packet import UpdateLeader, Packet
# TODO Modify Sync Function Based on New FSM


class Sync:
    """
    Synchronizes game actions.
    """

    def __init__(self, myself: str, tracker: Tracker, ):
        print("Sync Initiated")
        self.myself = myself
        self._delay_dict = {}

        self.leader_idx = 0
        self.leader_list = tracker.get_leader_list()

    def next_leader(self):
        if self.leader_idx < len(self.leader_list) - 1:
            self.leader_idx += 1
            self.leader = self.leader_list[self.leader_idx]

    def no_more_leader(self):
        return self.leader_idx == len(self.leader_list) - 1

    def is_leader_myself(self):
        # If you are the leader
        return self.myself == self.leader_list[self.leader_idx]

    def update_delay_dict(self, pkt: Packet):
        peer_player_id = pkt.get_player().get_name()
        self._delay_dict[peer_player_id] = pkt.get_data()

    def done(self):
        return len(self._delay_dict) == len(self.leader_list) - 1

    def add_delay(self, rcv_time: float):
        """
        Adds a random delay at first and second hops of the measure delay.
        This value returned by this function + measured difference will serve
        as the sample RTT on the game client.
        """
        return rcv_time + 0.1 * randrange(1, 9)
