from typing import Union
from game.models.action import Action
from game.models.player import Player
import json
import time


class Ack():
    """Acknowledge a packet."""

    def __init__(self, player: Player):
        self.data = None
        self.player = player

    def get_data(self):
        return self.data

    def get_player(self):
        return self.player


class Nak():
    """Nack a packet."""

    def __init__(self, player: Player):
        self.data = None
        self.player = player

    def get_data(self):
        return self.data

    def get_player(self):
        return self.player


class Packet:
    """
    We enclose all data to be sent over the network in a packet.

    Accepted data:
    - Action
    - SyncReq
    - SyncAck
    - SyncUpdate
    - LobbyRegister
    - LobbyLeave
    - LobbyStart
    - LobbySaveTracker
    - ss_nak
    - ss_ack
    """
    ACCEPTED_TYPES = Union[Action, Ack, Nak, dict]

    def __init__(self, payload: ACCEPTED_TYPES):
        self.data = payload.get_data()
        self.player = payload.get_player()
        self.payloadType = get_type(payload)
        self.createdAt = int(time.time())

    def json(self) -> str:
        """Return a json representation of the packet."""
        return json.dumps(dict(
            data=self.data,
            player=self.player,
            payload_type=self.payloadType,
            created_at=self.createdAt
        ))

    def __str__(self):
        return f"Packet: {str(self.data)}"


def get_type(p) -> str:
    """Return the type of the payload."""
    if isinstance(p, Action):
        return "action"
    if isinstance(p, Ack):
        return "ack"
    if isinstance(p, Nak):
        return "nak"
    return "unknown"
