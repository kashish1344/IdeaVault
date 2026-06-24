"""
IdeaVault — FastAPI application entry point.
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .api.v1.router import api_router
from .core.config import get_settings
from .core.database import Base, engine
from .models import User, Job  # noqa: F401 — registers models with Base.metadata

logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}',
)
logger = logging.getLogger("ideavault")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("starting up — env=%s", settings.app_env)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    logger.info("shutting down")
    await engine.dispose()


app = FastAPI(
    title="IdeaVault API",
    description="AI-powered image & video generation — multi-agent pipeline with custom DSA",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"] if not settings.is_production else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Middleware ────────────────────────────────────────────────────────────────

@app.middleware("http")
async def request_timing(request: Request, call_next) -> Response:
    start = time.perf_counter()
    response: Response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Response-Time-Ms"] = f"{duration_ms:.1f}"
    logger.info(
        "method=%s path=%s status=%d duration_ms=%.1f",
        request.method, request.url.path, response.status_code, duration_ms,
    )
    return response


# ── Error handlers ────────────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "internal server error"},
    )


# ── Routes ────────────────────────────────────────────────────────────────────

app.include_router(api_router)

# Serve locally generated media files
import os
_IMG_DIR = "/tmp/ideavault/images"
_VID_DIR = "/tmp/ideavault/videos"
os.makedirs(_IMG_DIR, exist_ok=True)
os.makedirs(_VID_DIR, exist_ok=True)
app.mount("/media/images", StaticFiles(directory=_IMG_DIR), name="images")
app.mount("/media/videos", StaticFiles(directory=_VID_DIR), name="videos")


@app.get("/health", tags=["infra"])
async def health() -> dict:
    return {"status": "ok", "version": "1.0.0", "env": settings.app_env}


@app.get("/", tags=["infra"])
async def root() -> dict:
    return {
        "name": "IdeaVault API",
        "docs": "/docs",
        "health": "/health",
    }
