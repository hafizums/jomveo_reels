"""Add ephemeral provider asset metadata.

Revision ID: 20260630_0006
Revises: 20260630_0005
"""

from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

revision: str = "20260630_0006"
down_revision: str | None = "20260630_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "assets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="SET NULL")),
        sa.Column("job_id", sa.String(36), sa.ForeignKey("generation_jobs.id", ondelete="CASCADE")),
        sa.Column(
            "provider_run_id", sa.String(36), sa.ForeignKey("provider_runs.id", ondelete="SET NULL")
        ),
        sa.Column(
            "created_by_user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL")
        ),
        sa.Column("asset_type", sa.String(20), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("storage_type", sa.String(30), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("download_required", sa.Boolean(), nullable=False),
        sa.Column("filename", sa.String(255)),
        sa.Column("content_type", sa.String(100)),
        sa.Column("metadata_json", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    for column in (
        "project_id",
        "job_id",
        "provider_run_id",
        "created_by_user_id",
        "status",
        "expires_at",
    ):
        op.create_index(f"ix_assets_{column}", "assets", [column])


def downgrade() -> None:
    op.drop_table("assets")
