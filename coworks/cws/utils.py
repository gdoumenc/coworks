from threading import Thread
from functools import wraps


def threaded(f):
    @wraps(f)
    def threaded_func(*args, **kwargs):
        thread = Thread(target=f, args=args, kwargs=kwargs)
        thread.start()

    return threaded_func
