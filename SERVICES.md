# Code Enhancer — Service Layer Deep Dive

Every layer in this service is independently swappable. This document covers what each
layer does, its interface contract, its default implementation, and exactly how to swap it.

---

## Layer Map

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              REQUEST COMES IN                               │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                    ┌──────────────────▼──────────────────┐
                    │           MIDDLEWARE CHAIN           │
                    │                                      │
                    │  ┌────────────────────────────────┐  │
                    │  │  1. RequestSizeLimitMiddleware  │  │
                    │  └───────────────┬────────────────┘  │
                    │                  │                   │
                    │  ┌───────────────▼────────────────┐  │
                    │  │  2. AuthMiddleware              │  │
                    │  │     verify_api_key()            │  │
                    │  └───────────────┬────────────────┘  │
                    │                  │                   │
                    │  ┌───────────────▼────────────────┐  │
                    │  │  3. RateLimitMiddleware         │  │
                    │  │     RateLimiter.check()         │  │
                    │  └───────────────┬────────────────┘  │
                    └──────────────────┼──────────────────┘
                                       │
                    ┌──────────────────▼──────────────────┐
                    │              ROUTE LAYER             │
                    │   enhance.py  (thin — no logic)      │
                    │   Depends(get_enhancer_service)      │
                    └──────────────────┬──────────────────┘
                                       │
                    ┌──────────────────▼──────────────────┐
                    │          ENHANCER SERVICE            │
                    │   Orchestrates the full pipeline:    │
                    │                                      │
                    │   1. CacheService.get()              │
                    │      ├─ HIT  → return immediately    │
                    │      └─ MISS → continue              │
                    │                                      │
                    │   2. PromptRouter.build()            │
                    │      └─ selects + assembles prompt   │
                    │                                      │
                    │   3. AIProvider.complete()           │
                    │      └─ calls AI API                 │
                    │                                      │
                    │   4. ResponseParser.parse()          │
                    │      └─ cleans + structures output   │
                    │                                      │
                    │   5. CacheService.set()              │
                    │      └─ stores result with TTL       │
                    └──────────────────┬──────────────────┘
                                       │
                    ┌──────────────────▼──────────────────┐
                    │           RESPONSE TO CLIENT         │
                    └─────────────────────────────────────┘
```

---

## 1. Middleware Layer

### 1a. Request Size Limit
Registered as a global FastAPI middleware in `main.py`. Checks `content-length` header
before any route logic runs. Returns `413` if the body exceeds 200KB.

**Swap:** Change the `200 * 1024` constant or move the limit to an env var `MAX_REQUEST_SIZE_KB`.

---

### 1b. Auth — `verify_api_key`

**File:** `api/middleware/auth.py`

**Interface:** FastAPI dependency function — `async def verify_api_key(request: Request)`

**Phase 1 (current):**
```
X-API-Key header → compare to API_KEY env var → pass or raise 401
ENVIRONMENT=development → always pass (skip check)
```

**Phase 2 (SSO):**
```
Authorization: Bearer <jwt> → POST auth-service/validate → user_id or raise 401
```

**How to swap:** Replace the function body only. The signature stays identical so
`Depends(verify_api_key)` in every route requires zero changes.

---

### 1c. Rate Limiter — `RateLimiter`

**File:** `api/middleware/rate_limit.py`

**Interface:**
```python
class RateLimiter:
    async def check(self, request: Request) -> bool: ...
