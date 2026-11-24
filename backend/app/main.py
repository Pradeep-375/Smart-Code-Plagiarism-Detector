import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from .api import admin, analysis, assignments, auth, dashboard, notifications, reports, submissions, users
from .core.config import get_settings
from .core.rate_limit import RateLimitMiddleware
from .database import Base, SessionLocal, engine
from . import models  # noqa: F401  (registers tables)
from .seed import seed_base, seed_demo

log = logging.getLogger("scpds")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate_for_runtime()
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    if settings.database_url.startswith("sqlite"):
        Base.metadata.create_all(engine)  # convenience for local development; PostgreSQL uses Alembic
    with SessionLocal() as db:
        seed_base(db)
        if settings.seed_demo_data:
            seed_demo(db)
    yield


app = FastAPI(
    title=settings.app_name, version="1.0.0", lifespan=lifespan,
    docs_url=None if settings.is_production else "/docs", redoc_url=None, openapi_url=None if settings.is_production else "/openapi.json",
)

app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"], allow_headers=["Authorization", "Content-Type"],
    expose_headers=["Content-Disposition"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Cache-Control", "no-store")
    return response


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    log.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse({"detail": "Internal server error"}, status_code=500)  # never leak internals


PREFIX = "/api/v1"
for module in (auth, users, admin, assignments, submissions, analysis, reports, dashboard, notifications):
    app.include_router(module.router, prefix=PREFIX)


@app.get(f"{PREFIX}/health", tags=["system"])
def health():
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
    return {"status": "ok"}
