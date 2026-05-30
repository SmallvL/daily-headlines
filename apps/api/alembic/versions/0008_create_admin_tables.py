"""create admin tables (groups, templates, push_subscriptions, audit_logs)

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-28
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers
revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add role column to users
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column("role", sa.String(32), nullable=False, server_default="user")
        )

    # User groups
    op.create_table(
        "user_groups",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(64), nullable=False, index=True),
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

    # User group members (many-to-many) — unique constraint inline
    op.create_table(
        "user_group_members",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "group_id",
            sa.String(64),
            sa.ForeignKey("user_groups.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("user_id", sa.String(64), nullable=False, index=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("group_id", "user_id", name="uq_group_member"),
    )

    # Source templates (public templates managed by admin)
    op.create_table(
        "source_templates",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("config_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(64), nullable=False, index=True),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Push subscriptions — unique constraint inline
    op.create_table(
        "push_subscriptions",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=False, index=True),
        sa.Column(
            "template_id",
            sa.String(64),
            sa.ForeignKey("source_templates.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "source_id",
            sa.String(64),
            sa.ForeignKey("sources.id"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "status",
            sa.String(32),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("pushed_by", sa.String(64), nullable=False),
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
        sa.UniqueConstraint(
            "user_id", "template_id", name="uq_push_subscription"
        ),
    )

    # Audit logs
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("actor_id", sa.String(64), nullable=False, index=True),
        sa.Column("action", sa.String(64), nullable=False, index=True),
        sa.Column("resource_type", sa.String(64), nullable=False, index=True),
        sa.Column("resource_id", sa.String(64), nullable=True),
        sa.Column("details_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("push_subscriptions")
    op.drop_table("source_templates")
    op.drop_table("user_group_members")
    op.drop_table("user_groups")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("role")
