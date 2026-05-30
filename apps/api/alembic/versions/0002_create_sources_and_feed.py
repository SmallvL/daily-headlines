"""create sources and feed

Revision ID: 0002_create_sources_and_feed
Revises: 0001_create_users
Create Date: 2026-05-28 00:00:01
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_create_sources_and_feed"
down_revision: str | None = "0001_create_users"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamp_column(name: str) -> sa.Column:
    return sa.Column(name, sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("config_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("created_by", sa.String(length=64), nullable=False),
        sa.Column("last_fetch_at", sa.DateTime(timezone=True), nullable=True),
        timestamp_column("created_at"),
        timestamp_column("updated_at"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_sources_created_by", "sources", ["created_by"])

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=64), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("settings_json", sa.Text(), nullable=False, server_default="{}"),
        timestamp_column("created_at"),
        timestamp_column("updated_at"),
        sa.UniqueConstraint("user_id", "source_id", name="uq_subscription_user_source"),
    )
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"])
    op.create_index("ix_subscriptions_source_id", "subscriptions", ["source_id"])

    op.create_table(
        "feed_items",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("source_id", sa.String(length=64), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("external_id", sa.String(length=512), nullable=True),
        sa.Column("dedupe_key", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("content_md", sa.Text(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("author", sa.String(length=255), nullable=True),
        sa.Column("language", sa.String(length=32), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        timestamp_column("fetched_at"),
        sa.Column("raw_json", sa.Text(), nullable=False, server_default="{}"),
        timestamp_column("created_at"),
        timestamp_column("updated_at"),
        sa.UniqueConstraint("source_id", "dedupe_key", name="uq_feed_item_source_dedupe"),
    )
    op.create_index("ix_feed_items_source_id", "feed_items", ["source_id"])
    op.create_index("ix_feed_items_dedupe_key", "feed_items", ["dedupe_key"])


def downgrade() -> None:
    op.drop_table("feed_items")
    op.drop_table("subscriptions")
    op.drop_table("sources")
