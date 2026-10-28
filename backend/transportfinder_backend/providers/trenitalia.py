"""Trenitalia rail search via the public lefrecce.it BFF endpoints.

Two calls: ``/website/locations/search`` turns a station name into a numeric id, then
``/website/ticket/solutions`` returns priced itineraries. This is the same unauthenticated
JSON the lefrecce.it web app consumes, so it carries live availability and the cheapest
fare per solution — no scraping, no API key.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, time
from functools import lru_cache

import httpx

from .base import Journey

logger = logging.getLogger(__name__)

name = "Trenitalia"
BASE = "https://www.lefrecce.it/Channels.Website.BFF.WEB/website"
# lefrecce.it keeps its search state in memory and routes to a bare `#/search-results`,
# so no per-search deeplink exists: the best a result can offer is the booking homepage.
SHOP = "https://www.lefrecce.it/Channels.Website.WEB/"
_HEADERS = {"accept": "application/json", "user-agent": "Mozilla/5.0 (transportfinder)"}
TIMEOUT = httpx.Timeout(45.0)


@lru_cache(maxsize=128)
def resolve_location(name_fragment: str) -> tuple[int, str]:
    """Map a free-text station name to (id, canonical name), first match wins."""
    with httpx.Client(timeout=TIMEOUT, headers=_HEADERS) as client:
        resp = client.get(f"{BASE}/locations/search", params={"name": name_fragment, "limit": 5})
        resp.raise_for_status()
        hits = resp.json()
    if not hits:
        raise LookupError(f"Trenitalia: nessuna stazione per {name_fragment!r}")
    return hits[0]["id"], hits[0]["name"]


def search(
    origin: str,
    destination: str,
    day: date,
    *,
    from_time: time = time(5, 0),
    limit: int = 20,
) -> list[Journey]:
    dep_id, dep_name = resolve_location(origin)
    arr_id, arr_name = resolve_location(destination)
    payload = {
        "departureLocationId": dep_id,
        "arrivalLocationId": arr_id,
        "departureTime": f"{datetime.combine(day, from_time).isoformat(timespec='milliseconds')}",
        "adults": 1,
        "children": 0,
        "criteria": {
            "frecceOnly": False,
            "regionalOnly": False,
            "noChanges": False,
            "order": "DEPARTURE_DATE",
            "offset": 0,
            "limit": limit,
        },
        "advancedSearchRequest": {"bestFare": False, "bikeFilter": False},
    }
    with httpx.Client(timeout=TIMEOUT, headers=_HEADERS) as client:
        resp = client.post(f"{BASE}/ticket/solutions", json=payload)
        resp.raise_for_status()
        data = resp.json()

    journeys: list[Journey] = []
    for entry in data.get("solutions", []):
        sol = entry.get("solution", {})
        trains = sol.get("trains", [])
        # A solution with no departure time is a placeholder row, not an itinerary.
        if not sol.get("departureTime"):
            continue
        legs, layover_min = _parse_legs(sol)
        journeys.append(
            Journey(
                provider=name,
                mode="train",
                origin=sol.get("origin", dep_name),
                destination=sol.get("destination", arr_name),
                departure=datetime.fromisoformat(sol["departureTime"]),
                arrival=datetime.fromisoformat(sol["arrivalTime"]),
                changes=max(len(trains) - 1, 0),
                price=sol.get("price", {}).get("amount"),
                legs=legs,
                note=None if sol.get("status") == "SALEABLE" else sol.get("status"),
                deeplink=SHOP,
                layover_min=layover_min,
            )
        )
    logger.debug("Trenitalia %s->%s %s: %d soluzioni", dep_name, arr_name, day, len(journeys))
    return journeys


def _parse_legs(sol: dict) -> tuple[list[str], int | None]:
    """Per-node legs with the transfer time between consecutive trains.

    ``trains`` carries only acronym/name, but ``nodes`` carries each segment's stations and
    times. A connection's wait is the next node's departure minus this node's arrival, which is
    exactly the "sosta" a passenger experiences between changes.
    """
    nodes = sol.get("nodes", [])
    if not nodes:
        return [f"{t.get('acronym', '?')} {t.get('name', '')}".strip() for t in sol.get("trains", [])], None

    legs: list[str] = []
    total_wait = 0
    for i, node in enumerate(nodes):
        train = node.get("train", {})
        label = f"{train.get('acronym', '?')} {train.get('name', '')}".strip()
        dest = node.get("destination")
        arrival = node.get("arrivalTime")
        if dest and arrival:
            label += f" → {dest} {datetime.fromisoformat(arrival):%H:%M}"
        legs.append(label)
        if i < len(nodes) - 1:
            nxt = nodes[i + 1]
            wait = (
                datetime.fromisoformat(nxt["departureTime"])
                - datetime.fromisoformat(node["arrivalTime"])
            ).total_seconds()
            wait_min = int(wait // 60)
            total_wait += wait_min
            h, m = divmod(wait_min, 60)
            legs.append(f"(sosta {h}h{m:02d})")

    return legs, total_wait if len(nodes) > 1 else None
