"""Add billing, quotas, reservations, and cost records.

Revision ID: 20260630_0005
Revises: 20260630_0004
Create Date: 2026-06-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260630_0005"
down_revision: str | None = "20260630_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "credit_accounts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("balance_credits", sa.Integer(), nullable=False),
        sa.Column("reserved_credits", sa.Integer(), nullable=False),
        sa.Column("lifetime_purchased_credits", sa.Integer(), nullable=False),
        sa.Column("lifetime_used_credits", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_credit_accounts_project_id", "credit_accounts", ["project_id"])
    op.create_table(
        "project_quotas",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("daily_job_limit", sa.Integer()),
        sa.Column("monthly_job_limit", sa.Integer()),
        sa.Column("daily_credit_limit", sa.Integer()),
        sa.Column("monthly_credit_limit", sa.Integer()),
        sa.Column("max_concurrent_jobs", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "credit_transactions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "account_id",
            sa.String(36),
            sa.ForeignKey("credit_accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "job_id", sa.String(36), sa.ForeignKey("generation_jobs.id", ondelete="SET NULL")
        ),
        sa.Column("type", sa.String(30), nullable=False),
        sa.Column("amount_credits", sa.Integer(), nullable=False),
        sa.Column("balance_after_credits", sa.Integer(), nullable=False),
        sa.Column("reserved_after_credits", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(500)),
        sa.Column("idempotency_key", sa.String(255)),
        sa.Column("metadata_json", sa.JSON()),
        sa.Column(
            "created_by_user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL")
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_credit_transactions_project_id", "credit_transactions", ["project_id"])
    op.create_index("ix_credit_transactions_type", "credit_transactions", ["type"])
    op.create_table(
        "job_cost_estimates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "job_id",
            sa.String(36),
            sa.ForeignKey("generation_jobs.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("estimated_credits", sa.Integer(), nullable=False),
        sa.Column("reserved_credits", sa.Integer(), nullable=False),
        sa.Column("pricing_version", sa.String(30), nullable=False),
        sa.Column("estimate_json", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "provider_cost_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "provider_run_id", sa.String(36), sa.ForeignKey("provider_runs.id", ondelete="SET NULL")
        ),
        sa.Column(
            "job_id",
            sa.String(36),
            sa.ForeignKey("generation_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(100), nullable=False),
        sa.Column("model", sa.String(150)),
        sa.Column("estimated_credits", sa.Integer(), nullable=False),
        sa.Column("actual_credits", sa.Integer(), nullable=False),
        sa.Column("pricing_version", sa.String(30), nullable=False),
        sa.Column("metadata_json", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_provider_cost_records_job_id", "provider_cost_records", ["job_id"])
    op.create_table(
        "rate_limit_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE")),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("key", sa.String(100), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_seconds", sa.Integer(), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    with op.batch_alter_table("generation_jobs") as batch_op:
        batch_op.add_column(sa.Column("estimated_credits", sa.Integer()))
        batch_op.add_column(sa.Column("reserved_credits", sa.Integer()))
        batch_op.add_column(sa.Column("billing_status", sa.String(20)))


def downgrade() -> None:
    with op.batch_alter_table("generation_jobs") as batch_op:
        batch_op.drop_column("billing_status")
        batch_op.drop_column("reserved_credits")
        batch_op.drop_column("estimated_credits")
    op.drop_table("rate_limit_events")
    op.drop_table("provider_cost_records")
    op.drop_table("job_cost_estimates")
    op.drop_table("credit_transactions")
    op.drop_table("project_quotas")
    op.drop_table("credit_accounts")
