import asyncio
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

from api.ai.base import AIProvider
from api.ai.prompts import PromptRouter
from api.cache import CacheService, make_cache_key
from api.models import (
    EnhanceRequest, EnhanceResponse, EnhanceData, AlreadyOptimalData,
    CompleteRequest, CompleteResponse, CompleteData,
    GenerateRequest, GenerateResponse, GenerateData,
)
from api.services.response_parser import ResponseParser, ParseError


class EnhancerService:
    def __init__(
        self,
        ai_provider: AIProvider,
        cache_service: CacheService,
        response_parser: ResponseParser,
        ai_timeout: int = 30,
        max_workers: int = 4,
    ):
        self._ai = ai_provider
        self._cache = cache_service
        self._parser = response_parser
        self._router = PromptRouter()
        self._timeout = ai_timeout
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    # --- Enhance ---

    async def enhance(self, request: EnhanceRequest) -> EnhanceResponse:
        cache_key = make_cache_key(
            "enhance", request.language, request.technology or "",
            request.code, ""
        )

        cached = self._cache.get(cache_key)
        if cached:
            cached["cached"] = True
            return EnhanceResponse(**cached)

        messages = self._router.build_enhance(request)

        try:
            ai_response = await self._ai.complete(messages, timeout=self._timeout)
            already_optimal, data = self._parser.parse_enhance(ai_response)

            response = EnhanceResponse(
                success=True,
                already_optimal=already_optimal,
                data=data,
                cached=False,
            )
            self._cache.set(cache_key, response.model_dump())
            return response

        except ParseError as e:
            return EnhanceResponse(success=False, error=str(e))
        except Exception as e:
            return EnhanceResponse(success=False, error=f"Enhancement failed: {str(e)}")

    # --- Complete ---

    async def complete(self, request: CompleteRequest) -> CompleteResponse:
        cache_key = make_cache_key(
            "complete", request.language, request.technology or "",
            request.code, request.context or ""
        )

        cached = self._cache.get(cache_key)
        if cached:
            cached["cached"] = True
            return CompleteResponse(**cached)

        messages = self._router.build_complete(request)

        try:
            ai_response = await self._ai.complete(messages, timeout=self._timeout)
            already_optimal, data = self._parser.parse_complete(ai_response)

            response = CompleteResponse(
                success=True,
                already_optimal=already_optimal,
                data=data,
                cached=False,
            )
            self._cache.set(cache_key, response.model_dump())
            return response

        except ParseError as e:
            return CompleteResponse(success=False, error=str(e))
        except Exception as e:
            return CompleteResponse(success=False, error=f"Completion failed: {str(e)}")

    # --- Generate ---

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        cache_key = make_cache_key(
            "generate", ",".join(sorted(request.languages)), "",
            "", request.prompt
        )

        cached = self._cache.get(cache_key)
        if cached:
            cached["cached"] = True
            return GenerateResponse(**cached)

        messages = self._router.build_generate(request)

        try:
            ai_response = await self._ai.complete(messages, timeout=self._timeout)
            data = self._parser.parse_generate(ai_response)

            response = GenerateResponse(
                success=True,
                data=data,
                cached=False,
            )
            self._cache.set(cache_key, response.model_dump())
            return response

        except ParseError as e:
            return GenerateResponse(success=False, error=str(e))
        except Exception as e:
            return GenerateResponse(success=False, error=f"Generation failed: {str(e)}")

    # --- Supported languages ---

    def get_supported_languages(self) -> list[str]:
        from api.ai.prompts.technology_hints import TECHNOLOGY_HINTS
        return sorted(TECHNOLOGY_HINTS.keys())

    def __del__(self):
        if hasattr(self, "_executor"):
            try:
                self._executor.shutdown(wait=False)
            except Exception:
                pass
