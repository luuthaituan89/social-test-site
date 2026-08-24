from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .routes import (auth, users, friends, posts, chat, upload, notifications, albums,
                     giphy, activity, groups, data_lifecycle, products, search)
from .services.cache import healthy as redis_healthy
from .services.observability import RequestContextMiddleware, configure_observability
from .services.rate_limit import RateLimitMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Schema changes are performed by `alembic upgrade head` before Uvicorn.
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="SocialN API",
    version="2.0.0",
    description="Modular REST + WebSocket API for the SocialN social network",
    lifespan=lifespan,
)

origins = [value.strip() for value in settings.cors_origins.split(",") if value.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestContextMiddleware)

app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

for route_module in (auth, users, friends, posts, chat, upload, notifications, albums,
                     giphy, activity, groups, data_lifecycle, products, search):
    app.include_router(route_module.router)

configure_observability(app)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "SocialN API",
        "version": app.version,
        "dependencies": {"database": "configured", "redis": "ok" if redis_healthy() else "degraded"},
    }
