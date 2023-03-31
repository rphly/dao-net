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

    def add_delay(self, player_id):
        """
        Adds a random delay at first and second hops of the measure delay.
        This value returned by this function + measured difference will serve
        as the sample RTT on the game client.
        """
        if len(self._delay_dict) != len(self.leader_list) - 1:
            return
        else:
            delay = self._delay_dict[player_id]
            time.sleep(delay)
        return

    def get_ordered_delays(self):
        return sorted(self._delay_dict.items(), key=lambda x:x[1], reverse=True)
    
    def get_wait_times(self):
        ordered_delays = self.get_ordered_delays()
        wait_times = []

        for i in range(len(ordered_delays)-1):
            wait_times.append(ordered_delays[i] - ordered_delays[i+1])

        return wait_times
