"""SQLAlchemy models for the TransportFinder node.

The node owns the "how to get there / get around" domain (flights, trains,
buses, car, ferry, local transit — declared editorially in
`brain/conoscenza/`). This module gives that domain a minimal structured
store: a single `TransportRoute` table modelling a leg between two places
plus assisted/link data. Paid providers (Amadeus/Kiwi/Rome2Rio) are future
work — the model only leaves room for them via `provider`/`source`, nothing
is integrated yet.

Registered on `suite_backend_core.Base` — picked up automatically by
`alembic revision --autogenerate` via ../database/env.py.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from suite_backend_core import Base


def _utcnow() -> datetime:
    """Timezone-aware UTC now (never naive `utcnow()`)."""
    return datetime.now(timezone.utc)


class TransportRoute(Base):
    """A transport leg between two places ("how to get there / get around").

    `mode` is the transport type (flight/train/bus/car/ferry/transit/other),
    `provider` the carrier/operator (e.g. an airline), `url` an assisted
    deep-link. `source` records how the row came to be
    ("assisted"/"link"/"api") — the seam for future paid-API integrations.
    """

    __tablename__ = "transport_routes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    origin: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    destination: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    mode: Mapped[str] = mapped_column(String(20), nullable=False, default="other")
    provider: Mapped[str | None] = mapped_column(String(200))
    url: Mapped[str | None] = mapped_column(Text)
    duration_minutes: Mapped[int | None] = mapped_column(Integer)
    price: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str | None] = mapped_column(String(3), default="EUR")
    departure: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    arrival: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="assisted")
    created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
