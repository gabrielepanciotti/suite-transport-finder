"""Itabus coach search via the site's own Salesforce Commerce Cloud JSON controllers.

Itabus has no documented API, but its booking SPA talks to two plain GET endpoints under
`/on/demandware.store/Sites-ITABUS-Site/it`: `Api-Stations` returns the full stop catalogue
(~1500 entries, cached for the process) and `Api-Travels` returns the day's routes with a
nested fare table. Dates must be ISO — the `dd/mm/yyyy` the website itself uses in its URLs
makes the controller answer 500.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from functools import lru_cache

import httpx

from .base import Journey

logger = logging.getLogger(__name__)

name = "Itabus"
BASE = "https://www.itabus.it/on/demandware.store/Sites-ITABUS-Site/it"
SHOP = "https://www.itabus.it/it/search"
_HEADERS = {"accept": "application/json", "user-agent": "Mozilla/5.0 (transportfinder)"}
TIMEOUT = httpx.Timeout(45.0)


@lru_cache(maxsize=1)
def _stations() -> list[dict]:
    with httpx.Client(timeout=TIMEOUT, headers=_HEADERS) as client:
        resp = client.get(f"{BASE}/Api-Stations")
        resp.raise_for_status()
        return resp.json()["data"]


@lru_cache(maxsize=128)
def resolve_station(city: str) -> tuple[str, str]:
    """Map a city name to (code, canonical name).

    Itabus lists both terminal groups (``PER_T``) and single stops (``PER1``); the group is
    what the search wants, so an exact name match on a ``_T`` code wins over anything else.
    """
    needle = city.strip().lower()
    exact = [s for s in _stations() if s["name"].strip().lower() == needle]
    for station in sorted(exact, key=lambda s: not s["code"].endswith("_T")):
        return station["code"], station["name"]
    for station in _stations():
        if needle in station["name"].strip().lower():
            return station["code"], station["name"]
    raise LookupError(f"Itabus: nessuna fermata per {city!r}")


def _cheapest(rates: dict) -> float | None:
    """Walk the carrier → class → family fare tree and return the lowest price."""
    prices: list[float] = []
    for carrier, classes in rates.items():
        if carrier == "available" or not isinstance(classes, dict):
            continue
        for families in classes.values():
            if not isinstance(families, dict):
                continue
            for family in families.values():
                if isinstance(family, dict) and isinstance(family.get("price"), (int, float)):
                    prices.append(float(family["price"]))
    return min(prices) if prices else None


def deeplink(origin_code: str, destination_code: str, day: date) -> str:
    return (
        f"{SHOP}?origin={origin_code}&destination={destination_code}"
        f"&dateStart={day:%d/%m/%Y}&adults=1&children=0"
    )


def search(origin: str, destination: str, day: date) -> list[Journey]:
    from_code, from_name = resolve_station(origin)
    to_code, to_name = resolve_station(destination)
    params = {
        "origin": from_code,
        "destination": to_code,
        "datestart": day.isoformat(),
        "adults": 1,
        "children": 0,
    }
    with httpx.Client(timeout=TIMEOUT, headers=_HEADERS) as client:
        resp = client.get(f"{BASE}/Api-Travels", params=params)
        resp.raise_for_status()
        data = resp.json()
    if data.get("error"):
        raise RuntimeError(data["error"])

    link = deeplink(from_code, to_code, day)
    journeys: list[Journey] = []
    for route in (data.get("data", {}).get("outbound", {}) or {}).get("routes", []):
        if not route.get("available", True):
            continue
        journeys.append(
            Journey(
                provider=name,
                mode="bus",
                origin=route.get("origin", {}).get("name", from_name),
                destination=route.get("destination", {}).get("name", to_name),
                departure=datetime.fromisoformat(route["departure_timestamp"]),
                arrival=datetime.fromisoformat(route["arrival_timestamp"]),
                changes=int(route.get("transferNumber", 0)),
                price=_cheapest(route.get("rates", {})),
                legs=[f"Itabus {route.get('service_name', '')}".strip()],
                deeplink=link,
            )
        )
    logger.debug("Itabus %s->%s %s: %d corse", from_name, to_name, day, len(journeys))
    return sorted(journeys, key=lambda j: j.departure)
