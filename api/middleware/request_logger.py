import uuid
import time
import logging
from fastapi import Request

logger = logging.getLogger("api.request")


async def request_logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id

    start = time.time()

    logger.info(
        f"{request.method} {request.url.path}",
        extra={"request_id": request_id},
    )

    response = await call_next(request)

    duration_ms = round((time.time() - start) * 1000, 2)
    logger.info(
        f"{request.method} {request.url.path} → {response.status_code}",
        extra={
            "request_id": request_id,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )

    response.headers["X-Request-ID"] = request_id
    return response
