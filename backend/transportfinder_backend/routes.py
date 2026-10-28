"""Domain API for the TransportFinder node — transport routes/legs.

Minimal CRUD over the async DB (see `db.py`) for `TransportRoute`: the
structured "how to get there / get around" store. Assisted/link rows today;
the `provider`/`source` columns leave room for future paid-API integrations
(Amadeus/Kiwi/Rome2Rio) without a schema change.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from . import models, schemas
from .db import get_db_session
from .pagination import Pagina, paginate_query
from .providers import PROVIDERS
from .search import search

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


def _to_out(journey) -> schemas.JourneyOut:
    """One ranked option (Journey or Combined) as the API's response model."""
    return schemas.JourneyOut(
        provider=getattr(journey, "provider", None),
        mode=journey.mode,
        origin=getattr(journey, "origin", None),
        destination=getattr(journey, "destination", None),
        departure=journey.departure,
        arrival=journey.arrival,
        duration_min=journey.duration_min,
        changes=journey.changes,
        layover_min=getattr(journey, "layover_min", None),
        price=journey.price,
        currency=getattr(journey, "currency", "EUR"),
        legs=journey.legs,
        note=getattr(journey, "note", None),
        deeplink=journey.deeplink,
        price_breakdown=getattr(journey, "price_breakdown", None),
    )


@router.post("/search", response_model=schemas.SearchResponse)
async def search_transport(payload: schemas.SearchRequest) -> schemas.SearchResponse:
    """Search train/bus options for one route, live from the providers.

    The blocking provider calls run off the event loop (`run_in_threadpool`); a
    provider that fails degrades into `errors`, never a 5xx.
    """
    unknown = [m for m in payload.modes if m not in PROVIDERS]
    if unknown:
        raise HTTPException(
            status_code=422,
            detail=f"unknown modes: {', '.join(unknown)} (available: {', '.join(PROVIDERS)})",
        )

    modes = list(dict.fromkeys(payload.modes))
    logger.info(
        "search %s->%s %s modes=%s combine=%s",
        payload.origin,
        payload.destination,
        payload.day,
        modes,
        payload.combine,
    )

    result = await run_in_threadpool(
        search,
        payload.origin,
        payload.destination,
        payload.day,
        modes=modes,
        from_time=payload.from_time,
        sort=payload.sort,
        max_changes=payload.max_changes,
        combine=payload.combine,
        via=payload.via,
        max_results=payload.max_results,
    )

    if result.errors:
        logger.warning("search %s->%s degraded: %d provider(s) failed", payload.origin, payload.destination, len(result.errors))

    return schemas.SearchResponse(
        origin=result.origin,
        destination=result.destination,
        date=result.date,
        errors=result.errors,
        journeys=[_to_out(j) for j in result.journeys],
    )


async def _get_or_404(session: AsyncSession, route_id: int) -> models.TransportRoute:
    route = await session.scalar(
        select(models.TransportRoute).where(
            models.TransportRoute.id == route_id,
            models.TransportRoute.deleted_at.is_(None),
        )
    )
    if route is None:
        raise HTTPException(status_code=404, detail="Transport route not found")
    return route


@router.post("/routes", response_model=schemas.TransportRouteOut, status_code=201)
async def create_route(
    payload: schemas.TransportRouteCreate,
    session: AsyncSession = Depends(get_db_session),
) -> models.TransportRoute:
    route = models.TransportRoute(**payload.model_dump())
    session.add(route)
    await session.commit()
    await session.refresh(route)
    logger.info("created transport route id=%s %s->%s", route.id, route.origin, route.destination)
    return route


@router.get("/routes", response_model=list[schemas.TransportRouteOut])
async def list_routes(
    session: AsyncSession = Depends(get_db_session),
    origin: str | None = Query(None, alias="from"),
    destination: str | None = Query(None, alias="to"),
    mode: str | None = Query(None),
) -> list[models.TransportRoute]:
    stmt = select(models.TransportRoute).where(models.TransportRoute.deleted_at.is_(None))
    if origin is not None:
        stmt = stmt.where(models.TransportRoute.origin == origin)
    if destination is not None:
        stmt = stmt.where(models.TransportRoute.destination == destination)
    if mode is not None:
        stmt = stmt.where(models.TransportRoute.mode == mode)
    stmt = stmt.order_by(models.TransportRoute.id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.get("/saved", response_model=Pagina[schemas.TransportRouteOut])
async def list_saved_routes(
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = Query(None),
    q: str | None = Query(None),
) -> Pagina[schemas.TransportRouteOut]:
    """List saved routes using the family's stable cursor contract."""
    stmt = select(models.TransportRoute).where(models.TransportRoute.deleted_at.is_(None))
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(or_(
            models.TransportRoute.origin.ilike(pattern),
            models.TransportRoute.destination.ilike(pattern),
            models.TransportRoute.provider.ilike(pattern),
        ))
    return await paginate_query(session, stmt.order_by(models.TransportRoute.id.desc()), limit=limit, cursor=cursor)


@router.get("/routes/{route_id}", response_model=schemas.TransportRouteOut)
async def get_route(
    route_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> models.TransportRoute:
    return await _get_or_404(session, route_id)


@router.patch("/routes/{route_id}", response_model=schemas.TransportRouteOut)
@router.patch("/saved/{route_id}", response_model=schemas.TransportRouteOut)
async def update_route(
    route_id: int,
    payload: schemas.TransportRouteUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> models.TransportRoute:
    route = await _get_or_404(session, route_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(route, field, value)
    await session.commit()
    await session.refresh(route)
    return route


@router.delete("/routes/{route_id}", status_code=204)
@router.delete("/saved/{route_id}", status_code=204)
async def delete_route(
    route_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    route = await _get_or_404(session, route_id)
    route.deleted_at = models._utcnow()
    await session.commit()
