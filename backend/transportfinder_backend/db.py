"""Async DB session wiring for the TransportFinder node's structured store.

Kept out of the vendor package (`suite_backend_core`, conform-managed): this
module glues the vendor's generic engine/session helpers to this node's
`Settings.database_url`. Importable with no `DATABASE_URL` configured (dev
without a DB) — the dependency raises 503 instead of failing at import time,
so `/health` and any DB-free routes stay unaffected.
"""
from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from suite_backend_core import get_session, make_engine, make_session_factory
from suite_backend_core.config import get_settings

_settings = get_settings()

_engine: AsyncEngine | None
_session_factory: async_sessionmaker[AsyncSession] | None

if _settings.database_url:
    _engine = make_engine(_settings.database_url)
    _session_factory = make_session_factory(_engine)
else:
    _engine = None
    _session_factory = None


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding an `AsyncSession`.

    Raises 503 when `DATABASE_URL` is not configured, e.g. dev without a DB.
    """
    if _session_factory is None:
        raise HTTPException(status_code=503, detail="Database not configured")

    async for session in get_session(_session_factory):
        yield session
