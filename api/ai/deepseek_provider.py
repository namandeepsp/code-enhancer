import httpx
from .base import AIProvider, AIResponse


class DeepSeekProvider(AIProvider):
    _BASE_URL = "https://api.deepseek.com/v1/chat/completions"

    def __init__(self, api_key: str, model: str = "deepseek-chat", timeout: int = 30):
        self._api_key = api_key
        self._model = model
        self._timeout = timeout

    def is_available(self) -> bool:
        return bool(self._api_key)

    async def complete(self, messages: list[dict], timeout: int = None) -> AIResponse:
        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": 0.2,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self._BASE_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                timeout=timeout or self._timeout,
            )
            response.raise_for_status()

        data = response.json()
        choice = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})

        return AIResponse(
            content=choice,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
        )
