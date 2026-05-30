"""create user item states

Revision ID: 0004_create_user_item_states
Revises: 0003_create_saved_searches
Create Date: 2026-05-28 00:00:03
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004_create_user_item_states"
down_revision: str | None = "0003_create_saved_searches"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_item_states",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("item_id", sa.String(length=64), sa.ForeignKey("feed_items.id"), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("saved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("hidden_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tags_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("user_id", "item_id", name="uq_user_item_state"),
    )
    op.create_index("ix_user_item_states_user_id", "user_item_states", ["user_id"])
    op.create_index("ix_user_item_states_item_id", "user_item_states", ["item_id"])


def downgrade() -> None:
    op.drop_table("user_item_states")
