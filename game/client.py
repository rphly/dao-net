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

        self._round_inputs: dict[str, str] = {}

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
        players = self.get_players()
        if len(players) == config.NUM_PLAYERS:
            self._set_state("INIT")
        self._next()

    def init(self):
        # start counting down
        # do all the network stuff here
        self._set_state("AWAIT_KEYPRESS")
        self._next()

    def await_keypress(self):
        # 1) Received local keypress
        if self._my_keypress is None:
            for k in ["Q", "W", "E", "R", "T", "Y"]:
                keyboard.add_hotkey(k, lambda: self._insert_input(k))
        else:
            # 2) SelectingSeat success: change state
            # 3) SelectingSeat Failure: clear my keypress
            pass

        # 4) Received others keypress

        # if received other keypress

        self._next()

    def process_others_keypress(self, data):
        # handle others kp
        success = self._process_others_keypress(data)

        if (self._my_keypress is None):
            self._set_state("AWAIT_KEYPRESS")
        else:
            if len(self._get_round_inputs) == self._get_num_alive():
                self._set_state("END_ROUND")

    def end_round(self):
        # if player failed to input/ find chair, he loses
        for player in self._get_round_inputs.keys():
            if player not in self._round_inputs:
                player.kill()

        self._reduce_chairs()

        # if num of chairs = 1, end game
        if self._get_chairs() == 1:
            self._set_state("END_GAME")

        else:
            self._set_state("AWAIT_KEYPRESS")

        # clear all inputs
        self._clear_round_inputs()

        self._next()

    def end_game(self):
        # terminate all connections
        ...

    def _next(self):
        self._state = self.trigger_handler(self._state)
        return self._state

    def _register(self, player: Player):
        self._players[player.id] = player

    def _get_players(self) -> dict[str, Player]:
        return self._players

    def _set_state(self, state):
        self._state = state

    def _reduce_chairs(self):
        self._current_chairs = self._current_chairs - 1

    def _get_chairs(self):
        return self._current_chairs

    def _get_round_inputs(self):
        return self._round_inputs

    def _clear_round_inputs(self):
        self._round_inputs = {}

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
