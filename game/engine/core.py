from game.clock import sync
from game.models.action import Action


class Core:
    """Default protocol used for game operations."""

    def __init__(self,):
        self.clock = sync.Sync(2)

    # or some other value. may be good to just rely on clock and decouple this logic from the engine
    @sync.add_delay(2)
    def send_action(self, data: Action):
        ...
