"""Small in-process sliding-window rate limiter (per client IP).

For multi-instance deployments replace the store with Redis (see docs/deployment.md).
"""
import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from .config import get_settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)

    async def dispatch(self, request, call_next):
        settings = get_settings()
        if settings.environment == "test" or request.url.path.endswith("/health"):
            return await call_next(request)
        client = request.client.host if request.client else "unknown"
        is_auth = "/auth/login" in request.url.path or "/auth/register" in request.url.path or "/auth/forgot" in request.url.path
        bucket = "auth" if is_auth else "api"
        limit = settings.auth_rate_limit_per_minute if is_auth else settings.rate_limit_per_minute
        now = time.monotonic()
        q = self.hits[(client, bucket)]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= limit:
            return JSONResponse({"detail": "Too many requests. Please slow down."}, status_code=429, headers={"Retry-After": "60"})
        q.append(now)
        return await call_next(request)
