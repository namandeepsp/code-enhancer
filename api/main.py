import time
import psutil
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.exceptions import RequestValidationError
from fastapi import HTTPException

from api.logger import setup_logging, get_logger
from api.middleware import rate_limiter
from api.middleware.request_logger import request_logging_middleware
from api.routes import enhance

setup_logging()
logger = get_logger("api.main")

app = FastAPI(
    title="Code Enhancer API",
    description="AI-powered code enhancement, completion, and generation service",
    version="1.0.0",
)

app.start_time = time.time()

# --- Request logging + ID ---
app.middleware("http")(request_logging_middleware)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Request size limit (200KB) ---
@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > 200 * 1024:
        return JSONResponse(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content={"success": False, "error": "Request too large (max 200KB)"},
        )
    return await call_next(request)

# --- Rate limit ---
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    try:
        await rate_limiter.check(request)
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"success": False, "error": e.detail},
        )
    except Exception:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Rate limiter failure"},
        )
    return await call_next(request)

# --- Error handlers ---
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"success": False, "error": "Invalid request format", "details": exc.errors()},
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception on {request.method} {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"success": False, "error": "Internal server error"},
    )

# --- System endpoints ---
@app.get("/ping")
async def ping():
    return PlainTextResponse("pong")

@app.get("/health")
async def health():
    from api.dependencies import get_enhancer_service
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "memory_usage_mb": psutil.Process().memory_info().rss / 1024 / 1024,
        "ai": {},
    }
    try:
        service = get_enhancer_service()
        health_status["ai"]["available"] = service._ai.is_available()
        if not service._ai.is_available():
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["error"] = str(e)

    if health_status["memory_usage_mb"] > 400:
        health_status["status"] = "warning"
        health_status["warning"] = "High memory usage"

    status_code = 200 if health_status["status"] in ("healthy", "warning") else 503
    return JSONResponse(status_code=status_code, content=health_status)

@app.get("/metrics")
async def metrics():
    return {
        "memory_mb": psutil.Process().memory_info().rss / 1024 / 1024,
        "cpu_percent": psutil.Process().cpu_percent(),
        "uptime_seconds": time.time() - app.start_time,
    }

# --- Routers ---
app.include_router(enhance.router)
