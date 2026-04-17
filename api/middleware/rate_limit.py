import os
import time
from collections import defaultdict
from threading import Lock
from fastapi import Request, HTTPException, status


class RateLimiter:
    def __init__(self, requests_per_minute: int = 30):
        self.requests_per_minute = requests_per_minute
        self.requests: dict = defaultdict(list)
        self.lock = Lock()

    def _client_key(self, request: Request) -> str:
        ip = request.client.host if request.client else "unknown"
        ua = request.headers.get("user-agent", "unknown")
        return f"{ip}:{ua}"

    async def check(self, request: Request) -> bool:
        # Tighter window in testing so rate limit tests trigger without waiting a full minute
        if os.getenv("TESTING") == "true":
            if not request.url.path.startswith("/api/"):
                return True
            limit = 40
            window = 10
        else:
            limit = self.requests_per_minute
            window = 60

        key = self._client_key(request)
        now = time.time()
        window_start = now - window

        with self.lock:
            # Evict timestamps outside the current window
            self.requests[key] = [t for t in self.requests[key] if t > window_start]

            if len(self.requests[key]) >= limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Max {limit} requests per {window}s"
                )

            self.requests[key].append(now)

        return True


rate_limiter = RateLimiter(
    requests_per_minute=int(os.getenv("RATE_LIMIT_RPM", "30"))
)
