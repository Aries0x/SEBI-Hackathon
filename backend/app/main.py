"""
MarketTrust AI — FastAPI Application Factory.

Central entry point: creates the FastAPI app, configures CORS,
registers routers, and sets up lifespan events for DB and MinIO.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database.connection import init_db, close_db
from app.storage import init_storage
from app.chat.rag_indexer import ensure_rag_collection


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup / shutdown lifecycle hooks."""
    # ── Startup ─────────────────────────────────────────────
    await init_db()
    init_storage()
    ensure_rag_collection()
    yield
    # ── Shutdown ────────────────────────────────────────────
    await close_db()


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    app = FastAPI(
        title="MarketTrust AI",
        description=(
            "Verify whether a financial communication (video, image, email, "
            "website) can be trusted before an investor makes a decision."
        ),
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # ── CORS ────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ─────────────────────────────────────────────
    from app.api.investigations import router as investigations_router
    from app.api.chat import router as chat_router

    app.include_router(investigations_router, prefix="/api")
    app.include_router(chat_router, prefix="/api")

    # ── Health check ────────────────────────────────────────
    @app.get("/api/health", tags=["system"])
    async def health_check():
        return {"status": "healthy", "version": "0.1.0"}

    return app


app = create_app()
