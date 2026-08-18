import logging
import sys
import time
import uuid

import sentry_sdk
import structlog
from starlette.middleware.base import BaseHTTPMiddleware

from ..config import settings


def configure_observability(app) -> None:
    logging.basicConfig(stream=sys.stdout, level=getattr(logging, settings.log_level.upper(), logging.INFO), format="%(message)s")
    structlog.configure(processors=[structlog.contextvars.merge_contextvars, structlog.processors.TimeStamper(fmt="iso"), structlog.processors.add_log_level, structlog.processors.JSONRenderer()])
    if settings.sentry_dsn:
        sentry_sdk.init(dsn=settings.sentry_dsn, environment=settings.environment, traces_sample_rate=0.1)
    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        started = time.perf_counter()
        structlog.contextvars.bind_contextvars(request_id=request_id, method=request.method, path=request.url.path)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            structlog.get_logger("http").info("request_complete", status=response.status_code, duration_ms=round((time.perf_counter()-started)*1000, 2))
            return response
        finally:
            structlog.contextvars.clear_contextvars()
