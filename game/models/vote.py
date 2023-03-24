from game.models.player import Player
from game.transport.packet import Packet


class Vote(Packet):
    def __init__(self, playerid: str, player: Player):
        super().__init__(playerid, player, "vote")

    def __str__(self):
        return f"Vote: {self.__class__.__name__}"
