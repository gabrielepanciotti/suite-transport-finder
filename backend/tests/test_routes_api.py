"""API-level tests for the TransportFinder domain store — transport routes.

Exercises the CRUD routes in `transportfinder_backend/routes.py` against a
real async SQLite DB, overriding the production `get_db_session` dependency.

Setup mirrors Travel's test_store_api.py: a temp-file SQLite DB (not
`:memory:`) so each anyio worker/event-loop request can reopen the same data,
with `engine.dispose()` between tests to clear loop-bound pooled connections.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from collections.abc import AsyncIterator
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from suite_backend_core import Base
from transportfinder_backend import models  # noqa: F401  (registers tables on Base.metadata)
from transportfinder_backend.app import app
from transportfinder_backend.db import get_db_session

# --- Test DB wiring -----------------------------------------------------------

_TMP_DIR = tempfile.mkdtemp(prefix="transportfinder_routes_test_")
_DB_PATH = Path(_TMP_DIR) / "routes_test.db"
_engine = create_async_engine(f"sqlite+aiosqlite:///{_DB_PATH.as_posix()}")
_TestSession = async_sessionmaker(_engine, expire_on_commit=False)


async def _override_get_db_session() -> AsyncIterator[AsyncSession]:
    async with _TestSession() as session:
        yield session


client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_db():
    app.dependency_overrides[get_db_session] = _override_get_db_session

    async def _setup() -> None:
        async with _engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_setup())
    asyncio.run(_engine.dispose())
    yield
    asyncio.run(_engine.dispose())


# --- Helpers ------------------------------------------------------------------


def _make_route(
    origin: str = "Roma",
    destination: str = "Parigi",
    mode: str = "flight",
    **extra: object,
) -> dict:
    payload = {"origin": origin, "destination": destination, "mode": mode, **extra}
    resp = client.post("/api/routes", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


# --- Tests --------------------------------------------------------------------


def test_create_route_returns_full_payload():
    body = _make_route(provider="ITA Airways", duration_minutes=125, price=89.9)
    assert body["id"] > 0
    assert body["origin"] == "Roma"
    assert body["destination"] == "Parigi"
    assert body["mode"] == "flight"
    assert body["provider"] == "ITA Airways"
    assert body["duration_minutes"] == 125
    assert body["price"] == 89.9
    assert body["currency"] == "EUR"
    assert body["source"] == "assisted"
    assert body["created"] is not None
    assert body["updated"] is not None


def test_get_route():
    created = _make_route()
    resp = client.get(f"/api/routes/{created['id']}")
    assert resp.status_code == 200, resp.text
    assert resp.json()["id"] == created["id"]


def test_get_route_404():
    resp = client.get("/api/routes/99999")
    assert resp.status_code == 404


def test_list_routes():
    _make_route(origin="Roma", destination="Parigi", mode="flight")
    _make_route(origin="Roma", destination="Milano", mode="train")
    resp = client.get("/api/routes")
    assert resp.status_code == 200, resp.text
    assert len(resp.json()) == 2


def test_list_filter_from():
    _make_route(origin="Roma", destination="Parigi")
    _make_route(origin="Napoli", destination="Parigi")
    resp = client.get("/api/routes", params={"from": "Roma"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["origin"] == "Roma"


def test_list_filter_to():
    _make_route(origin="Roma", destination="Parigi")
    _make_route(origin="Roma", destination="Milano")
    resp = client.get("/api/routes", params={"to": "Milano"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["destination"] == "Milano"


def test_list_filter_mode():
    _make_route(mode="flight")
    _make_route(origin="Roma", destination="Milano", mode="train")
    resp = client.get("/api/routes", params={"mode": "train"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["mode"] == "train"


def test_patch_route():
    created = _make_route()
    resp = client.patch(f"/api/routes/{created['id']}", json={"price": 45.0})
    assert resp.status_code == 200, resp.text
    assert resp.json()["price"] == 45.0


def test_delete_route():
    created = _make_route()
    resp = client.delete(f"/api/routes/{created['id']}")
    assert resp.status_code == 204
    assert client.get(f"/api/routes/{created['id']}").status_code == 404
