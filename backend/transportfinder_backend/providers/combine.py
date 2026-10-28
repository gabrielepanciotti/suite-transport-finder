"""Mixed-mode itineraries that no single carrier will sell you.

Trenitalia only sells trains and FlixBus only sells coaches, so neither will ever propose
"train to Bologna, coach onward". This module builds those by hand: for each candidate hub
it searches every provider on both legs and pairs the ones that connect with enough time
to change.

Total changes of a combined itinerary = leg1.changes + leg2.changes + 1 (the hub itself).
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from . import PROVIDERS
from .base import Journey

logger = logging.getLogger(__name__)

# Hubs where the Rome/Florence–Bologna spine meets the Venice–Trieste line.
DEFAULT_HUBS = ["Bologna", "Firenze", "Venezia", "Padova"]
MIN_TRANSFER = timedelta(minutes=25)
MAX_LAYOVER = timedelta(hours=4)


@dataclass(frozen=True, slots=True)
class Combined:
    """Two legs stitched at a hub, presented as one option."""

    hub: str
    first: Journey
    second: Journey

    @property
    def departure(self) -> datetime:
        return self.first.departure

    @property
    def arrival(self) -> datetime:
        return self.second.arrival

    @property
    def changes(self) -> int:
        return self.first.changes + self.second.changes + 1

    @property
    def price(self) -> float | None:
        if self.first.price is None or self.second.price is None:
            return None
        return round(self.first.price + self.second.price, 2)

    @property
    def price_breakdown(self) -> str:
        """The two ticket prices, because a combined trip is two separate purchases."""
        parts = [f"{p:.2f}" if p is not None else "n.d." for p in (self.first.price, self.second.price)]
        return " + ".join(parts)

    @property
    def deeplink(self) -> str | None:
        links = [l for l in (self.first.deeplink, self.second.deeplink) if l]
        return " | ".join(dict.fromkeys(links)) or None

    @property
    def layover(self) -> timedelta:
        return self.second.departure - self.first.arrival

    @property
    def layover_min(self) -> int | None:
        return round(self.layover.total_seconds() / 60)

    @property
    def note(self) -> str | None:
        """Warn when the hub transfer spans two stops that are not side by side."""
        hub = self.hub.lower()
        if self.first.mode == self.second.mode:
            return None
        if "firenze" in hub:
            return "trasbordo: il treno arriva in stazione, il bus parte dalla fermata di interscambio (tram T1 ~25')"
        if "venezia" in hub:
            return "trasbordo: verifica la fermata bus (Mestre FS o Tronchetto, ~15 km)"
        return None

    @property
    def duration_min(self) -> int:
        return round((self.arrival - self.departure).total_seconds() / 60)

    @property
    def duration_hhmm(self) -> str:
        h, m = divmod(self.duration_min, 60)
        return f"{h}h{m:02d}"

    @property
    def mode(self) -> str:
        return "mix" if self.first.mode != self.second.mode else self.first.mode

    @property
    def legs(self) -> list[str]:
        icon = {"train": "🚆", "bus": "🚌"}
        return [
            f"{icon[self.first.mode]} {' + '.join(self.first.legs)} → {self.hub}"
            f" {self.first.arrival:%H:%M}",
            f"(sosta {self.layover.seconds // 3600}h{self.layover.seconds % 3600 // 60:02d})",
            f"{icon[self.second.mode]} {self.second.departure:%H:%M} {' + '.join(self.second.legs)}",
        ]


def _search(mode: str, origin: str, destination: str, day: date, from_time: time) -> list[Journey]:
    module = PROVIDERS[mode]
    try:
        if mode == "train":
            return module.search(origin, destination, day, from_time=from_time)
        return module.search(origin, destination, day)
    except Exception as exc:  # noqa: BLE001 - a dead hub must not sink the whole search
        logger.debug("combine: %s %s->%s ko: %s", module.name, origin, destination, exc)
        return []


def _purchasable(leg: Journey) -> bool:
    """A leg you cannot buy on its own cannot be half of a self-assembled itinerary.

    Trenitalia prices some feeder services (the `FL`/Link coaches) at 0.00 because they are
    only sold bundled with a Frecciarossa ticket. Pairing one of those produces an itinerary
    that looks like the cheapest on the board and cannot actually be booked.
    """
    return leg.price is not None and leg.price > 0


def _pair(hub: str, first_legs: list[Journey], second_legs: list[Journey]) -> list[Combined]:
    out: list[Combined] = []
    for first in first_legs:
        for second in sorted(second_legs, key=lambda j: j.departure):
            gap = second.departure - first.arrival
            if gap < MIN_TRANSFER:
                continue
            if gap > MAX_LAYOVER:
                break  # sorted by departure, everything later is worse
            out.append(Combined(hub=hub, first=first, second=second))
            break  # earliest valid connection only, one row per first leg
    return out


def search(
    origin: str,
    destination: str,
    day: date,
    *,
    hubs: list[str] | None = None,
    modes: list[str] | None = None,
    from_time: time = time(5, 0),
    max_changes: int = 1,
) -> list[Combined]:
    """Build every hub itinerary whose total change count fits ``max_changes``."""
    hubs = hubs or DEFAULT_HUBS
    modes = modes or list(PROVIDERS)
    jobs = [(hub, mode) for hub in hubs for mode in modes]

    with ThreadPoolExecutor(max_workers=min(8, len(jobs) or 1)) as pool:
        first_legs = list(pool.map(lambda j: _search(j[1], origin, j[0], day, from_time), jobs))

    by_hub: dict[str, list[Journey]] = {hub: [] for hub in hubs}
    for (hub, _mode), legs in zip(jobs, first_legs, strict=True):
        # A leg that already burns the whole change budget can never be half of a pair.
        by_hub[hub] += [
            leg for leg in legs if leg.changes < max_changes and _purchasable(leg)
        ]

    combos: list[Combined] = []
    for hub, legs in by_hub.items():
        if not legs:
            continue
        earliest = min(leg.arrival for leg in legs) + MIN_TRANSFER
        onward: list[Journey] = []
        with ThreadPoolExecutor(max_workers=len(modes)) as pool:
            for batch in pool.map(
                lambda m: _search(m, hub, destination, day, earliest.time()), modes
            ):
                onward += batch
        combos += _pair(hub, legs, [leg for leg in onward if _purchasable(leg)])

    return sorted(
        (c for c in combos if c.changes <= max_changes), key=lambda c: (c.price is None, c.price or 0)
    )
