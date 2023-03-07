from typing import Union
from game.models.action import Action
import json
import time


class Packet:
    """
    We enclose all data to be sent over the network in a packet.

    Accepted data:
    - Action
    - SyncReq
    - SyncAck
    - SyncUpdate
    """
    ACCEPTED_TYPES = Union[Action, dict]

    def __init__(self, payload: ACCEPTED_TYPES):
        self.data = payload.get_data()
        self.payloadType = get_type(payload)
        self.createdAt = int(time.time())

    def json(self) -> str:
        """Return a json representation of the packet."""
        return json.dumps(dict(
            data=self.data,
            payload_type=self.payloadType,
            created_at=self.createdAt
        ))

    def __str__(self):
        return f"Packet: {str(self.data)}"


def get_type(p) -> str:
    """Return the type of the payload."""
    if isinstance(p, Action):
        return "action"
    return "unknown"
