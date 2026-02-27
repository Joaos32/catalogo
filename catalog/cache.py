import time
from typing import Any, Callable, Dict, Tuple


class TTLCache:
    def __init__(self, ttl_seconds: int = 3600):
        self.ttl = ttl_seconds
        self.store: Dict[Any, Tuple[Any, float]] = {}

    def get(self, key: Any) -> Any:
        entry = self.store.get(key)
        if entry:
            value, expiry = entry
            if expiry > time.time():
                return value
            else:
                # expired
                self.store.pop(key, None)
        return None

    def set(self, key: Any, value: Any) -> None:
        self.store[key] = (value, time.time() + self.ttl)


# global cache instance, TTL can be adjusted via environment
cache = TTLCache()


def cached(func: Callable) -> Callable:
    """Decorator that caches function results in the module-level TTLCache.

    The key is constructed from the function name and its arguments.
    """

    def wrapper(*args, **kwargs):
        key = (func.__name__, args, tuple(sorted(kwargs.items())))
        cached_val = cache.get(key)
        if cached_val is not None:
            return cached_val
        result = func(*args, **kwargs)
        cache.set(key, result)
        return result

    return wrapper
