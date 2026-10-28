"""Tests for POST /api/search — no network, stubbed providers.

Exercises only the part that is ours: request validation, the off-thread
orchestration, and the ranking serialization. Provider modules are swapped for
stubs, mirroring `test_cli_search.py`.
"""

from __future__ import annotations

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from transportfinder_backend import search
from transportfinder_backend.app import app
from transportfinder_backend.providers.base import Journey

client = TestClient(app)


def _journey(dep: str, arr: str, price: float, mode: str = "train", changes: int = 0) -> Journey:
    return Journey(
        provider="Stub",
        mode=mode,
        origin="Perugia",
        destination="Udine",
        departure=datetime.fromisoformat(dep),
        arrival=datetime.fromisoformat(arr),
        changes=changes,
        price=price,
        legs=["IC 580"],
    )


class _StubProvider:
    name = "Stub"

    def __init__(self, journeys=(), error: Exception | None = None):
        self._journeys = list(journeys)
        self._error = error

    def search(self, origin, destination, day, **kwargs):
        if self._error:
            raise self._error
        return self._journeys


@pytest.fixture(autouse=True)
def _stub_train_provider(monkeypatch):
    monkeypatch.setattr(
        search,
        "PROVIDERS",
        {"train": _StubProvider([_journey("2026-09-13T06:37", "2026-09-13T13:51", 55.75)])},
    )


def test_search_returns_ranked_journeys():
    resp = client.post(
        "/api/search",
        json={
            "origin": "Perugia",
            "destination": "Udine",
            "day": "2026-09-13",
            "modes": ["train"],
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["origin"] == "Perugia"
    assert body["destination"] == "Udine"
    assert body["date"] == "2026-09-13"
    assert body["errors"] == []
    assert len(body["journeys"]) == 1
    j = body["journeys"][0]
    assert j["mode"] == "train"
    assert j["price"] == 55.75
    assert j["duration_min"] == 434
    assert j["changes"] == 0
    assert j["deeplink"] is None


def test_search_rejects_unknown_mode():
    resp = client.post(
        "/api/search",
        json={"origin": "A", "destination": "B", "day": "2026-09-13", "modes": ["ship"]},
    )
    assert resp.status_code == 422


def test_search_rejects_empty_modes():
    resp = client.post(
        "/api/search",
        json={"origin": "A", "destination": "B", "day": "2026-09-13", "modes": []},
    )
    assert resp.status_code == 422


def test_search_reports_provider_errors_not_a_5xx(monkeypatch):
    class _Failing:
        name = "Broken"

        def search(self, *a, **kw):
            raise RuntimeError("502")

    monkeypatch.setattr(search, "PROVIDERS", {"train": _Failing()})
    resp = client.post(
        "/api/search",
        json={"origin": "A", "destination": "B", "day": "2026-09-13", "modes": ["train"]},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["journeys"] == []
    assert body["errors"] == ["Broken: 502"]
