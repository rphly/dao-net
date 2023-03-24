from game.models.player import Player
import json
import time


class Packet:
    """
    We enclose all data to be sent over the network in a packet.

    Accepted data:
    - Action
    - PeeringCompleted
    - SyncReq
    - SyncAck
    - SyncUpdate
    - LobbyRegister
    - LobbyLeave
    - LobbyStart
    - LobbySaveTracker
    - ss_nak
    - ss_ack
    - vote
    - sat_down
    """

    def __init__(self, data, player: Player, packet_type: str):
        self.data = data
        self.player = player
        self.packet_type = packet_type
        self.createdAt = int(time.time())

    def get_data(self):
        return self.data

    def get_player(self):
        return self.player

    def get_packet_type(self):
        return self.packet_type

    def get_created_at(self):
        return self.createdAt

    def json(self) -> str:
        """Return a json representation of the packet."""
        return json.dumps(dict(
            data=self.data,
            player=self.player.dict(),
            packet_type=self.packet_type,
            created_at=self.createdAt
        ))

    def from_json(d):
        """Return a packet from a json representation."""
        return Packet(
            d["data"],
            Player(d["player"].get("name")),
            d["packet_type"]
        )

    def __str__(self):
        return f"Packet: {str(self.data)}"


class Ack(Packet):
    """Acknowledge a packet."""

    def __init__(self, player: Player):
        super().__init__(None, player, "ack")


class Nak(Packet):
    """Nack a packet."""

    def __init__(self, player: Player):
        super().__init__(None, player, "nak")


class PeeringCompleted(Packet):
    """Peering has been completed."""

    def __init__(self, player: Player):
        super().__init__(None, player, "peering_completed")
# Timer Packets
class SyncReq(Packet):
    """Send a Sync packet"""

    def __init__(self, player: Player):
        super().__init__(None, player, "sync_req")

class SyncAck(Packet):
    """Send a Sync packet."""

    def __init__(self, player: Player):
        super().__init__(None, player, "sync_ack")

class PeerSyncAck(Packet):
    """Send peer their delay measurement."""

    def __init__(self, data, player: Player):
        super().__init__(data, player, "peer_sync_ack")

class UpdateLeader(Packet):
    """Update the leader of syncing."""

    def __init__(self, data: int, player: Player):
        super().__init__(data, player, "update_leader")
# End of Timer Packets
class ReadyToStart(Packet):
    """Ready to start game"""

    def __init__(self, player: Player):
        super().__init__(None, player, "ready_to_start")


class AckStart(Packet):
    """AckReady and Start"""

    def __init__(self, player: Player):
        super().__init__(None, player, "ack_start")


class SatDown(Packet):
    """Player has sat down."""

    def __init__(self, player: Player):
        super().__init__(None, player, "sat_down")

# initial transport layer initiation
class ConnectionRequest(Packet):
    """Initial request to connect"""

    def __init__(self, player: Player):
        super().__init__(None, player, "connection_req")


class ConnectionEstab(Packet):
    """Connection has been established."""

    def __init__(self, player: Player):
        super().__init__(None, player, "connection_estab")
