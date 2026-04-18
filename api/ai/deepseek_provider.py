import asyncio
import httpx
from .base import AIProvider, AIResponse


class AIProviderError(Exception):
    def __init__(self, message: str, status_code: int = 0, retryable: bool = False):
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


# Status codes worth retrying — server-side or transient errors
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class DeepSeekProvider(AIProvider):
    _BASE_URL = "https://api.deepseek.com/v1/chat/completions"

    def __init__(
        self,
        api_key: str,
        model: str = "deepseek-chat",
        timeout: int = 30,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
    ):
        self._api_key = api_key
        self._model = model
        self._timeout = timeout
        self._max_retries = max_retries
        self._retry_base_delay = retry_base_delay

    def is_available(self) -> bool:
        return bool(self._api_key)

    async def complete(self, messages: list[dict], timeout: int = None) -> AIResponse:
        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": 0.2,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        effective_timeout = timeout or self._timeout
        last_error: Exception = None

        for attempt in range(1, self._max_retries + 1):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        self._BASE_URL,
                        json=payload,
                        headers=headers,
                        timeout=effective_timeout,
                    )

                # 4xx errors (except 429) are client mistakes — retrying won't help
                if response.status_code not in _RETRYABLE_STATUS_CODES:
                    response.raise_for_status()

                # Server-side or transient error — back off and retry
                if response.status_code in _RETRYABLE_STATUS_CODES:
                    last_error = AIProviderError(
                        f"DeepSeek API error {response.status_code}: {response.text[:200]}",
                        status_code=response.status_code,
                        retryable=True,
                    )
                    if attempt < self._max_retries:
                        # Exponential backoff: 1s, 2s, 4s
                        delay = self._retry_base_delay * (2 ** (attempt - 1))
                        await asyncio.sleep(delay)
                        continue
                    raise last_error

                # Success — parse response
                data = response.json()
                choice = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})

                return AIResponse(
                    content=choice,
                    prompt_tokens=usage.get("prompt_tokens", 0),
                    completion_tokens=usage.get("completion_tokens", 0),
                    total_tokens=usage.get("total_tokens", 0),
                )

            except (httpx.TimeoutException, httpx.ConnectError, httpx.RemoteProtocolError) as e:
                last_error = AIProviderError(
                    f"Network error on attempt {attempt}: {str(e)}",
                    retryable=True,
                )
                if attempt < self._max_retries:
                    delay = self._retry_base_delay * (2 ** (attempt - 1))
                    await asyncio.sleep(delay)
                    continue
                raise last_error

            except AIProviderError:
                raise

            except Exception as e:
                raise AIProviderError(f"Unexpected error: {str(e)}", retryable=False)

        raise last_error
