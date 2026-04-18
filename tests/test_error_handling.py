import json
import pytest
import asyncio
import tempfile
from unittest.mock import AsyncMock, patch

from api.ai.base import AIResponse
from api.ai.deepseek_provider import AIProviderError
from api.ai.mock_provider import MockAIProviderUnreliable
from api.services.response_parser import ResponseParser, ParseError
from api.services.enhancer_service import EnhancerService
from api.cache import DiskCacheService
from api.models import EnhanceRequest


# --- ResponseParser edge cases ---

class TestResponseParserResilience:

    def setup_method(self):
        self.parser = ResponseParser()

    def _ai(self, content: str) -> AIResponse:
        return AIResponse(content=content, prompt_tokens=10, completion_tokens=20, total_tokens=30)

    def test_strips_markdown_fences(self):
        raw = '```json\n{"already_optimal": false, "variants": [{"title": "T", "description": "D", "code": "x=1"}]}\n```'
        ok, data = self.parser.parse_enhance(self._ai(raw))
        assert not ok
        assert len(data.variants) == 1

    def test_extracts_json_with_preamble_text(self):
        raw = 'Here is the result:\n{"already_optimal": false, "variants": [{"title": "T", "description": "D", "code": "x=1"}]}'
        ok, data = self.parser.parse_enhance(self._ai(raw))
        assert not ok
        assert data.variants[0].code == "x=1"

    def test_field_alias_variant_singular(self):
        raw = json.dumps({"already_optimal": False, "variant": [{"title": "T", "description": "D", "code": "x=1"}]})
        ok, data = self.parser.parse_enhance(self._ai(raw))
        assert not ok
        assert len(data.variants) == 1

    def test_field_alias_code_implementation(self):
        raw = json.dumps({"already_optimal": False, "variants": [{"title": "T", "description": "D", "implementation": "x=1"}]})
        ok, data = self.parser.parse_enhance(self._ai(raw))
        assert not ok
        assert data.variants[0].code == "x=1"

    def test_field_alias_already_optimal_variants(self):
        # "optimal" instead of "already_optimal"
        raw = json.dumps({"optimal": True, "reasons": ["clean code"]})
        ok, data = self.parser.parse_enhance(self._ai(raw))
        assert ok
        assert "clean code" in data.notes

    def test_single_variant_as_dict_not_list(self):
        raw = json.dumps({"already_optimal": False, "variants": {"title": "T", "description": "D", "code": "x=1"}})
        ok, data = self.parser.parse_enhance(self._ai(raw))
        assert not ok
        assert len(data.variants) == 1

    def test_missing_notes_in_already_optimal(self):
        raw = json.dumps({"already_optimal": True})
        ok, data = self.parser.parse_enhance(self._ai(raw))
        assert ok
        assert data.notes == []

    def test_missing_title_uses_default(self):
        raw = json.dumps({"already_optimal": False, "variants": [{"description": "D", "code": "x=1"}]})
        ok, data = self.parser.parse_enhance(self._ai(raw))
        assert not ok
        assert data.variants[0].title == "Untitled"

    def test_completely_invalid_json_raises_parse_error(self):
        with pytest.raises(ParseError):
            self.parser.parse_enhance(self._ai("this is not json at all"))

    def test_empty_response_raises_parse_error(self):
        with pytest.raises(ParseError):
            self.parser.parse_enhance(self._ai(""))

    def test_generate_skips_non_language_keys(self):
        raw = json.dumps({
            "python": {"title": "T", "description": "D", "code": "x=1"},
            "token_usage": {"prompt": 10, "completion": 20, "total": 30},
            "error": None,
        })
        data = self.parser.parse_generate(self._ai(raw))
        assert "python" in data.languages
        assert "token_usage" not in data.languages
        assert "error" not in data.languages

    def test_generate_field_aliases(self):
        raw = json.dumps({
            "python": {"name": "T", "summary": "D", "source": "x=1"},
        })
        data = self.parser.parse_generate(self._ai(raw))
        assert data.languages["python"].title == "T"
        assert data.languages["python"].code == "x=1"

    def test_generate_partial_languages_returned(self):
        # AI only returned python even though go was requested — should not fail
        raw = json.dumps({"python": {"title": "T", "description": "D", "code": "x=1"}})
        data = self.parser.parse_generate(self._ai(raw))
        assert "python" in data.languages


