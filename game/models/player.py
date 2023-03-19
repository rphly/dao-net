import uuid


class Player:
    def __init__(self, name: str, ):
        self.name = name
        self.id = str(uuid.uuid4())
        self.is_alive = True

    def id(self):
        return self.id

    def is_alive(self):
        return self.is_alive

    def kill(self):
        self.is_alive = False

    def __str__(self):
        return f"{self.name} (#{self.id})"
