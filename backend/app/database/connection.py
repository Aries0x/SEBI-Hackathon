"""
MarketTrust AI — Database Connection with Automatic Fallback.

Provides the async SQLAlchemy engine, session factory, auto-table creation,
and lifecycle helpers.
"""

from __future__ import annotations

import logging
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings
from app.database.models import Base

logger = logging.getLogger(__name__)

# ── Engine & Session Factory ────────────────────────────────

engine: AsyncEngine | None = None
async_session_factory: async_sessionmaker[AsyncSession] | None = None


async def init_db() -> None:
    """Create the async engine, session factory, and ensure tables exist."""
    global engine, async_session_factory

    db_url = settings.database_url
    sqlite_url = "sqlite+aiosqlite:///./markettrust_local.db"

    connected = False
    if "postgresql" in db_url:
        try:
            temp_engine = create_async_engine(
                db_url,
                echo=settings.app_debug,
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=20,
            )
            async with temp_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            engine = temp_engine
            async_session_factory = async_sessionmaker(
                engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
            connected = True
            logger.info("Connected to PostgreSQL database.")
        except Exception as e:
            logger.warning(
                f"PostgreSQL connection failed ({e}). Switching to local SQLite database."
            )

    if not connected:
        engine = create_async_engine(
            sqlite_url,
            echo=settings.app_debug,
        )
        async_session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        from sqlalchemy import text
        async with engine.begin() as conn:
            await conn.execute(text("PRAGMA journal_mode=WAL;"))
            await conn.execute(text("PRAGMA synchronous=NORMAL;"))
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Local SQLite database initialized with WAL mode: markettrust_local.db")


async def close_db() -> None:
    """Dispose the engine on shutdown."""
    global engine
    if engine is not None:
        await engine.dispose()
        engine = None


async def get_session() -> AsyncSession:
    """Yield a database session for dependency injection."""
    if async_session_factory is None:
        raise RuntimeError("Database not initialized.")
    async with async_session_factory() as session:
        yield session


def get_sync_session():
    """Create a synchronous DB session with automatic fallback to local SQLite."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.config import settings

    db_url = settings.database_url
    if "postgresql" in db_url:
        try:
            sync_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
            engine = create_engine(sync_url, connect_args={"connect_timeout": 5})
            # Test connection
            with engine.connect() as conn:
                pass
            return sessionmaker(bind=engine)()
        except Exception:
            pass

    # Fallback to local SQLite
    sqlite_sync_url = "sqlite:///./markettrust_local.db"
    engine = create_engine(sqlite_sync_url)
    return sessionmaker(bind=engine)()

