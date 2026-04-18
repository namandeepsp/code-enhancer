import asyncio
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

from api.ai.base import AIProvider
from api.ai.deepseek_provider import AIProviderError
from api.ai.prompts import PromptRouter
from api.cache import CacheService, make_cache_key
from api.logger import get_logger
from api.models import (
    EnhanceRequest, EnhanceResponse, EnhanceData, AlreadyOptimalData,
    CompleteRequest, CompleteResponse, CompleteData,
    GenerateRequest, GenerateResponse, GenerateData,
)
from api.services.response_parser import ResponseParser, ParseError

logger = get_logger("api.enhancer")


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

        # Return cached result immediately — no AI call needed
        cached = self._cache.get(cache_key)
        if cached:
            cached["cached"] = True
            return EnhanceResponse(**cached)

        messages = self._router.build_enhance(request)

        try:
            ai_response = await self._ai.complete(messages, timeout=self._timeout)
            already_optimal, data = self._parser.parse_enhance(ai_response)

            logger.info(
                "Enhance completed",
                extra={"task": "enhance", "language": request.language, "already_optimal": already_optimal, "cached": False},
            )
            response = EnhanceResponse(
                success=True,
                already_optimal=already_optimal,
                data=data,
                cached=False,
            )
            self._cache.set(cache_key, response.model_dump())
            return response

        except ParseError as e:
            logger.error("Parse error during enhance", extra={"task": "enhance", "language": request.language})
            return EnhanceResponse(success=False, error=str(e))
        except AIProviderError as e:
            logger.error(f"AI provider error during enhance: {e}", extra={"task": "enhance", "language": request.language, "status_code": e.status_code})
            return EnhanceResponse(success=False, error=f"AI service error: {str(e)}")
        except Exception as e:
            logger.exception("Unexpected error during enhance", extra={"task": "enhance", "language": request.language})
            return EnhanceResponse(success=False, error=f"Enhancement failed: {str(e)}")

    # --- Complete ---

    async def complete(self, request: CompleteRequest) -> CompleteResponse:
        # Context is included in the cache key so different file contexts produce different results
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

            logger.info(
                "Complete completed",
                extra={"task": "complete", "language": request.language, "already_optimal": already_optimal, "cached": False},
            )
            response = CompleteResponse(
                success=True,
                already_optimal=already_optimal,
                data=data,
                cached=False,
            )
            self._cache.set(cache_key, response.model_dump())
            return response

        except ParseError as e:
            logger.error("Parse error during complete", extra={"task": "complete", "language": request.language})
            return CompleteResponse(success=False, error=str(e))
        except AIProviderError as e:
            logger.error(f"AI provider error during complete: {e}", extra={"task": "complete", "language": request.language, "status_code": e.status_code})
            return CompleteResponse(success=False, error=f"AI service error: {str(e)}")
        except Exception as e:
            logger.exception("Unexpected error during complete", extra={"task": "complete", "language": request.language})
            return CompleteResponse(success=False, error=f"Completion failed: {str(e)}")

    # --- Generate ---

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        # Sort languages so ["python", "go"] and ["go", "python"] hit the same cache entry
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

            logger.info(
                "Generate completed",
                extra={"task": "generate", "language": ",".join(request.languages), "cached": False},
            )
            response = GenerateResponse(
                success=True,
                data=data,
                cached=False,
            )
            self._cache.set(cache_key, response.model_dump())
            return response

        except ParseError as e:
            logger.error("Parse error during generate", extra={"task": "generate"})
            return GenerateResponse(success=False, error=str(e))
        except AIProviderError as e:
            logger.error(f"AI provider error during generate: {e}", extra={"task": "generate", "status_code": e.status_code})
            return GenerateResponse(success=False, error=f"AI service error: {str(e)}")
        except Exception as e:
            logger.exception("Unexpected error during generate", extra={"task": "generate"})
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
