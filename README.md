# Code Enhancer

AI-powered code enhancement, completion, and generation service.
Built with FastAPI, backed by Gemini API, with a disk-based caching layer.

---

## What It Does

- **Enhance** — Submits existing code and gets back an improved version, or a confirmation that the code is already optimal
- **Complete** — Submits partial/stub code with full file context and gets back the best complete implementation
- **Generate** — Submits a natural language prompt and gets back generated code in one or more languages, each with a title and description
- **Variants** — Every task supports returning multiple implementation approaches for the user to choose from
- **Technology-aware** — Accepts a `technology` field and follows that ecosystem's conventions (FastAPI, Django, React, Express, Spring Boot, Gin, etc.)
- **Always formatted** — Every code output is properly formatted and commented to industry standards

---

## Architecture & Design Docs

| Document | Description |
|---|---|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | High-level architecture, request flow, all layer diagrams, environment variables, Docker and CI/CD setup |
| [SERVICES.md](./SERVICES.md) | Deep dive on every layer — interface contracts, default implementations, and exactly how to swap each layer |
| [PROMPTS.md](./PROMPTS.md) | Prompt strategy, template structure, technology hints, ALREADY_OPTIMAL contract, and tuning guidelines |

---

## API Routes

| Method | Route | Description |
|---|---|---|
| `POST` | `/api/enhance` | Enhance existing code or confirm it's already optimal |
| `POST` | `/api/complete` | Complete partial/stub code using file context |
| `POST` | `/api/generate` | Generate code from a natural language prompt |
| `GET` | `/api/languages` | List all supported technologies |
| `GET` | `/api/health` | Enhancer service health + AI provider status |
| `GET` | `/health` | Full service health including memory usage |
| `GET` | `/ping` | Lightweight liveness probe — returns `pong` |
| `GET` | `/metrics` | Memory, CPU, and uptime stats |

---

## Running Locally

