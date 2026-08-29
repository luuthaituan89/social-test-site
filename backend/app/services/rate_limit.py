from collections import defaultdict, deque
from time import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from .cache import redis_client
from ..config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis fixed-window limiter with stricter buckets for sensitive routes."""

    def __init__(self, app):
        super().__init__(app)
        self.local = defaultdict(deque)

    @staticmethod
    def route_bucket(path: str, method: str) -> tuple[str, int]:
        if path.startswith(("/api/auth/login", "/api/auth/register", "/api/auth/forgot-password",
                            "/api/auth/reset-password", "/api/auth/2fa")):
            return "auth", settings.auth_rate_limit_per_minute
        if method in {"POST", "PUT"} and (path in {"/api/upload", "/api/chat/upload"}
                                           or path.endswith("/avatar") or path.endswith("/cover")
                                           or "/media" in path):
            return "upload", settings.upload_rate_limit_per_minute
        if path.startswith("/api/search"):
            return "search", settings.search_rate_limit_per_minute
        return "api", settings.rate_limit_per_minute

    async def dispatch(self, request, call_next):
        if request.url.path in {"/health", "/metrics"}:
            return await call_next(request)
        identity = request.client.host if request.client else "unknown"
        group, limit = self.route_bucket(request.url.path, request.method)
        bucket = int(time() // 60)
        key = f"rate:{group}:{identity}:{bucket}"
        try:
            client = redis_client()
            count = client.incr(key)
            if count == 1:
                client.expire(key, 70)
        except Exception:
            now = time()
            queue = self.local[f"{group}:{identity}"]
            while queue and queue[0] < now - 60:
                queue.popleft()
            queue.append(now)
            count = len(queue)
        if count > limit:
            return JSONResponse({"detail": "Too many requests. Please try again shortly."}, status_code=429,
                                headers={"Retry-After": "60", "X-RateLimit-Limit": str(limit),
                                         "X-RateLimit-Remaining": "0"})
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, limit - count))
        return response
