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
        self._inputs: dict[str, str] = {}

        self._current_chairs: int = config.NUM_CHAIRS

    def state(self):
        return self._state

    def trigger_handler(self, state):
        if state == "LOBBY":
            self._lobby()
        if state == "INIT":
            self._init()
        elif state == "ready":
            self._ready()
        elif state == "PLAY":
            return self._play()
        elif state == "END_ROUND":
            self._
        elif state == "end":
            return self._end()

    def _lobby(self):
        # check for players
        # if not enough players:
        # call next immediately
        players = self.get_players
        if len(players) == config.NUM_PLAYERS:
            self._set_state("INIT")
        self.next()

    def _init(self):
        # start counting down
        # do all the network stuff here

        ...

    def _ready(self):
        # if not yet sent,
        # send ready to all clients
        # if not all ready, call next immediately
        # if all ready go to play state
        # next()
        ...

    def _play(self):
        # wait for current player keypress
        # verify if keypress is qwerty or overlapped
        ...

    def _end_round(self):
        # if player failed to input/ find a chair, kick him
        for player in self._players.keys:
            if player not in self._inputs:
                player.alive = False

        # reduce chair by 1
        self._reduce_chairs()
        self._set_state("PLAY")
        self.next()

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

    def _insert_input(self, player: Player, keypress):
        # save dict of player keypresses
        # only allow player to insert input if alive
        if player.is_alive:
            self._inputs[player] = keypress
            return keypress
