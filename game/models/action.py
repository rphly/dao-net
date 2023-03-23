from game.models.player import Player
from game.transport.packet import Packet


class Action(Packet):
    def __init__(self, data: dict, player: Player):
        super().__init__(data, player, "action")

    def __str__(self):
        return f"Action: {super().get_packet_type()}"
