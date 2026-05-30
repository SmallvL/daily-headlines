"""add fetch retry fields

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-28
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers
revision = "0007"
down_revision = "0006_create_source_fetch_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("source_fetch_logs") as batch_op:
        batch_op.add_column(
            sa.Column("attempt", sa.Integer(), nullable=False, server_default="1")
        )
        batch_op.add_column(
            sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3")
        )
        batch_op.add_column(
            sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("source_fetch_logs") as batch_op:
        batch_op.drop_column("next_retry_at")
        batch_op.drop_column("max_attempts")
        batch_op.drop_column("attempt")
