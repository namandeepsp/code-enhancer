import hashlib
import os
from typing import Optional

import diskcache

from .base import CacheService


def make_cache_key(task: str, language: str, technology: str, code: str, prompt: str) -> str:
    normalized = code.strip().lower()
    raw = f"{task}|{language}|{technology}|{normalized}|{prompt}"
    return hashlib.sha256(raw.encode()).hexdigest()


class DiskCacheService(CacheService):
    def __init__(self, path: str, ttl_hours: int, size_limit_mb: int):
        self._ttl_seconds = ttl_hours * 3600
        self._cache = diskcache.Cache(
            directory=path,
            size_limit=size_limit_mb * 1024 * 1024,
        )

    def get(self, key: str) -> Optional[dict]:
        return self._cache.get(key)

    def set(self, key: str, value: dict, ttl_seconds: Optional[int] = None) -> None:
        self._cache.set(key, value, expire=ttl_seconds or self._ttl_seconds)

    def delete(self, key: str) -> None:
        self._cache.delete(key)

    def clear(self) -> None:
        self._cache.clear()
