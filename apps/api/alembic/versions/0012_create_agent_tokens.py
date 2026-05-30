"""create agent_tokens table

Revision ID: 0012
Revises: 0011
Create Date: 2026-05-29
"""

from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_tokens",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("token_hash", sa.String(128), nullable=False, unique=True),
        sa.Column("prefix", sa.String(10), nullable=False),
        sa.Column("scopes", sa.Text, nullable=False, server_default="read:feed"),
        sa.Column("enabled", sa.Boolean, server_default=sa.text("1")),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "ix_agent_tokens_user_id",
        "agent_tokens",
        ["user_id"],
    )
    op.create_index(
        "ix_agent_tokens_token_hash",
        "agent_tokens",
        ["token_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_agent_tokens_token_hash", table_name="agent_tokens")
    op.drop_index("ix_agent_tokens_user_id", table_name="agent_tokens")
    op.drop_table("agent_tokens")
