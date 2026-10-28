"""Pydantic schemas for the TransportFinder node's structured store.

A `TransportRouteCreate` / `TransportRouteUpdate` / `TransportRouteOut` triple
for the single `TransportRoute` model in `models.py`. `Update` fields are all
optional (partial PATCH); `Out` mirrors the ORM model via `from_attributes`.
Enum-like string columns are constrained with `Literal[...]`.
"""
from __future__ import annotations

from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TransportMode = Literal["flight", "train", "bus", "car", "ferry", "transit", "other"]
TransportSource = Literal["assisted", "link", "api"]


class TransportRouteCreate(BaseModel):
    origin: str
    destination: str
    mode: TransportMode = "other"
    provider: str | None = None
    url: str | None = None
    duration_minutes: int | None = None
    price: float | None = None
    currency: str | None = "EUR"
    departure: datetime | None = None
    arrival: datetime | None = None
    notes: str | None = None
    source: TransportSource = "assisted"


class TransportRouteUpdate(BaseModel):
    origin: str | None = None
    destination: str | None = None
    mode: TransportMode | None = None
    provider: str | None = None
    url: str | None = None
    duration_minutes: int | None = None
    price: float | None = None
    currency: str | None = None
    departure: datetime | None = None
    arrival: datetime | None = None
    notes: str | None = None
    source: TransportSource | None = None


class TransportRouteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    origin: str
    destination: str
    mode: str
    provider: str | None = None
    url: str | None = None
    duration_minutes: int | None = None
    price: float | None = None
    currency: str | None = None
    departure: datetime | None = None
    arrival: datetime | None = None
    notes: str | None = None
    source: str
    created: datetime
    updated: datetime


class SearchRequest(BaseModel):
    origin: str = Field(min_length=1)
    destination: str = Field(min_length=1)
    day: date
    modes: list[str] = Field(default=["train", "bus"], min_length=1)
    from_time: time = time(5, 0)
    sort: Literal["price", "duration", "departure"] = "departure"
    max_changes: int | None = Field(default=None, ge=0)
    combine: bool = False
    via: list[str] | None = None
    max_results: int = Field(default=0, ge=0)


class JourneyOut(BaseModel):
    provider: str | None = None
    mode: str
    origin: str | None = None
    destination: str | None = None
    departure: datetime
    arrival: datetime
    duration_min: int
    changes: int
    layover_min: int | None = None
    price: float | None = None
    currency: str = "EUR"
    legs: list[str] = []
    note: str | None = None
    deeplink: str | None = None
    price_breakdown: str | None = None


class SearchResponse(BaseModel):
    origin: str
    destination: str
    date: date
    errors: list[str] = []
    journeys: list[JourneyOut] = []
