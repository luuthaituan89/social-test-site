from collections import defaultdict, deque
from time import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from .cache import redis_client
from ..config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis fixed-window limiter with an in-process development fallback."""

    def __init__(self, app):
        super().__init__(app)
        self.local = defaultdict(deque)

    async def dispatch(self, request, call_next):
        if request.url.path in {"/health", "/metrics"}:
            return await call_next(request)
        identity = request.client.host if request.client else "unknown"
        bucket = int(time() // 60)
        key = f"rate:{identity}:{bucket}"
        try:
            client = redis_client()
            count = client.incr(key)
            if count == 1:
                client.expire(key, 70)
        except Exception:
            now = time()
            queue = self.local[identity]
            while queue and queue[0] < now - 60:
                queue.popleft()
            queue.append(now)
            count = len(queue)
        if count > settings.rate_limit_per_minute:
            return JSONResponse({"detail": "Too many requests. Please try again shortly."}, status_code=429)
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(settings.rate_limit_per_minute)
        return response
