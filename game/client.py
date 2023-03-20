import json
from game.engine.core import Core
from game.models.player import Player
from game.models.action import Action
from game.lobby.tracker import Tracker
from game.transport.transport import Transport
from game.transport.packet import Packet, Nak, Ack
import config
import keyboard
import socket
from time import time


class Client():
    """
    Game FSM 
    """

    def __init__(self, my_name: str, tracker: Tracker):
        super().__init__()

        self._state: str = "PEERING"
        self._players: dict[str, Player] = {}
        self._votekick: dict[str, int] = {}
        self._myself = Player(name=my_name)
        self.game_over = False
        self.tracker = tracker

        self._round_inputs: dict[str, str] = {
            "Q": None,
            "W": None,
            "E": None,
            "R": None,
            "T": None,
            "Y": None,
        }

        self._current_chairs: int = config.NUM_CHAIRS
        self._my_keypress = None

        # selecting seats algo
        self._nak_count = 0
        self._ack_count = 0
        self._is_selecting_seat = False

        # transport layer stuff
        self._transportLayer = Transport(
            self.tracker.get_ip_port(my_name)[1], tracker=self.tracker)

    def _state(self):
        return self._state

    def start(self):
        while not self.game_over:
            self._next()

    def trigger_handler(self, state):
        if state == "PEERING":
            self.peering()

        if state == "SYNCHRONIZE_CLOCK":
            self.sync_clock()

        if state == "INIT":
            self.init()

        elif state == "AWAIT_KEYPRESS":
            self.await_keypress()

        elif state == "PROC_OTHERS_KEYPRESS":
            self.process_others_keypress()

        elif state == "END_ROUND":
            self.end_round

        elif state == "END_GAME":
            self.end_game()

    def peering(self):
        if self._transportLayer.all_connected():
            self._state = "SYNCHRONIZE_CLOCK"
        self._next()

    def sync_clock(self):
        # logic to sync clocks here
        time.sleep(10)
        self._state = "INIT"
        self._next()

    def init(self):
        # start counting down
        # do all the network stuff here
        self._state("AWAIT_KEYPRESS")
        self._next()

    def await_keypress(self):
        # 1) Received local keypress
        if self._my_keypress is None:
            for k in ["Q", "W", "E", "R", "T", "Y"]:
                keyboard.add_hotkey(k, lambda: self._insert_input(k))
        else:
            # 2) SelectingSeat
            self._selecting_seats()

        if self._is_selecting_seat:
            thresh = (config.NUM_PLAYERS // 2)
            if self._nak_count >= thresh:
                # SelectingSeat failed
                self._my_keypress = None
                self._nak_count = 0
                self._ack_count = 0
                self._is_selecting_seat = False

            if self._ack_count > thresh:
                # SelectingSeat success
                self._state("END_ROUND")
                self._next()
                return

        # 4) Check for others' keypress, let transport layer handler handle it
        self._checkTransportLayerForIncomingData()
        self._next()

    def byzantine_send(self):
        # determine who has lost
        # send who to kick to everyone else
        player_to_kick = None
        for player in self._players.keys():
            if player not in self._round_inputs.values():
                player_to_kick = player

        for player in self._players.keys():
            _send_vote(player_to_kick, player)

        # init votekick dict
        # should put at init/ start of round
        self._votekick = self._players
        self._votekick = dict.fromkeys(self._votekick, 0)

        self._state = "BYZANTINE_RCV"

        self._next()

    def byzantine_recv(self):
        # wait till we receive everyone's vote
        # remove the most voted player
        if _rcv_vote(data):
            self._votekick[data.player_to_kick] = self._votekick[data.player_to_kick] + 1

        # if num of votes == num of players
        if sum(self._votekick.values()) == len(self._players):
            max_vote = max(self._votekick.values())
            # in case there is a tie

            to_be_kicked = [key for key,
                            value in self._votekick.items() if value == max_vote]

            # 1) if only one voted, remove from player_list
            if len(to_be_kicked) == 1:
                self._players.pop(to_be_kicked[0])

            # 2) if tied, just go to next round
            self._votekick = {}
            self._state = "END_ROUND"

        else:
            self._state = "BYZANTINE_RCV"

        self._next()

    def end_round(self):

        # clear all inputs, remove last chair
        d = self._round_inputs
        d = {value: None for value in d}
        d.popitem()
        self._round_inputs = d

        # if no chairs left, end the game, else reset
        if len(self._round_inputs.keys() < 1):
            self._state = "END_GAME"
        else:
            self._state = "AWAIT_INPUT"

        self._next()

    def end_game(self):
        # terminate all connections
        self._transportLayer.shutdown()
        self.game_over = True


######### helper functions #########


    def _checkTransportLayerForIncomingData(self):
        """handle data being received from transport layer"""
        data = self._transportLayer.receive()

        if data:
            pkt_json = json.loads(data)

            if pkt_json.get("payload_type") == "action":
                # keypress
                action = Action(pkt_json.get("data"), Player(
                    pkt_json.get("player").get("id")))
                self._receiving_seats(action)

            elif pkt_json.get("payload_type") == "ss_nak":
                # drop the nak/ack if we've moved on
                if self._is_selecting_seat:
                    self._nak_count += 1

            elif pkt_json.get("payload_type") == "ss_ack":
                # drop the nak/ack if we've moved on
                if self._is_selecting_seat:
                    self._ack_count += 1

    def _selecting_seats(self):
        self._is_selecting_seat = True
        for player in self._players().values():  # TODO: send in order using time clock
            self._send_seat(player)

    def _send_seat(self, player: Player):
        pkt = Packet(Action(dict(seat=self._my_keypress), player))
        self._transportLayer.send(pkt, player.id)

    def _send_ack(self, player: Player):
        self._transportLayer.send(Packet(Ack(self._myself)), player.id)

    def _send_nak(self, player: Player):
        self._transportLayer.send(Packet(Nak(self._myself)), player.id)

    def _next(self):
        self._state = self.trigger_handler(self._state)
        return self._state

    def _register(self, player: Player):
        self._players[player.id] = player

    def _insert_input(self, keypress):
        self._my_keypress = keypress
        keyboard.remove_all_hotkeys()

    def _receiving_seats(self, action: Action):
        seat = action.get_data().get("seat")
        player = action.get_player()
        if seat:
            if self._round_inputs[seat] is None:
                self._round_inputs[seat] = player
                self._send_ack(player)
                return
        self._send_nak(player)
