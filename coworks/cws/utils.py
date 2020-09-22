from threading import Thread
from functools import wraps
import platform
import sys


def threaded(f):
    @wraps(f)
    def threaded_func(*args, **kwargs):
        thread = Thread(target=f, args=args, kwargs=kwargs)
        thread.start()

    return threaded_func


def get_system_info():
    python_info = f"python {sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}"
    platform_system = platform.system().lower()
    platform_release = platform.release()
    platform_info = f"{platform_system} {platform_release}"
    return f"{python_info}, {platform_info}"
