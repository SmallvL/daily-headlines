"""add cron schedule fields to sources

Revision ID: 0013
Revises: 0012
Create Date: 2026-05-29
"""

from alembic import op
import sqlalchemy as sa

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("sources") as batch:
        batch.add_column(sa.Column("schedule_mode", sa.String(16), nullable=False, server_default="interval"))
        batch.add_column(sa.Column("cron_expression", sa.String(64), nullable=True))
        batch.add_column(sa.Column("cron_days_of_week", sa.String(32), nullable=True))
        batch.add_column(sa.Column("cron_hour", sa.Integer, nullable=True))
        batch.add_column(sa.Column("cron_minute", sa.Integer, nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("sources") as batch:
        batch.drop_column("cron_minute")
        batch.drop_column("cron_hour")
        batch.drop_column("cron_days_of_week")
        batch.drop_column("cron_expression")
        batch.drop_column("schedule_mode")
