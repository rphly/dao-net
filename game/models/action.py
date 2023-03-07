from game.models.player import Player


class Action:
    def __init__(self, data: dict, player: Player):
        self.data = data
        self.player = player

    def get_data(self):
        return self.data

    def get_player(self):
        return self.player

    def __str__(self):
        return f"Action: {self.__class__.__name__}"
