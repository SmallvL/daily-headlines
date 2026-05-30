"""add source schedule

Revision ID: 0005_add_source_schedule
Revises: 0004_create_user_item_states
Create Date: 2026-05-28 00:00:04
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_add_source_schedule"
down_revision: str | None = "0004_create_user_item_states"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "sources",
        sa.Column("schedule_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("sources", sa.Column("schedule_interval_minutes", sa.Integer(), nullable=True))
    op.add_column("sources", sa.Column("next_fetch_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("sources", "next_fetch_at")
    op.drop_column("sources", "schedule_interval_minutes")
    op.drop_column("sources", "schedule_enabled")