```

**Default implementation:** In-memory sliding window using `defaultdict(list)` + `threading.Lock`.
Keyed on `IP:UserAgent`. Limit: 30 req/min (configurable via `RATE_LIMIT_RPM` env var).

**How to swap to Redis-backed:**
1. Create `RedisRateLimiter(RateLimiter)` implementing the same `check()` method
2. In `dependencies.py`, change `get_rate_limiter()` to return `RedisRateLimiter()`
3. Nothing else changes

---

## 2. Route Layer

**File:** `api/routes/enhance.py`

Routes are intentionally thin — they do nothing except:
- Validate the request shape (Pydantic does this automatically)
- Call `enhancer_service.process(request)`
- Return the response

No business logic lives here. This keeps routes stable even when the service layer changes.

---

## 3. EnhancerService

**File:** `api/services/enhancer_service.py`

The orchestrator. Owns the full request pipeline. Injected with all dependencies at
construction time via `dependencies.py`.

```python
class EnhancerService:
    def __init__(
        self,
        ai_provider: AIProvider,
        cache_service: CacheService,
        response_parser: ResponseParser,
    ): ...

    async def enhance(self, request: EnhanceRequest) -> EnhanceResponse: ...
    async def complete(self, request: CompleteRequest) -> CompleteResponse: ...
    async def generate(self, request: GenerateRequest) -> GenerateResponse: ...
```

All three methods follow the same pipeline:
```
cache.get(key) → hit? return | miss? → prompt_router.build() → ai.complete() → parser.parse() → cache.set(key) → return
```

AI calls are submitted to a `ThreadPoolExecutor` (max 4 workers) to prevent blocking
the async event loop during long AI response times.

---

## 4. AI Provider Layer

**File:** `api/ai/base.py`

**Interface:**
```python
class AIProvider(ABC):
    @abstractmethod
    async def complete(self, messages: list[dict], timeout: int) -> AIResponse: ...

    @abstractmethod
    def is_available(self) -> bool: ...
```

**AIResponse shape:**
```python
class AIResponse:
    content: str          # raw text from the model
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
```

### Default: DeepSeekProvider

**File:** `api/ai/deepseek_provider.py`

- Uses `httpx.AsyncClient` for non-blocking HTTP
- Endpoint: `https://api.deepseek.com/v1/chat/completions`
- Model: `deepseek-chat` (default) or `deepseek-coder` (set via `DEEPSEEK_MODEL`)
- Auth: `Authorization: Bearer <DEEPSEEK_API_KEY>`
- OpenAI-compatible request/response format

### MockAIProvider (testing)

**File:** `api/ai/mock_provider.py`

Returns deterministic hardcoded responses. Activated when `TESTING=true`.
Zero real API calls in CI — no cost, no flakiness from network.

### How to swap to OpenAI / Claude:

1. Create `OpenAIProvider(AIProvider)` or `ClaudeProvider(AIProvider)` implementing `complete()`
2. In `dependencies.py`, change `get_ai_provider()` to return the new provider
3. Set the relevant API key env var
4. Nothing else changes — `EnhancerService` only knows about `AIProvider`

---

## 5. Prompt Router

**File:** `api/ai/prompts/` (one file per task type)

The prompt router selects and assembles the correct system + user prompt based on
`task_type` and optionally injects technology-specific instructions.

```python
class PromptRouter:
    def build(self, task: str, request: BaseRequest) -> list[dict]:
        # returns OpenAI-format messages list:
        # [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
```

**Prompt files:**

| File | Used for |
|---|---|
| `enhance_prompt.py` | `POST /api/enhance` |
| `complete_prompt.py` | `POST /api/complete` |
| `generate_prompt.py` | `POST /api/generate` |

Each file exports two things:
- `SYSTEM_PROMPT` — generic, task-level instructions (formatting, commenting standards, already_optimal signal)
- `TECHNOLOGY_HINTS` — dict mapping technology name → additional instructions injected into the user message

**How to tune prompts:** Edit the prompt file directly. Zero impact on any other layer.

**How to add a new technology:** Add an entry to `TECHNOLOGY_HINTS` in the relevant prompt file.

---

## 6. Cache Layer

**File:** `api/cache/cache_service.py`

**Interface:**
```python
class CacheService(ABC):
    @abstractmethod
    def get(self, key: str) -> dict | None: ...

    @abstractmethod
    def set(self, key: str, value: dict, ttl_seconds: int) -> None: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...

    @abstractmethod
    def clear(self) -> None: ...
```

**Cache key generation:**
```python
def make_key(task: str, language: str, technology: str, code: str, prompt: str) -> str:
    normalized = code.strip().lower()
    raw = f"{task}|{language}|{technology}|{normalized}|{prompt}"
    return hashlib.sha256(raw.encode()).hexdigest()
```

