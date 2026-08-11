"""
MarketTrust AI — API Dependency Injection.

Provides FastAPI dependencies for database sessions, storage, etc.
Automatically initializes DB if not already initialized.
"""

from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import connection


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session, auto-initializing if needed."""
    if connection.async_session_factory is None:
        await connection.init_db()

    if connection.async_session_factory is None:
        raise RuntimeError("Failed to initialize database session factory.")

    async with connection.async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
