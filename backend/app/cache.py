import time
import asyncio
from typing import Any


class TTLCache:
    """Tiny async-safe in-memory cache. Swap for Redis in production."""

    def __init__(self, ttl: int = 300):
        self.ttl = ttl
        self._store: dict[str, tuple[float, Any]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str):
        async with self._lock:
            hit = self._store.get(key)
            if not hit:
                return None
            ts, value = hit
            if time.time() - ts > self.ttl:
                self._store.pop(key, None)
                return None
            return value

    async def set(self, key: str, value: Any):
        async with self._lock:
            self._store[key] = (time.time(), value)
