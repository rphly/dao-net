from game.engine.core import Core
from game.models import Player


class Client():
    """
    Game FSM 
    """

    def __init__(self, engine=Core(),):
        super().__init__()
        self._game_engine: Core = engine
        self._players: dict[str, Player] = {}

    def state(self):
        return self._state

    def trigger_handler(self, state):
        if state == "init":
            self._init()
            return "ready"
        elif state == "init_wait":
            self._init()
            return "init_wait"
        elif state == "ready":
            self._ready()
            return "play"
        elif state == "ready_wait":
            self._ready()
            return "ready_wait"
        elif state == "play":
            return "end"
        elif state == "end":
            return "end"

    def _init(self):
        # if not yet sync:
        # init game clock sync
        # if not sync done:
        # go to init_wait
        # else when all done go to ready
        ...

    def _ready(self):
        # if not yet sent,
        # send ready to all clients
        # if not all ready, go to ready_wait state
        # if all ready go to play state
        # next()
        ...

    def _start(self):
        ...

    def _start(self):
        ...

    def next(self):
        self._state = self.trigger_handler(self._state)
        return self._state

    def register(self, player: Player):
        self._players[player.id] = player

    def get_players(self) -> dict[str, Player]:
        return self._players
