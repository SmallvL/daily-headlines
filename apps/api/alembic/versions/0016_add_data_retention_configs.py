"""data_retention_configs table

Revision ID: 0016
Revises: 0015
Create Date: 2026-05-29
"""

from alembic import op
import sqlalchemy as sa

revision = "0016"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "data_retention_configs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("table_name", sa.String(100), nullable=False, unique=True),
        sa.Column("max_age_days", sa.Integer(), nullable=True),
        sa.Column("max_records", sa.Integer(), nullable=True),
        sa.Column("keep_saved", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("config_json", sa.Text(), nullable=True),
        sa.Column("last_purge_at", sa.DateTime(), nullable=True),
        sa.Column("last_purge_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # Insert default retention configs
    configs = [
        ("feed_items", 90, 500, 1, 1),
        ("source_fetch_logs", 30, None, 0, 1),
        ("audit_logs", 180, None, 0, 1),
        ("agent_drafts", 30, None, 0, 1),
        ("user_item_states", 90, None, 0, 1),
    ]
    for table_name, max_age, max_rec, keep_saved, enabled in configs:
        op.execute(
            f"INSERT INTO data_retention_configs "
            f"(table_name, max_age_days, max_records, keep_saved, enabled) "
            f"VALUES ('{table_name}', {max_age}, {'NULL' if max_rec is None else max_rec}, "
            f"{keep_saved}, {enabled})"
        )


def downgrade() -> None:
    op.drop_table("data_retention_configs")
