import os
from functools import lru_cache

from api.ai import AIProvider, MockAIProvider, DeepSeekProvider
from api.cache import CacheService, DiskCacheService
from api.services import EnhancerService, ResponseParser


@lru_cache(maxsize=1)
def get_ai_provider() -> AIProvider:
    if os.getenv("TESTING") == "true":
        return MockAIProvider()
    return DeepSeekProvider(
        api_key=os.getenv("DEEPSEEK_API_KEY", ""),
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        timeout=int(os.getenv("DEEPSEEK_TIMEOUT", "30")),
    )


@lru_cache(maxsize=1)
def get_cache_service() -> CacheService:
    return DiskCacheService(
        path=os.getenv("CACHE_PATH", "/app/.cache/"),
        ttl_hours=int(os.getenv("CACHE_TTL_HOURS", "24")),
        size_limit_mb=int(os.getenv("CACHE_SIZE_LIMIT_MB", "500")),
    )


@lru_cache(maxsize=1)
def get_enhancer_service() -> EnhancerService:
    return EnhancerService(
        ai_provider=get_ai_provider(),
        cache_service=get_cache_service(),
        response_parser=ResponseParser(),
        ai_timeout=int(os.getenv("DEEPSEEK_TIMEOUT", "30")),
    )