Normalizing the code before hashing means minor whitespace differences (trailing spaces,
blank lines) hit the same cache entry.

### Default: DiskCacheService

**File:** `api/cache/disk_cache_service.py`

- Backend: `diskcache.Cache`
- Location: `/app/.cache/` (created at Docker build time)
- TTL: 24 hours (configurable via `CACHE_TTL_HOURS`)
- Max size: 500MB (configurable via `CACHE_SIZE_LIMIT_MB`)
- Eviction: LRU when size limit is hit
- Persists across container restarts (Render persistent disk)

### How to swap to Redis:

1. Create `RedisCacheService(CacheService)` implementing `get()`, `set()`, `delete()`, `clear()`
2. In `dependencies.py`, change `get_cache_service()` to return `RedisCacheService()`
3. Add `REDIS_URL` env var
4. Nothing else changes

### How to swap to in-memory (for local dev without disk):

1. Create `InMemoryCacheService(CacheService)` using a plain `dict` + `TTLCache`
2. Swap in `dependencies.py`

---

## 7. Response Parser

**File:** `api/services/response_parser.py`

**Interface:**
```python
class ResponseParser(ABC):
    @abstractmethod
    def parse_enhance(self, raw: str) -> EnhanceData: ...

    @abstractmethod
    def parse_complete(self, raw: str) -> CompleteData: ...

    @abstractmethod
    def parse_generate(self, raw: str) -> GenerateData: ...
```

**Default implementation responsibilities:**
- Strip markdown code fences (` ```python ... ``` `)
- Parse structured JSON from AI response for multi-language generation
- Detect `ALREADY_OPTIMAL` signal in AI response → set `already_optimal: true`
- Validate parsed shape — raise `ParseError` if output is malformed

**How to swap:** If switching AI providers and the response format changes,
create a new `ResponseParser` subclass and swap it in `dependencies.py`.

---

## 8. Dependencies Wiring — `dependencies.py`

**File:** `api/dependencies.py`

The single file that wires everything together. Uses `@lru_cache(maxsize=1)` so each
singleton is created once and reused for the lifetime of the process.

```python
@lru_cache(maxsize=1)
def get_ai_provider() -> AIProvider:
    if os.getenv("TESTING") == "true":
        return MockAIProvider()
    return DeepSeekProvider(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        timeout=int(os.getenv("DEEPSEEK_TIMEOUT", "30")),
    )

@lru_cache(maxsize=1)
def get_cache_service() -> CacheService:
    return DiskCacheService(
        path="/app/.cache/",
        ttl_hours=int(os.getenv("CACHE_TTL_HOURS", "24")),
        size_limit_mb=int(os.getenv("CACHE_SIZE_LIMIT_MB", "500")),
    )

@lru_cache(maxsize=1)
def get_enhancer_service() -> EnhancerService:
    return EnhancerService(
        ai_provider=get_ai_provider(),
        cache_service=get_cache_service(),
        response_parser=ResponseParserImpl(),
    )
```

**To swap any layer:** Change the return value of the relevant `get_*` function.
Routes use `Depends(get_enhancer_service)` — they never change.

---

## Summary: What Changes When You Swap

| What you want to do | File(s) to change |
|---|---|
| Switch AI provider (DeepSeek → Claude) | `dependencies.py` — `get_ai_provider()` |
| Switch cache backend (disk → Redis) | `dependencies.py` — `get_cache_service()` |
| Switch auth (API key → SSO JWT) | `middleware/auth.py` — `verify_api_key()` body only |
| Switch rate limiter (memory → Redis) | `dependencies.py` — `get_rate_limiter()` |
| Tune prompts for a task | `ai/prompts/enhance_prompt.py` (or complete/generate) |
| Add a new technology hint | `TECHNOLOGY_HINTS` dict in the relevant prompt file |
| Change response parsing logic | `services/response_parser.py` — parser implementation |
| Add a new API endpoint | `routes/enhance.py` + new method in `EnhancerService` |
