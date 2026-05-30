"""create source fetch logs

Revision ID: 0006_create_source_fetch_logs
Revises: 0005_add_source_schedule
Create Date: 2026-05-28 00:00:05
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006_create_source_fetch_logs"
down_revision: str | None = "0005_add_source_schedule"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "source_fetch_logs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("source_id", sa.String(length=64), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("trigger", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("inserted_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_source_fetch_logs_source_id", "source_fetch_logs", ["source_id"])
    op.create_index("ix_source_fetch_logs_status", "source_fetch_logs", ["status"])


def downgrade() -> None:
    op.drop_table("source_fetch_logs")
