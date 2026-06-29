"""Add provider run observability fields.

Revision ID: 20260629_0003
Revises: 20260629_0002
Create Date: 2026-06-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260629_0003"
down_revision: str | None = "20260629_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("provider_runs") as batch_op:
        batch_op.add_column(sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("duration_ms", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("external_request_id", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("sdk_version", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("provider_mode", sa.String(length=50), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("provider_runs") as batch_op:
        batch_op.drop_column("provider_mode")
        batch_op.drop_column("sdk_version")
        batch_op.drop_column("external_request_id")
        batch_op.drop_column("duration_ms")
        batch_op.drop_column("completed_at")
        batch_op.drop_column("started_at")
