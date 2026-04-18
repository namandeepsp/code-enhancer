# Code Enhancer Service — Architecture

A production-ready AI-powered code enhancement, completion, and generation service
built on FastAPI, backed by DeepSeek API, with a disk-based caching layer.

---

## What This Service Does

| Feature | Description |
|---|---|
| **Code Enhancement** | Analyzes submitted code and returns an improved version, or confirms the code is already optimal |
| **Smart Completion** | Accepts incomplete code (e.g. empty function stubs) with full file context and returns the best complete implementation |
| **Code Variants** | Returns multiple implementation approaches so the user can choose |
| **Code Generation** | Accepts a natural language prompt and returns generated code in multiple languages, each with a title, description, and the code itself |
| **Always Formatted** | Every code output is properly formatted and commented to industry standards |
| **Technology-Aware** | Accepts a `technology` field (e.g. `fastapi`, `react`, `spring-boot`) and follows that ecosystem's conventions |

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          API GATEWAY LAYER                          │
│                                                                     │
│   POST /api/enhance        →  Enhance existing code                │
│   POST /api/complete       →  Complete partial/stub code            │
│   POST /api/generate       →  Generate code from text prompt        │
│   GET  /api/languages      →  List supported languages              │
│   GET  /health             →  Service health + AI connectivity      │
│   GET  /ping               →  Lightweight liveness probe            │
│   GET  /metrics            →  Memory + uptime stats                 │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         MIDDLEWARE CHAIN                            │
│                                                                     │
│   1. Request Size Limit  →  Max 200KB per request                  │
│   2. Auth Check          →  X-API-Key header (skip in dev)         │
│   3. Rate Limiter        →  30 req/min per client (IP + UA)        │
│                                                                     │
│   Order: Size → Auth → Rate Limit                                  │
│   (Auth before cache — prevents cache probing by unauth clients)   │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          CACHE LAYER                                │
│                                                                     │
│   Backend : diskcache (disk-persisted, TTL-based)                  │
│   TTL     : 24 hours                                               │
│   Key     : SHA-256 hash of (task_type + code + language +         │
│             technology + prompt)                                    │
│                                                                     │
│   Cache HIT  → return cached response immediately                  │
│   Cache MISS → continue to AI pipeline                             │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        PROMPT ROUTER                                │
│                                                                     │
│   Decides which prompt template to use based on task type          │
│                                                                     │
│   ┌─────────────┐  ┌──────────────┐  ┌──────────────────────────┐ │
│   │  ENHANCE    │  │   COMPLETE   │  │        GENERATE          │ │
│   │  template   │  │   template   │  │        template          │ │
│   └──────┬──────┘  └──────┬───────┘  └────────────┬─────────────┘ │
│          │                │                        │               │
│          └────────────────┴────────────────────────┘               │
│                           │                                        │
│                           ▼                                        │
│              Assembled system + user prompt                        │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         AI CLIENT LAYER                             │
│                                                                     │
│   Provider  : DeepSeek API  (deepseek-chat / deepseek-coder)       │
│   Transport : httpx async client                                   │
│   Endpoint  : POST https://api.deepseek.com/v1/chat/completions    │
│   Timeout   : 30s (configurable via DEEPSEEK_TIMEOUT env var)      │
│                                                                     │
│   Interface : AIProvider (abstract base)                           │
│   ┌──────────────────┐   ← swap provider without changing logic    │
│   │  DeepSeekProvider│                                             │
│   └──────────────────┘                                             │
│   Future: OpenAIProvider, ClaudeProvider (same interface)          │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      RESPONSE PARSER                                │
│                                                                     │
│   - Strip markdown code fences (``` python ... ```)                │
│   - Parse structured JSON from AI for multi-language generation    │
│   - Detect "no enhancement needed" signal from AI response         │
│   - Validate parsed output shape before returning                  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       CACHE WRITE + RESPOND                         │
│                                                                     │
│   - Store parsed result in diskcache with 24h TTL                  │
│   - Return structured API response to client                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Request & Response Contracts

### POST /api/enhance

**Request**
```json
{
  "code": "def add(a, b):\n    return a",
  "language": "python",
  "technology": "fastapi",
  "context": "full file content here (optional)",
  "variants": 2
}
```

**Response — enhancement found**
```json
{
  "success": true,
  "task": "enhance",
  "already_optimal": false,
  "data": {
    "variants": [
      {
        "title": "Type-safe with validation",
        "description": "Adds type hints and input validation following PEP 484",
        "code": "def add(a: int | float, b: int | float) -> int | float:\n    \"\"\"Add two numbers.\"\"\"\n    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):\n        raise TypeError(\"Both arguments must be numeric\")\n    return a + b"
      },
      {
        "title": "Minimal idiomatic",
        "description": "Clean, minimal version following PEP 8",
        "code": "def add(a: float, b: float) -> float:\n    \"\"\"Return the sum of a and b.\"\"\"\n    return a + b"
      }
    ],
    "token_usage": { "prompt": 120, "completion": 210, "total": 330 }
  },
  "error": null,
  "cached": false
}
```