# --- AIProviderError ---

class TestAIProviderError:

    def test_retryable_flag(self):
        err = AIProviderError("server busy", status_code=503, retryable=True)
        assert err.retryable is True
        assert err.status_code == 503

    def test_non_retryable_flag(self):
        err = AIProviderError("bad request", status_code=400, retryable=False)
        assert err.retryable is False


# --- Gemini provider ---

class TestGeminiProvider:

    def test_build_payload_separates_system_prompt(self):
        from api.ai.gemini_provider import GeminiProvider
        provider = GeminiProvider(api_key="test")
        messages = [
            {"role": "system", "content": "You are an expert."},
            {"role": "user", "content": "Enhance this code."},
        ]
        payload = provider._build_payload(messages)
        assert "systemInstruction" in payload
        assert payload["systemInstruction"]["parts"][0]["text"] == "You are an expert."
        assert payload["contents"][0]["role"] == "user"
        assert payload["contents"][0]["parts"][0]["text"] == "Enhance this code."

    def test_is_available_with_key(self):
        from api.ai.gemini_provider import GeminiProvider
        assert GeminiProvider(api_key="test-key").is_available() is True

    def test_is_not_available_without_key(self):
        from api.ai.gemini_provider import GeminiProvider
        assert GeminiProvider(api_key="").is_available() is False

    def test_falls_back_to_15_on_503(self):
        async def run():
            from api.ai.gemini_provider import GeminiProvider
            import httpx

            call_count = 0
            models_called = []

            async def mock_post(url, **kwargs):
                nonlocal call_count
                call_count += 1
                models_called.append(url)
                req = httpx.Request("POST", url)
                if "gemini-2.5-flash" in url:
                    return httpx.Response(503, text="Overloaded", request=req)
                # fallback model succeeds
                body_text = json.dumps({"already_optimal": False, "variants": [{"title": "T", "description": "D", "code": "x=1"}]})
                body = {
                    "candidates": [{"content": {"parts": [{"text": body_text}]}}],
                    "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 20, "totalTokenCount": 30},
                }
                return httpx.Response(200, json=body, request=req)

            provider = GeminiProvider(api_key="test-key", max_retries=3, retry_base_delay=0.01)
            with patch("httpx.AsyncClient.post", new=AsyncMock(side_effect=mock_post)):
                response = await provider.complete([{"role": "user", "content": "test"}], timeout=5)
                assert any("gemini-flash-latest" in m for m in models_called)
                assert "already_optimal" in response.content

        asyncio.run(run())


# --- EnhancerService error handling ---

