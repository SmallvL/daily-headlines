"""create agent tables

Revision ID: 0009
Revises: 0008
Create Date: 2026-01-15
"""
import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "llm_providers",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=False),
        sa.Column("api_key", sa.Text(), nullable=False),
        sa.Column("model", sa.String(120), nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("0")),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("1")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "agent_drafts",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=False, index=True),
        sa.Column("provider_id", sa.String(64), nullable=False, index=True),
        sa.Column("prompt_md", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.String(32),
            nullable=False,
            server_default="drafting",
        ),
        sa.Column(
            "source_draft_json", sa.Text(), nullable=False, server_default="{}"
        ),
        sa.Column("error_message", sa.Text()),
        sa.Column(
            "llm_model", sa.String(120), nullable=False, server_default=""
        ),
        sa.Column(
            "llm_tokens_used", sa.Integer(), server_default=sa.text("0")
        ),
        sa.Column(
            "llm_cost",
            sa.Float(),
            nullable=False,
            server_default=sa.text("0.0"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("agent_drafts")
    op.drop_table("llm_providers")
