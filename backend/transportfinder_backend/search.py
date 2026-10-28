"""Shared search pipeline: collect from providers, combine, dedupe, rank.

Both the ``tfind`` CLI and the ``POST /api/search`` endpoint run through
:func:`search`, so the two can never drift apart on what a ranked option looks
like. Everything here is pure orchestration over the provider modules — no
network, no rendering.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date, time

from .providers import PROVIDERS, combine as combine_provider
from .providers.base import Journey

logger = logging.getLogger(__name__)

# A ranked option is either a single-provider Journey or a mixed-mode combine.Combined.
AnyJourney = Journey | combine_provider.Combined

SORTS = {
    "departure": lambda j: j.departure,
    "duration": lambda j: j.duration_min,
    "price": lambda j: (j.price is None, j.price or 0.0),
}


def collect(
    origin: str, destination: str, day: date, modes: list[str], from_time: time
) -> tuple[list[Journey], list[str]]:
    """Query the selected providers in parallel; a failing provider degrades, never blocks."""
    errors: list[str] = []

    def run(mode: str) -> list[Journey]:
        module = PROVIDERS[mode]
        try:
            if mode == "train":
                return module.search(origin, destination, day, from_time=from_time)
            return module.search(origin, destination, day)
        except Exception as exc:  # noqa: BLE001 - one dead provider must not kill the search
            logger.warning("provider %s %s->%s failed: %s", module.name, origin, destination, exc)
            errors.append(f"{module.name}: {exc}")
            return []

    with ThreadPoolExecutor(max_workers=len(modes)) as pool:
        results = list(pool.map(run, modes))
    return [j for batch in results for j in batch], errors


def dedupe(journeys: list[AnyJourney]) -> list[AnyJourney]:
    """Collapse rows that are the same physical trip, keeping both ways to buy it.

    Two different things share a departure/arrival pair. One is noise: a ride sold whole that
    also surfaces as an A→hub + hub→B pair, same clock, two tickets, higher total — drop it.
    The other is a real choice: FlixBus sells Firenze→Udine 07:00→12:55 as one 29,47 € ticket
    with a protected connection, while buying its two legs apart costs 20,96 €. Same buses,
    8,51 € apart, and only one of them rebooks you if the first leg is late — so both belong
    on the board.

    The rule that separates them: a split survives only when it undercuts the single ticket.
    """
    singles: dict[tuple, object] = {}
    splits: dict[tuple, object] = {}

    def cheaper(a, b) -> bool:
        return (a.price if a.price is not None else float("inf")) < (
            b.price if b.price is not None else float("inf")
        )

    for j in journeys:
        key = (j.departure, j.arrival)
        bucket = splits if hasattr(j, "price_breakdown") else singles
        current = bucket.get(key)
        if current is None or cheaper(j, current):
            bucket[key] = j

    kept = list(singles.values())
    for key, split in splits.items():
        rival = singles.get(key)
        if rival is None or cheaper(split, rival):
            kept.append(split)
    return kept


@dataclass(frozen=True, slots=True)
class SearchResult:
    """The outcome of one search: ranked options plus per-provider degradation notes."""

    origin: str
    destination: str
    date: date
    errors: list[str]
    journeys: list[AnyJourney]


def search(
    origin: str,
    destination: str,
    day: date,
    *,
    modes: list[str],
    from_time: time = time(5, 0),
    sort: str = "departure",
    max_changes: int | None = None,
    combine: bool = False,
    via: list[str] | None = None,
    max_results: int = 0,
) -> SearchResult:
    """Run the full pipeline: collect → (combine) → filter → dedupe → rank → limit."""
    journeys, errors = collect(origin, destination, day, modes, from_time)

    if combine:
        hubs = via or combine_provider.DEFAULT_HUBS
        changes_budget = max_changes if max_changes is not None else 1
        journeys += combine_provider.search(
            origin,
            destination,
            day,
            hubs=hubs,
            modes=modes,
            from_time=from_time,
            max_changes=changes_budget,
        )

    if max_changes is not None:
        journeys = [j for j in journeys if j.changes <= max_changes]
    journeys = dedupe(journeys)
    journeys.sort(key=SORTS[sort])
    if max_results:
        journeys = journeys[:max_results]

    return SearchResult(origin, destination, day, errors, journeys)


def journey_to_dict(journey: AnyJourney) -> dict:
    """One ranked option as a plain dict with ISO timestamps — for the CLI's JSON output.

    Works for both a plain `Journey` and a `combine_provider.Combined` (a mixed-mode itinerary): fields
    only the former carries (`provider`, `origin`, `destination`, `currency`, `note`) fall back
    to their empty values on the latter, and vice-versa for `price_breakdown`.
    """
    layover_min = getattr(journey, "layover_min", None)
    return {
        "provider": getattr(journey, "provider", None),
        "mode": journey.mode,
        "origin": getattr(journey, "origin", None),
        "destination": getattr(journey, "destination", None),
        "departure": journey.departure.isoformat(),
        "arrival": journey.arrival.isoformat(),
        "duration_min": journey.duration_min,
        "changes": journey.changes,
        "layover_min": layover_min,
        "price": journey.price,
        "currency": getattr(journey, "currency", "EUR"),
        "legs": journey.legs,
        "note": getattr(journey, "note", None),
        "deeplink": journey.deeplink,
        "price_breakdown": getattr(journey, "price_breakdown", None),
    }
