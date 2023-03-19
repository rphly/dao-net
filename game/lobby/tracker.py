class Tracker():
    def __init__(self, data=None):
        if data:
            self.tracker_list = data.get("tracker_list")
        else:
            self.tracker_list = {}

    def add(self, player_id, port):
        # save port number
        self.tracker_list[player_id] = port

    def remove(self, player_id):
        # remove player from tracker
        self.tracker_list.pop(player_id)

    def get_port(self, player_id):
        # return port number
        return self.tracker_list[player_id]

    def is_port_used(self, port):
        return port in self.tracker_list.values()

    def get_players(self):
        # return list of players
        return list(self.tracker_list.keys())

    def get_player_count(self):
        # return number of players
        return len(self.tracker_list) + 1

    def __str__(self):
        return f"Current players: {str(list(self.tracker_list.keys()))}"
