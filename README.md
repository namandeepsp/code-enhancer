# Code Enhancer

AI-powered code enhancement, completion, and generation service.
Built with FastAPI, backed by DeepSeek API, with a disk-based caching layer.

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

> This section will be filled in as routes are implemented.

---

## Running Locally

> This section will be filled in once the service is scaffolded.

---

## Testing

> This section will be filled in once the test suite is in place.
> Will cover: running unit tests, integration tests, what MockAIProvider does, and test scripts.

---

## CI/CD Pipeline

> This section will be filled in once GitHub Actions and Render config are added.
> Will cover: pipeline trigger conditions, steps, how MockAIProvider is used in CI,
> and how Render deploys on merge to main.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `ENVIRONMENT` | `development` | `development` skips API key auth |
| `TESTING` | `false` | `true` activates MockAIProvider (no real API calls) |
| `DEEPSEEK_API_KEY` | — | Required in production |
| `DEEPSEEK_MODEL` | `deepseek-chat` | Model to use |
| `DEEPSEEK_TIMEOUT` | `30` | AI request timeout in seconds |
| `API_KEY` | — | Service API key for production auth |
| `CACHE_TTL_HOURS` | `24` | Cache entry lifetime |
| `CACHE_SIZE_LIMIT_MB` | `500` | Max disk cache size |
| `RATE_LIMIT_RPM` | `30` | Requests per minute per client |
| `MAX_VARIANTS` | `3` | Maximum variants a client can request per call |

---

## Tech Stack

| Layer | Choice |
|---|---|
| Framework | FastAPI (Python 3.11) |
| AI Client | httpx async — DeepSeek API (`deepseek-chat` / `deepseek-coder`) |
| Cache | diskcache (disk-persisted, TTL + LRU) |
| Validation | Pydantic v2 |
| Testing | pytest + pytest-asyncio |
| Container | Docker |
| CI | GitHub Actions |
| Hosting | Render.com (free tier) |
