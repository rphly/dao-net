from game.models.player import Player
import json


class Action:
    def __init__(self, data: dict, player: Player):
        self.data = data
        self.player = player

    def get_data(self):
        # Q
        return self.data

    def get_player(self):
        return self.player

    def to_json(self):
        return json.dumps(dict(
            data=self.get_data(),
            payload_type="action",
            player=self.get_player()
        ))

    def __str__(self):
        return f"Action: {self.__class__.__name__}"
