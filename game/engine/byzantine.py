from game.engine.core import Core
from game.models.action import Action


class Byzantine(Core):
    def __init__(self,):
        super().__init__()

    def send_action(self, data: Action):
        print("Do some consensus thing here")
        super().send_action(data)
        ...