**Response — already optimal**
```json
{
  "success": true,
  "task": "enhance",
  "already_optimal": true,
  "data": {
    "message": "Your code already follows best practices for this technology.",
    "notes": ["Proper type hints present", "Docstring present", "PEP 8 compliant"]
  },
  "error": null,
  "cached": false
}
```

---

### POST /api/complete

**Request**
```json
{
  "code": "def calculate_discount(price, user_tier):\n    pass",
  "language": "python",
  "technology": "django",
  "context": "# Full file shown here so AI understands the codebase",
  "variants": 1
}
```

**Response**
```json
{
  "success": true,
  "task": "complete",
  "already_optimal": false,
  "data": {
    "variants": [
      {
        "title": "Tier-based discount calculator",
        "description": "Implements discount logic based on user tier with constants",
        "code": "DISCOUNT_RATES = {\n    \"bronze\": 0.05,\n    \"silver\": 0.10,\n    \"gold\": 0.20,\n}\n\ndef calculate_discount(price: float, user_tier: str) -> float:\n    \"\"\"\n    Calculate discounted price based on user membership tier.\n\n    Args:\n        price: Original price in base currency.\n        user_tier: Membership tier (bronze, silver, gold).\n\n    Returns:\n        Discounted price. Returns original price if tier is unrecognized.\n    \"\"\"\n    rate = DISCOUNT_RATES.get(user_tier.lower(), 0.0)\n    return round(price * (1 - rate), 2)"
      }
    ],
    "token_usage": { "prompt": 180, "completion": 290, "total": 470 }
  },
  "error": null,
  "cached": true
}
```

---

### POST /api/generate

**Request**
```json
{
  "prompt": "Create a JWT authentication middleware",
  "languages": ["python", "javascript", "go"],
  "technology_per_language": {
    "python": "fastapi",
    "javascript": "express",
    "go": "gin"
  },
  "variants": 1
}
```

**Response**
```json
{
  "success": true,
  "task": "generate",
  "already_optimal": false,
  "data": {
    "python": {
      "title": "FastAPI JWT Auth Middleware",
      "description": "Dependency-injection based JWT verification for FastAPI routes",
      "code": "from fastapi import Depends, HTTPException, status\nfrom fastapi.security import HTTPBearer\nimport jwt\n\n# ... full generated code ..."
    },
    "javascript": {
      "title": "Express JWT Middleware",
      "description": "Express middleware function for JWT token verification",
      "code": "const jwt = require('jsonwebtoken');\n\n// ... full generated code ..."
    },
    "go": {
      "title": "Gin JWT Auth Middleware",
      "description": "Gin middleware for JWT validation using golang-jwt",
      "code": "package middleware\n\nimport (\n    \"github.com/gin-gonic/gin\"\n    // ...\n)\n\n// ... full generated code ..."
    },
    "token_usage": { "prompt": 250, "completion": 890, "total": 1140 }
  },
  "error": null,
  "cached": false
}
```

---

## Project Structure

```
code-enhancer/
├── api/
│   ├── __init__.py
│   ├── main.py                        # FastAPI app, middleware, global handlers
│   ├── dependencies.py                # lru_cache singletons (AI client, cache, service)
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── requests.py                # EnhanceRequest, CompleteRequest, GenerateRequest
│   │   └── responses.py               # ApiResponse, EnhanceResponse, GenerateResponse, etc.
│   │
│   ├── routes/
│   │   ├── __init__.py
│   │   └── enhance.py                 # /enhance, /complete, /generate, /languages endpoints
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── enhancer_service.py        # Orchestrates: cache check → prompt → AI → parse → cache write
│   │   └── response_parser.py         # Strips fences, parses JSON, detects already_optimal
│   │
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── base.py                    # AIProvider abstract base class
│   │   ├── deepseek_provider.py       # DeepSeek API implementation (httpx async)
│   │   └── prompts/
│   │       ├── __init__.py
│   │       ├── enhance_prompt.py      # System + user prompt templates for enhancement
│   │       ├── complete_prompt.py     # Prompt templates for code completion
│   │       └── generate_prompt.py    # Prompt templates for code generation
│   │
│   ├── cache/
│   │   ├── __init__.py
│   │   └── cache_service.py           # diskcache wrapper with TTL, key hashing
│   │
│   └── middleware/
│       ├── __init__.py
│       ├── auth.py                    # Phase 1: X-API-Key check — Phase 2: SSO token validation
│       └── rate_limit.py              # In-memory rate limiter (same pattern as code-formatter)
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                    # TestClient, env setup, fixtures, mock AI provider
│   ├── test_enhance.py                # Enhancement + already_optimal + variants tests
│   ├── test_complete.py               # Completion with context tests
│   ├── test_generate.py               # Multi-language generation tests
│   ├── test_cache.py                  # Cache hit/miss, TTL, key collision tests
│   ├── test_health.py                 # /ping, /health, /metrics
│   ├── test_rate_limit.py             # 429 enforcement
│   └── test_stability.py             # Concurrent requests, bad input, recovery
│
├── .github/
│   └── workflows/
│       └── test.yml                   # CI: build Docker → run container → integration tests
│
├── .env.local                         # DEEPSEEK_API_KEY, ENVIRONMENT=development, etc.
├── .env.prod                          # Production env vars (never committed)
├── .gitignore
├── dockerfile
├── docker-compose.yml                 # Production compose
├── docker-compose.override.yml        # Dev compose (hot reload, mounts)
├── render.yaml                        # Render.com deployment config
├── requirements.txt
├── pytest.ini
├── ARCHITECTURE.md                    # This file
└── LICENSE
```

