"""Shared vocabulary for every transport provider.

A provider turns "from A to B on day D" into a list of :class:`Journey`. Nothing
provider-specific leaks past this boundary, so the CLI and the API can rank rail against
coach without knowing how either backend talks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class Journey:
    """One bookable door-to-door option on a single day."""

    provider: str
    mode: str  # "train" | "bus"
    origin: str
    destination: str
    departure: datetime
    arrival: datetime
    changes: int
    price: float | None
    currency: str = "EUR"
    legs: list[str] = field(default_factory=list)
    note: str | None = None
    deeplink: str | None = None
    layover_min: int | None = None

    @property
    def duration_min(self) -> int:
        return round((self.arrival - self.departure).total_seconds() / 60)

    @property
    def duration_hhmm(self) -> str:
        h, m = divmod(self.duration_min, 60)
        return f"{h}h{m:02d}"


class Provider(Protocol):
    """Every provider module exposes this one callable."""

    name: str

    def search(self, origin: str, destination: str, day: date) -> list[Journey]: ...
