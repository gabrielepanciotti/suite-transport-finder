"""add deleted_at to transport routes

Revision ID: a1c4d2e7f9b0
Revises: fbd3a9cf6fcb
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "a1c4d2e7f9b0"
down_revision = "fbd3a9cf6fcb"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("transport_routes", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("transport_routes", "deleted_at")
