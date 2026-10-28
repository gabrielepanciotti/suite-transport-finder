"""Cursor pagination primitives shared by finder endpoints."""
from __future__ import annotations

import base64
import binascii
from collections.abc import Sequence
from typing import Generic, TypeVar

from fastapi import HTTPException
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel


T = TypeVar("T")


class Pagina(BaseModel, Generic[T]):
    """A stable cursor-paginated response envelope."""

    items: list[T]
    total: int
    next_cursor: str | None = None


def decode_cursor(cursor: str | None) -> int:
    """Decode an opaque URL-safe base64 offset, or reject malformed cursors."""
    if cursor is None:
        return 0
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        value = base64.urlsafe_b64decode(padded.encode("ascii")).decode("ascii")
        offset = int(value)
        if offset < 0 or str(offset) != value:
            raise ValueError
    except (binascii.Error, UnicodeEncodeError, UnicodeDecodeError, ValueError):
        raise HTTPException(status_code=422, detail="Cursor di paginazione non valido") from None
    return offset


def encode_cursor(offset: int) -> str:
    return base64.urlsafe_b64encode(str(offset).encode("ascii")).decode("ascii").rstrip("=")


def paginate_list(items: Sequence[T], *, limit: int, cursor: str | None) -> Pagina[T]:
    """Apply finder cursor semantics to an already materialized list."""
    offset = decode_cursor(cursor)
    page_items = list(items[offset:offset + limit])
    next_cursor = encode_cursor(offset + limit) if offset + limit < len(items) else None
    return Pagina(items=page_items, total=len(items), next_cursor=next_cursor)


async def paginate_query(
    session: AsyncSession,
    statement: Select[tuple[T]],
    *,
    limit: int,
    cursor: str | None,
) -> Pagina[T]:
    """Apply finder cursor semantics to a SQLAlchemy select statement."""
    offset = decode_cursor(cursor)
    total = await session.scalar(select(func.count()).select_from(statement.order_by(None).subquery()))
    rows = (await session.execute(statement.offset(offset).limit(limit + 1))).scalars().all()
    has_more = len(rows) > limit
    page_items = list(rows[:limit])
    return Pagina(
        items=page_items,
        total=total or 0,
        next_cursor=encode_cursor(offset + limit) if has_more else None,
    )
