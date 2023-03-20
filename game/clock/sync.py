import functools
import time


class Sync:
    """Synchronizes game actions."""
    def __init__(self, player_id, socket):
        self.player_id = player_id
        self.socket = socket
        self.is_host = False
        self.host_timer


    def measure_delay(player_id, socket):
        creation_time = time.time()
        
        

    def add_delay(delay=0):
        def wr(fn):
            @functools.wraps(fn)
            def w(*args, **kwargs):
                print("adding delay to function")
                time.sleep(delay)
                return fn(*args, **kwargs)
            return w
        return wr