---

## Authentication — Phased Plan

### Phase 1 — Current (API Key, same as code-formatter)

A single `verify_api_key` FastAPI dependency checks the `X-API-Key` request header
against the `API_KEY` environment variable. In `development` mode the check is skipped entirely.

```
Request → X-API-Key header → match against API_KEY env var → pass or 401
```

This lives in one function in `api/middleware/auth.py` — intentionally minimal.

### Phase 2 — Future (Centralized SSO Auth Service)

Once the standalone auth service is built, the only change needed in code-enhancer
(and code-formatter, dev-snippets, or any other service) is replacing the body of
`verify_api_key`. Everything else — routes, middleware chain, service layer — stays untouched.

```
Request → Bearer JWT → auth service /validate → user_id returned → pass or 401
```

The auth service will be a separate project with:
- Its own FastAPI app
- Its own PostgreSQL database (authorized user records)
- JWT issuance on login, JWT validation on every downstream request
- Single sign-on across all services: dev-snippets, code-formatter, code-enhancer, and any future service

```python
# Phase 1 — env var check (now)
async def verify_api_key(request: Request):
    # checks X-API-Key against os.getenv("API_KEY")

# Phase 2 — SSO token validation (future, identical function signature)
async def verify_api_key(request: Request):
    # validates Bearer JWT against auth service /validate endpoint
    # returns user_id on success, raises 401 on failure
```

Because the function signature stays identical, `Depends(verify_api_key)` in every
route requires zero changes during the Phase 1 → Phase 2 migration.

---

## Prompt Strategy

Two categories of prompts are maintained:

### Generic Smart Prompts
Applied to all tasks regardless of technology. Focus on:
- Correctness and completeness
- Proper naming conventions
- Inline comments on non-obvious logic
- Docstrings / JSDoc / GoDoc as appropriate
- Removal of dead code

### Technology-Specific Goal Prompts
Injected when `technology` is provided. Examples:

| Technology | Additional Instructions Injected |
|---|---|
| `fastapi` | Use Pydantic models, dependency injection, proper status codes |
| `django` | Follow Django ORM patterns, use class-based views where appropriate |
| `react` | Functional components only, proper hook usage, no prop drilling |
| `express` | Async/await, proper error middleware, no callback hell |
| `spring-boot` | Use `@Service`/`@Repository` separation, constructor injection |
| `gin` | Idiomatic Go error handling, context propagation |

---

## Caching Strategy

```
Cache Key = SHA-256(task_type + "|" + language + "|" + technology + "|" + normalized_code + "|" + prompt)

normalized_code = code.strip().lower()   ← minor whitespace differences hit same cache entry
```

| Property | Value |
|---|---|
| Backend | `diskcache` (disk-persisted, survives container restarts on Render) |
| TTL | 24 hours |
| Max size | 500MB (configurable via `CACHE_SIZE_LIMIT_MB` env var) |
| Eviction | LRU when size limit is hit |
| Cache location | `/app/.cache/` (mounted as Docker volume on Render) |

---

## AI Provider Abstraction

```
AIProvider (abstract)
    └── DeepSeekProvider          ← default
    └── OpenAIProvider            ← future drop-in
    └── ClaudeProvider            ← future drop-in
    └── MockAIProvider            ← used in all tests (no real API calls in CI)
```

