import asyncio
import httpx
from .base import AIProvider, AIResponse
from .deepseek_provider import AIProviderError, _RETRYABLE_STATUS_CODES


class GeminiProvider(AIProvider):
    _BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    _PRIMARY_MODEL = "gemini-2.5-flash"
    _FALLBACK_MODEL = "gemini-flash-latest"

    def __init__(
        self,
        api_key: str,
        timeout: int = 30,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
    ):
        self._api_key = api_key
        self._timeout = timeout
        self._max_retries = max_retries
        self._retry_base_delay = retry_base_delay

    def is_available(self) -> bool:
        return bool(self._api_key)

    def _build_payload(self, messages: list[dict]) -> dict:
        # Gemini separates system prompt from conversation turns
        system_parts = []
        contents = []

        for msg in messages:
            if msg["role"] == "system":
                system_parts.append({"text": msg["content"]})
            else:
                # Gemini uses "model" instead of "assistant"
                role = "model" if msg["role"] == "assistant" else "user"
                contents.append({"role": role, "parts": [{"text": msg["content"]}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.2,
            },
        }

        if system_parts:
            payload["systemInstruction"] = {"parts": system_parts}

        return payload

    def _parse_response(self, data: dict) -> tuple[str, int, int, int]:
        """Extract content and token usage from Gemini response."""
        content = data["candidates"][0]["content"]["parts"][0]["text"]
        usage = data.get("usageMetadata", {})
        prompt_tokens = usage.get("promptTokenCount", 0)
        completion_tokens = usage.get("candidatesTokenCount", 0)
        total_tokens = usage.get("totalTokenCount", 0)
        return content, prompt_tokens, completion_tokens, total_tokens

    async def _call(self, model: str, payload: dict, timeout: int) -> AIResponse:
        """Make a single API call to a specific model."""
        url = self._BASE_URL.format(model=model)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=payload,
                # Gemini uses x-goog-api-key header, not a query param
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": self._api_key,
                },
                timeout=timeout,
            )

        if response.status_code not in _RETRYABLE_STATUS_CODES:
            response.raise_for_status()

        if response.status_code in _RETRYABLE_STATUS_CODES:
            raise AIProviderError(
                f"Gemini API error {response.status_code}: {response.text[:200]}",
                status_code=response.status_code,
                retryable=True,
            )

        content, prompt_tokens, completion_tokens, total_tokens = self._parse_response(response.json())
        return AIResponse(
            content=content,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )

    async def complete(self, messages: list[dict], timeout: int = None) -> AIResponse:
        payload = self._build_payload(messages)
        effective_timeout = timeout or self._timeout
        last_error: Exception = None

        for attempt in range(1, self._max_retries + 1):
            # Use primary model on first attempt, fall back to gemini-1.5-flash on subsequent attempts
            model = self._PRIMARY_MODEL if attempt == 1 else self._FALLBACK_MODEL

            try:
                return await self._call(model, payload, effective_timeout)

            except AIProviderError as e:
                last_error = e
                if not e.retryable:
                    raise

                if attempt < self._max_retries:
                    delay = self._retry_base_delay * (2 ** (attempt - 1))
                    # Log fallback so it's visible in structured logs
                    if attempt == 1:
                        print(f"[GeminiProvider] Primary model failed ({e.status_code}), falling back to {self._FALLBACK_MODEL}")
                    await asyncio.sleep(delay)
                    continue

                raise last_error

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
