"""FlixBus coach search via the public global.api.flixbus.com endpoints.

``/search/autocomplete/cities`` resolves a city name to FlixBus's UUID, then
``/search/service/v4/search`` returns the day's departures with live prices. Results are
keyed by fare class, so one trip can yield several rows; we keep the cheapest available one.

Prices come in two flavours and only one of them is what you pay: ``price.total`` omits
FlixBus's booking fee, while ``price.total_with_platform_fee`` is the checkout figure. We
report the latter — the gap is ~0.99 € per ticket, which a two-ticket itinerary pays twice.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime
from functools import lru_cache

import httpx

from .base import Journey

logger = logging.getLogger(__name__)

name = "FlixBus"
BASE = "https://global.api.flixbus.com"
SHOP = "https://shop.flixbus.it/search"
_HEADERS = {"accept": "application/json", "user-agent": "Mozilla/5.0 (transportfinder)"}
TIMEOUT = httpx.Timeout(45.0)


@lru_cache(maxsize=128)
def resolve_city(city: str, country: str = "IT") -> tuple[str, str]:
    """Map a city name to (uuid, canonical name)."""
    with httpx.Client(timeout=TIMEOUT, headers=_HEADERS) as client:
        resp = client.get(
            f"{BASE}/search/autocomplete/cities",
            params={"q": city, "lang": "it", "country": country, "flixbus_cities_only": "false"},
        )
        resp.raise_for_status()
        hits = resp.json()
    if not hits:
        raise LookupError(f"FlixBus: nessuna città per {city!r}")
    return hits[0]["id"], hits[0]["name"]


def deeplink(from_id: str, to_id: str, day: date) -> str:
    return (
        f"{SHOP}?departureCity={from_id}&arrivalCity={to_id}"
        f"&rideDate={day:%d.%m.%Y}&adult=1&_locale=it&currency=EUR"
    )


def search(origin: str, destination: str, day: date) -> list[Journey]:
    from_id, from_name = resolve_city(origin)
    to_id, to_name = resolve_city(destination)
    params = {
        "from_city_id": from_id,
        "to_city_id": to_id,
        "departure_date": day.strftime("%d.%m.%Y"),
        "products": json.dumps({"adult": 1}),
        "currency": "EUR",
        "locale": "it",
        "search_by": "cities",
        "include_after_midnight_rides": 1,
    }
    with httpx.Client(timeout=TIMEOUT, headers=_HEADERS) as client:
        resp = client.get(f"{BASE}/search/service/v4/search", params=params)
        resp.raise_for_status()
        data = resp.json()

    # Same physical ride can appear under several fare classes; keep the cheapest per ride.
    cheapest: dict[str, Journey] = {}
    for trip in data.get("trips", []):
        for ride in trip.get("results", {}).values():
            if ride.get("status") not in ("available", "calculating"):
                continue
            fares = ride.get("price", {})
            price = fares.get("total_with_platform_fee", fares.get("total"))
            transfers = ride.get("interconnection_transfers")
            if transfers is None:
                transfers = str(ride.get("transfer_type_key", "")).count("#")
            journey = Journey(
                provider=name,
                mode="bus",
                origin=from_name,
                destination=to_name,
                departure=datetime.fromisoformat(ride["departure"]["date"]),
                arrival=datetime.fromisoformat(ride["arrival"]["date"]),
                changes=int(transfers),
                price=price,
                legs=[ride.get("provider", "flixbus")],
                deeplink=deeplink(from_id, to_id, day),
            )
            key = journey.departure.isoformat()
            current = cheapest.get(key)
            if current is None or (price is not None and (current.price or 1e9) > price):
                cheapest[key] = journey
    logger.debug("FlixBus %s->%s %s: %d corse", from_name, to_name, day, len(cheapest))
    return sorted(cheapest.values(), key=lambda j: j.departure)
