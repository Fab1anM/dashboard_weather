from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(slots=True)
class _CacheEntry(Generic[T]):
    value: T
    expires_at: datetime


class TTLCache(Generic[T]):
    def __init__(self, ttl_seconds: int) -> None:
        self._ttl = timedelta(seconds=ttl_seconds)
        self._entries: dict[str, _CacheEntry[T]] = {}

    def get(self, key: str) -> T | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if datetime.now() >= entry.expires_at:
            del self._entries[key]
            return None
        return entry.value

    def set(self, key: str, value: T) -> None:
        self._entries[key] = _CacheEntry(
            value=value,
            expires_at=datetime.now() + self._ttl,
        )
