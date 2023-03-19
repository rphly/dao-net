from game.engine.core import Core
from game.models import Player
import config


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
            self._lobby()
        if state == "INIT":
            self._init()
        elif state == "AWAIT_KEYPRESS":
            return self._await_keypress()

        elif state == "RCV_OTHERS_KEYPRESS":
            return self._rcv_others_keypress()

        elif state == "END_ROUND":
            self._end_round
        elif state == "END_GAME":
            return self._end_game()

    def _lobby(self):
        # check for players
        # if not enough players:
        # call next immediately
        players = self.get_players()
        if len(players) == config.NUM_PLAYERS:
            self._set_state("INIT")
        self.next()

    def _init(self):
        # start counting down
        # do all the network stuff here
        self._set_state("AWAIT_KEYPRESS")
        self.next()

    def _await_keypress(self):
        # wait for current player keypress
        # verify if keypress is qwerty or overlapped

        # if received other keypress

        # if my keypress, await round end
        self.next()

    def _rcv_others_keypress(self):
        # handle others kp
        # if i haven't press, go back to waiting for my keypress
        #
        if (self._my_keypress is None):
            self._set_state("AWAIT_KEYPRESS")
        else:
            if len(self._get_round_inputs) == self._get_num_alive():
                self._set_state("END_ROUND")

    def _end_round(self):
        # if player failed to input/ find chair, he loses
        for player in self._players.keys:
            if player not in self._round_inputs:
                player.alive = False

        self._reduce_chairs()

        # if num of chairs = 1, end game
        if self._get_chairs() == 1:
            self._set_state("END_GAME")

        else:
            self._set_state("AWAIT_KEYPRESS")

        # clear all inputs
        self._round_inputs = {}

        self.next()

    def _end_game(self):
        # terminate all connections
        ...

    def next(self):
        self._state = self.trigger_handler(self._state)
        return self._state

    def register(self, player: Player):
        self._players[player.id] = player

    def get_players(self) -> dict[str, Player]:
        return self._players

    def _set_state(self, state):
        self._state = state

    def _reduce_chairs(self):
        self._current_chairs = self._current_chairs - 1

    def _get_chairs(self):
        return self._current_chairs

    def _get_round_inputs(self):
        return self._round_inputs

    # function to insert inputs, receiver needs to call this

    def _insert_input(self, player_id: str, keypress):
        # save dict of player keypresses
        # only allow player to insert input if alive
        if player_id.is_alive() and (player_id not in self._round_inputs):
            self._round_inputs[player_id] = keypress
            return keypress

    def _get_num_alive(self):
        count = 0
        for player in self.get_players():
            if player.is_alive:
                count = count + 1

        return count
