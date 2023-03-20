import functools
import time

from game.lobby.tracker import Tracker
from game.transport.transport import Transport

class Sync:
    """Synchronizes game actions."""
    def __init__(self, my_name: str, tracker: Tracker, transportLayer: Transport):
        self.name = my_name
        self.ip_port = self.tracker.get_ip_port(my_name)
        self.transport_layer = transportLayer
        self.leader_idx = 0
        self.leader_list = tracker.get_leader_list()

        while self.ip_port == self.leader_list[self.leader_idx]:
            self.measure_delay()


    def measure_delay():
        self.
        
    def send_sync_req():

        

    def add_delay(delay=0):
        def wr(fn):
            @functools.wraps(fn)
            def w(*args, **kwargs):
                print("adding delay to function")
                time.sleep(delay)
                return fn(*args, **kwargs)
            return w
        return wr
