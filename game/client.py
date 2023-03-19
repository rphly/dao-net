from game.engine.core import Core
from game.models import Player
import config
import keyboard


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
        players = self._players
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

    def end_round(self):
        # 1) I have lost the game: lose state
        # 2) Another player has lost the game

        for player in self._players.keys():
            if player not in self._round_inputs.values():
                self._players.pop(player)

        # clear all inputs, remove last chair
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
        ...


######### helper functions #########


    def _next(self):
        self._state = self.trigger_handler(self._state)
        return self._state

    def _register(self, player: Player):
        self._players[player.id] = player

    def _insert_input(self, player: Player, keypress):
        self._my_keypress = keypress
        print(f"Attempt to sit at {keypress}")
        keyboard.remove_all_hotkeys()

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
