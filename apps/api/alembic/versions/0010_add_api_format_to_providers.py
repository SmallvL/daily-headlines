"""add api_format to llm_providers

Revision ID: 0010
Revises: 0009
Create Date: 2026-05-29
"""

from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "llm_providers",
        sa.Column("api_format", sa.String(32), nullable=False, server_default="openai"),
    )


def downgrade() -> None:
    op.drop_column("llm_providers", "api_format")