### Prerequisites
- Python 3.11+
- Docker + Docker Compose
- Gemini API key from [aistudio.google.com](https://aistudio.google.com)

### Setup

```bash
# Clone and enter the project
cd code-enhancer

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and fill in your env vars
cp .env.local .env
# Edit .env — set GEMINI_API_KEY and API_KEY
```

### Run in development mode (MockAIProvider — no API key needed)

```bash
TESTING=true ENVIRONMENT=development CACHE_PATH=/tmp/code-enhancer-cache \
  uvicorn api.main:app --reload --port 8000
```

### Run in development mode with Docker (hot reload)

```bash
# Uses docker-compose.override.yml automatically — TESTING=true, hot reload on
docker-compose up --build
```

### Run in production mode locally (real Gemini API)

```bash
# Uses only docker-compose.yml — no override, real API calls
docker-compose -f docker-compose.yml --env-file .env.local up --build
```

### Build clean + run all tests (single command)

```bash
./build.sh
```

This script:
1. Clears all `__pycache__` and `.pyc` files
2. Clears the test disk cache
3. Builds the Docker image with `--no-cache`
4. Runs the full test suite

---

## Testing

Tests use `MockAIProvider` — zero real API calls, zero cost, runs fully offline.

### Run all tests

```bash
TESTING=true ENVIRONMENT=development CACHE_PATH=/tmp/test-cache-enhancer \
  .venv/bin/python -m pytest tests/ -v
```

### Run a specific test file

```bash
TESTING=true ENVIRONMENT=development CACHE_PATH=/tmp/test-cache-enhancer \
  .venv/bin/python -m pytest tests/test_enhance.py -v
```

### Run excluding slow tests

```bash
TESTING=true ENVIRONMENT=development CACHE_PATH=/tmp/test-cache-enhancer \
  .venv/bin/python -m pytest tests/ -v -m "not slow"
```

### Run only error handling tests

```bash
TESTING=true ENVIRONMENT=development CACHE_PATH=/tmp/test-cache-enhancer \
  .venv/bin/python -m pytest tests/test_error_handling.py -v
```

### Test suite breakdown

| File | What it covers |
|---|---|
| `test_enhance.py` | Enhancement flow, variants, cache hit, validation, response envelope |
| `test_complete.py` | Completion flow, context, cache hit, validation |
| `test_generate.py` | Multi-language generation, technology hints, cache hit, validation |
| `test_cache.py` | Cache miss→hit, key isolation per task/language/technology |
| `test_health.py` | `/ping`, `/health`, `/metrics`, `/api/languages`, `/api/health` |
| `test_rate_limit.py` | 429 enforcement, response shape, non-API routes exempt |
| `test_stability.py` | Bad inputs, large code, unicode, concurrent requests, memory stability |
| `test_error_handling.py` | Parser resilience, field aliases, retry logic, AI provider errors, Gemini fallback |

### What MockAIProvider does

`MockAIProvider` returns deterministic hardcoded responses based on the task type detected from the user message. It never makes HTTP calls. Activated automatically when `TESTING=true`.

`MockAIProviderUnreliable` cycles through 8 edge case response formats (markdown fences, field aliases, wrong structure, 503 errors) to test parser and service resilience.

---

## CI/CD Pipeline

### GitHub Actions

Triggers on: push to `main`/`develop`, PR to `main`

```
1. Checkout code
2. Build Docker image
3. Run container (TESTING=true, ENVIRONMENT=development)
4. Poll /ping until ready (max 15 retries)
5. Run integration tests via pytest
6. On failure — dump docker logs
7. Check memory usage via docker stats
```

No real API keys needed in CI — `MockAIProvider` handles all AI calls.

### Render.com

- Defined in `render.yaml` as `env: docker`
- Render builds the Dockerfile on every push to `main`
- `healthCheckPath: /ping` — deploy only goes live if `/ping` responds
- `GEMINI_API_KEY` and `API_KEY` set as secrets in Render dashboard (never committed)
- Persistent disk mounted at `/app/.cache/` for diskcache

---

## Docker Commands

```bash
# Dev mode (hot reload, MockAIProvider)
docker-compose up --build

# Production mode locally (real Gemini API)
docker-compose -f docker-compose.yml --env-file .env.local up --build

# Build clean image (no layer cache)
docker build --no-cache -t code-enhancer .

# Stop and remove containers
docker-compose down

# Stop and remove containers + volumes (clears persistent cache)
docker-compose down -v

# View logs
docker logs code-enhancer-app-1 -f

# Check memory usage
docker stats code-enhancer-app-1 --no-stream

# Run tests inside running container
docker exec -it code-enhancer-app-1 \
  python -m pytest tests/ -v
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `ENVIRONMENT` | `development` | `development` skips API key auth |
| `TESTING` | `false` | `true` activates MockAIProvider (no real API calls) |
| `AI_PROVIDER` | `gemini` | AI provider to use — `gemini` or `deepseek` |
| `GEMINI_API_KEY` | — | Required when `AI_PROVIDER=gemini` |
| `DEEPSEEK_API_KEY` | — | Required when `AI_PROVIDER=deepseek` |
| `DEEPSEEK_MODEL` | `deepseek-chat` | DeepSeek model to use |
| `AI_TIMEOUT` | `30` | AI request timeout in seconds |
| `API_KEY` | — | Service API key for production auth (`X-API-Key` header) |
| `CACHE_PATH` | `/app/.cache/` | Disk cache directory |
| `CACHE_TTL_HOURS` | `24` | Cache entry lifetime |
| `CACHE_SIZE_LIMIT_MB` | `500` | Max disk cache size |
| `RATE_LIMIT_RPM` | `30` | Requests per minute per client |
| `MAX_VARIANTS` | `3` | Maximum variants a client can request per call |
| `LOG_LEVEL` | `INFO` | Log level — `DEBUG` in development, `INFO` in production |

---

## Tech Stack

| Layer | Choice |
|---|---|
| Framework | FastAPI (Python 3.11) |
| AI Provider | Gemini API (`gemini-2.5-flash` / `gemini-flash-latest` fallback) |
| AI Client | httpx async |
| Cache | diskcache (disk-persisted, TTL + LRU) |
| Validation | Pydantic v2 |
| Testing | pytest + pytest-asyncio |
| Container | Docker |
| CI | GitHub Actions |
| Hosting | Render.com (free tier) |
