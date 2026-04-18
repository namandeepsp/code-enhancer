from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class AIResponse:
    content: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class AIProvider(ABC):
    @abstractmethod
    async def complete(self, messages: list[dict], timeout: int) -> AIResponse: ...

    @abstractmethod
    def is_available(self) -> bool: ...
