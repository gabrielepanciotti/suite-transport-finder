"""Contract tests for the finder-standard endpoints and response envelopes."""
from __future__ import annotations

import asyncio
import json
import tempfile
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from suite_backend_core import Base
from transportfinder_backend import models  # noqa: F401 -- register table metadata
from transportfinder_backend.app import app, create_application
from transportfinder_backend.db import get_db_session
from transportfinder_backend.vista import DEFAULT_VISTA, node_config_path


_DB_PATH = Path(tempfile.mkdtemp(prefix="transportfinder_standard_test_")) / "standard.db"
_engine = create_async_engine(f"sqlite+aiosqlite:///{_DB_PATH.as_posix()}")
_Session = async_sessionmaker(_engine, expire_on_commit=False)


async def _db_override() -> AsyncIterator[AsyncSession]:
    async with _Session() as session:
        yield session


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch):
    app.dependency_overrides[get_db_session] = _db_override

    async def setup() -> None:
        async with _engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.run_sync(Base.metadata.create_all)

    asyncio.run(setup())
    asyncio.run(_engine.dispose())
    yield TestClient(app)
    asyncio.run(_engine.dispose())


def _route(client: TestClient, origin: str, destination: str, provider: str = "Trenitalia") -> dict:
    response = client.post("/api/routes", json={
        "origin": origin, "destination": destination, "mode": "train", "provider": provider,
    })
    assert response.status_code == 201, response.text
    return response.json()


def test_saved_is_paginated_and_cursor_advances(client: TestClient):
    _route(client, "Roma", "Milano")
    _route(client, "Roma", "Bologna")
    _route(client, "Roma", "Torino")

    first = client.get("/api/saved", params={"limit": 2})
    assert first.status_code == 200, first.text
    first_body = first.json()
    assert first_body["total"] == 3
    assert len(first_body["items"]) == 2
    assert first_body["next_cursor"]
    assert [item["id"] for item in first_body["items"]] == [3, 2]

    last = client.get("/api/saved", params={"limit": 2, "cursor": first_body["next_cursor"]})
    assert last.status_code == 200, last.text
    assert [item["id"] for item in last.json()["items"]] == [1]
    assert last.json()["next_cursor"] is None


def test_saved_filters_and_validates_pagination(client: TestClient):
    _route(client, "Roma", "Milano", provider="Trenitalia")
    _route(client, "Roma", "Parigi", provider="FlixBus")
    assert client.get("/api/saved", params={"q": "flix"}).json()["total"] == 1
    assert client.get("/api/saved", params={"cursor": "not-a-cursor"}).status_code == 422
    assert client.get("/api/saved", params={"limit": 201}).status_code == 422


def test_soft_deleted_routes_are_not_readable(client: TestClient):
    created = _route(client, "Roma", "Milano")
    assert client.delete(f"/api/saved/{created['id']}").status_code == 204
    assert client.get(f"/api/routes/{created['id']}").status_code == 404
    assert client.get("/api/routes").json() == []
    assert client.get("/api/saved").json()["total"] == 0


def test_error_envelopes_keep_fastapi_detail(client: TestClient):
    validation = client.get("/api/saved", params={"limit": 201})
    assert validation.status_code == 422
    assert validation.json()["error"]["code"] == "validation_error"
    assert validation.json()["error"]["field"] == "limit"
    assert validation.json()["detail"]

    missing = client.get("/api/routes/999")
    assert missing.status_code == 404
    assert missing.json()["error"] == {
        "code": "not_found", "message": "Risorsa non trovata", "field": None,
    }
    assert missing.json()["detail"] == "Transport route not found"


def test_vista_uses_node_config_and_local_opt_in(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ALLOW_DEV_OWNER", "1")
    response = TestClient(create_application()).get("/api/vista")
    assert response.status_code == 200, response.text
    configured = json.loads(node_config_path().read_text(encoding="utf-8"))["vista"]
    assert configured == DEFAULT_VISTA
