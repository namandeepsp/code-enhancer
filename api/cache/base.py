from abc import ABC, abstractmethod
from typing import Optional


class CacheService(ABC):
    @abstractmethod
    def get(self, key: str) -> Optional[dict]: ...

    @abstractmethod
    def set(self, key: str, value: dict, ttl_seconds: int) -> None: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...

    @abstractmethod
    def clear(self) -> None: ...
