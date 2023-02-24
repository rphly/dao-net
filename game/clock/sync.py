import functools
import time


class Sync:
    """Synchronizes game actions."""

    def add_delay(delay=0):
        def wr(fn):
            @functools.wraps(fn)
            def w(*args, **kwargs):
                print("adding delay to function")
                time.sleep(delay)
                return fn(*args, **kwargs)
            return w
        return wr