class TestEnhancerServiceErrorHandling:

    def _make_service(self, provider, tmp_path):
        return EnhancerService(
            ai_provider=provider,
            cache_service=DiskCacheService(path=tmp_path, ttl_hours=1, size_limit_mb=10),
            response_parser=ResponseParser(),
        )

    def test_ai_provider_error_returns_clean_response(self):
        async def run():
            with tempfile.TemporaryDirectory() as tmp:
                from api.ai.base import AIProvider

                class FailingProvider(AIProvider):
                    def is_available(self): return True
                    async def complete(self, messages, timeout):
                        raise AIProviderError("Service down", status_code=503, retryable=True)

                service = self._make_service(FailingProvider(), tmp)
                req = EnhanceRequest(code="def foo(): pass", language="python", variants=1)
                resp = await service.enhance(req)
                assert resp.success is False
                assert "AI service error" in resp.error

        asyncio.run(run())

    def test_parse_error_returns_clean_response(self):
        async def run():
            with tempfile.TemporaryDirectory() as tmp:
                from api.ai.base import AIProvider

                class GarbageProvider(AIProvider):
                    def is_available(self): return True
                    async def complete(self, messages, timeout):
                        return AIResponse("not json at all %%%", 0, 0, 0)

                service = self._make_service(GarbageProvider(), tmp)
                req = EnhanceRequest(code="def foo(): pass", language="python", variants=1)
                resp = await service.enhance(req)
                assert resp.success is False
                assert resp.error is not None

        asyncio.run(run())

    def test_unreliable_provider_handles_all_modes(self):
        """Cycle through all MockAIProviderUnreliable modes — none should crash the service."""
        async def run():
            with tempfile.TemporaryDirectory() as tmp:
                provider = MockAIProviderUnreliable()
                service = self._make_service(provider, tmp)

                for i in range(8):
                    req = EnhanceRequest(
                        code=f"def unreliable_test_{i}(): pass",
                        language="python",
                        variants=1,
                    )
                    resp = await service.enhance(req)
                    # Every response must be a valid envelope — success or failure, never a crash
                    assert resp.success is True or resp.error is not None

        asyncio.run(run())


# --- DeepSeek retry logic (mocked HTTP) ---

class TestDeepSeekRetry:

    def test_retries_on_503_then_succeeds(self):
        async def run():
            from api.ai.deepseek_provider import DeepSeekProvider
            import httpx

            call_count = 0

            async def mock_post(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    # Build a proper response with a dummy request attached
                    req = httpx.Request("POST", "https://api.deepseek.com")
                    return httpx.Response(503, text="Service Unavailable", request=req)
                req = httpx.Request("POST", "https://api.deepseek.com")
                return httpx.Response(200, json={
                    "choices": [{"message": {"content": json.dumps({
                        "already_optimal": False,
                        "variants": [{"title": "T", "description": "D", "code": "x=1"}]
                    })}}],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
                }, request=req)

            provider = DeepSeekProvider(api_key="test-key", max_retries=3, retry_base_delay=0.01)

            with patch("httpx.AsyncClient.post", new=AsyncMock(side_effect=mock_post)):
                response = await provider.complete([{"role": "user", "content": "test"}], timeout=5)
                assert call_count == 3
                assert "already_optimal" in response.content

        asyncio.run(run())

    def test_raises_after_max_retries_exhausted(self):
        async def run():
            from api.ai.deepseek_provider import DeepSeekProvider
            import httpx

            async def always_503(*args, **kwargs):
                req = httpx.Request("POST", "https://api.deepseek.com")
                return httpx.Response(503, text="Always down", request=req)

            provider = DeepSeekProvider(api_key="test-key", max_retries=3, retry_base_delay=0.01)

            with patch("httpx.AsyncClient.post", new=AsyncMock(side_effect=always_503)):
                with pytest.raises(AIProviderError) as exc_info:
                    await provider.complete([{"role": "user", "content": "test"}], timeout=5)
                assert exc_info.value.retryable is True
                assert exc_info.value.status_code == 503

        asyncio.run(run())

    def test_no_retry_on_401(self):
        async def run():
            from api.ai.deepseek_provider import DeepSeekProvider
            import httpx

            call_count = 0

            async def mock_401(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                req = httpx.Request("POST", "https://api.deepseek.com")
                return httpx.Response(401, text="Unauthorized", request=req)

            provider = DeepSeekProvider(api_key="bad-key", max_retries=3, retry_base_delay=0.01)

            with patch("httpx.AsyncClient.post", new=AsyncMock(side_effect=mock_401)):
                with pytest.raises(Exception):
                    await provider.complete([{"role": "user", "content": "test"}], timeout=5)
                assert call_count == 1

        asyncio.run(run())
