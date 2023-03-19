from game.engine.core import Core
from game.models import Player
import config
import keyboard
import socket


class Client():
    """
    Game FSM 
    """

    def __init__(self, engine=Core(),):
        super().__init__()
        self._game_engine: Core = engine
        self._state: str = "LOBBY"
        self._players: dict[str, Player] = {}

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

        # tracker, connection pool
        self._connection_pool: dict[str, socket.socket] = {}

    def state(self):
        return self._state

    def trigger_handler(self, state):
        if state == "LOBBY":
            self.lobby()

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

    def lobby(self):
        players = self.get_players()
        if len(players) == config.NUM_PLAYERS:
            self._state("INIT")
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
            # 2) SelectingSeat success and everyone submitted: change state
            is_success = self._selecting_seats()
            if is_success and all(self._round_inputs.values()):
                self._state("END_ROUND")
                _send_round_end()

            # 3) SelectingSeat Failure: clear my keypress
            else:
                self._my_keypress = None

        # 4) Received others keypress
        if _rcv_keypress(data):
            self._receiving_seats(data)

        self._next()

    def _selecting_seats(self) -> bool():
        nak_count = 0
        for player in self._players().keys():
            res = _send_seat(player)
            if res == NAK:
                nak_count += 1
        if nak_count > len(self._players):
            return False
        return True

    def _receiving_seats(self, data):
        if self._round_inputs[data.seat] is None:
            self._round_inputs[data.seat] = data.player
            _send_ack(data.player)
            return
        _send_nak(data.player)

    def end_round(self):

        self._next()

    def end_game(self):
        # terminate all connections
        ...

    def _next(self):
        self._state = self.trigger_handler(self._state)
        return self._state

    def _register(self, player: Player):
        self._players[player.id] = player

    # function to insert inputs, receiver needs to call this

    def _insert_input(self, player: Player, keypress):
        # save dict of player keypresses
        # only allow player to insert input if alive
        self._my_keypress = keypress
        print(f"Attempt to sit at {keypress}")
        keyboard.remove_all_hotkeys()

    def _process_others_input(self, player: Player, keypress):
        ...

    def _get_num_alive(self):
        count = 0
        for player in self.get_players():
            if player.is_alive:
                count = count + 1

        return count