The provider is injected into `EnhancerService` via `dependencies.py` using `lru_cache`,
identical to how `FormatterService` is wired in code-formatter.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `ENVIRONMENT` | `development` | `development` skips API key auth |
| `TESTING` | `false` | `true` uses MockAIProvider in tests |
| `DEEPSEEK_API_KEY` | — | Required in production |
| `DEEPSEEK_MODEL` | `deepseek-chat` | Model to use |
| `DEEPSEEK_TIMEOUT` | `30` | AI request timeout in seconds |
| `API_KEY` | — | Service API key for production auth |
| `CACHE_TTL_HOURS` | `24` | Cache entry lifetime |
| `CACHE_SIZE_LIMIT_MB` | `500` | Max disk cache size |
| `RATE_LIMIT_RPM` | `30` | Requests per minute per client |
| `MAX_VARIANTS` | `3` | Maximum variants a client can request |

---

## Docker Setup

### dockerfile
- Base: `python:3.11-slim`
- Non-root user (`appuser`)
- `HEALTHCHECK` on `/ping`
- Cache directory created at build time: `/app/.cache/`

### docker-compose.yml (production)
- `mem_limit: 512m` (Render free tier limit)
- `restart: unless-stopped`
- Cache volume mounted for persistence

### docker-compose.override.yml (development)
- Hot reload via `--reload`
- `api/` and `tests/` mounted as volumes
- `TESTING=true` → MockAIProvider active (no API costs during dev)

---

## CI/CD Pipeline

### GitHub Actions (`test.yml`)
Triggers on: push to `main`/`develop`, PR to `main`

```
1. Checkout code
2. Build Docker image
3. Run container (TESTING=true, ENVIRONMENT=development)
4. Poll /ping until ready (max 10 retries)
5. Run integration tests (pytest, no real AI calls — MockAIProvider)
6. On failure: dump docker logs
7. Check memory usage: docker stats
```

### Render.com (CD)
- `render.yaml` defines service as `env: docker`
- Render builds the Dockerfile on every push to `main`
- `healthCheckPath: /ping` — deploy only goes live if ping passes
- Persistent disk mounted at `/app/.cache/` for diskcache

---

## Why DeepSeek API (not a custom model)

| Option | Verdict |
|---|---|
| Custom fine-tuned model | ❌ Needs GPU hosting (~$100+/mo), thousands of training examples, ongoing maintenance |
| Self-hosted OSS model (Llama, Mistral) | ❌ 7B model needs 6-8GB RAM — no free tier supports this |
| OpenAI GPT-4o | ✅ Excellent quality, but expensive (~$15/1M output tokens) |
| Anthropic Claude 3.5 Sonnet | ✅ Best for reasoning, but expensive (~$15/1M output tokens) |
| **DeepSeek API (deepseek-coder)** | ✅ **Recommended** — trained specifically on code, ~10-20x cheaper than GPT-4o, OpenAI-compatible format |

DeepSeek is chosen as the default. Because the AI client is behind an abstract `AIProvider`
interface, switching to Claude or GPT-4o is a one-line config change.

---

## Swappable Layers

Every layer is designed to be independently replaceable without touching any other layer.
All wiring happens in a single file — `api/dependencies.py` — using `lru_cache` singletons.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        dependencies.py                             │
│                  (single wiring point for all layers)              │
│                                                                     │
│   get_ai_provider()      → returns AIProvider instance             │
│   get_cache_service()    → returns CacheService instance           │
│   get_enhancer_service() → returns EnhancerService instance        │
└─────────────────────────────────────────────────────────────────────┘
```

| Layer | Interface / Base | Default | How to Swap |
|---|---|---|---|
| AI Provider | `AIProvider` (abstract) | `DeepSeekProvider` | Change `get_ai_provider()` in `dependencies.py` |
| Cache Backend | `CacheService` (abstract) | `DiskCacheService` | Change `get_cache_service()` in `dependencies.py` |
| Auth | `verify_api_key` function | API key vs env var | Replace function body in `middleware/auth.py` |
| Rate Limiter | `RateLimiter` class | In-memory | Subclass with Redis backend, swap in `dependencies.py` |
| Prompt Templates | One file per task in `ai/prompts/` | DeepSeek-tuned | Edit prompt file — zero impact on service logic |
| Response Parser | `ResponseParser` class, injected | JSON + fence stripper | Swap class in `dependencies.py` |

---

## Scalability Notes

- The service is stateless except for the disk cache — horizontal scaling is possible by pointing multiple instances at a shared NFS/EFS volume
- Rate limiting is in-memory per instance — acceptable for single-instance free tier; upgrade to Redis-backed limiter when scaling horizontally
- `ThreadPoolExecutor` in the service layer (same pattern as code-formatter) prevents AI call timeouts from blocking the event loop
- `MAX_VARIANTS` env var caps the number of AI completions per request to prevent runaway token costs
