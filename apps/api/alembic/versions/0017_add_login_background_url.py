"""add login_background_url to user_preferences

Revision ID: 0017
Revises: 0016
Create Date: 2026-06-16
"""

from alembic import op
import sqlalchemy as sa

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_preferences",
        sa.Column("login_background_url", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_preferences", "login_background_url")
