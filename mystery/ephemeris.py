"""Serialize this package's calls when configuring Swiss Ephemeris modes."""
from functools import wraps
from threading import RLock

LOCK = RLock()


def serialized(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        with LOCK:
            return function(*args, **kwargs)
    return wrapped
