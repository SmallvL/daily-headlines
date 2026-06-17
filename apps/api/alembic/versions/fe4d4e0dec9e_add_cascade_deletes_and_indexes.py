"""add cascade deletes and indexes

Revision ID: fe4d4e0dec9e
Revises: 0017
Create Date: 2026-06-17 06:02:59.796659
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'fe4d4e0dec9e'
down_revision: Union[str, None] = '0017'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("PRAGMA legacy_alter_table=ON")

    with op.batch_alter_table('feed_items', recreate='always') as batch_op:
        batch_op.create_foreign_key('fk_feed_items_source', 'sources', ['source_id'], ['id'], ondelete='CASCADE')

    with op.batch_alter_table('source_fetch_logs', recreate='always') as batch_op:
        batch_op.create_foreign_key('fk_source_fetch_logs_source', 'sources', ['source_id'], ['id'], ondelete='CASCADE')

    with op.batch_alter_table('subscriptions', recreate='always') as batch_op:
        batch_op.create_foreign_key('fk_subscriptions_source', 'sources', ['source_id'], ['id'], ondelete='CASCADE')

    with op.batch_alter_table('user_item_states', recreate='always') as batch_op:
        batch_op.create_foreign_key('fk_user_item_states_item', 'feed_items', ['item_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    op.execute("PRAGMA legacy_alter_table=ON")

    with op.batch_alter_table('user_item_states', recreate='always') as batch_op:
        batch_op.create_foreign_key('fk_user_item_states_item', 'feed_items', ['item_id'], ['id'])

    with op.batch_alter_table('subscriptions', recreate='always') as batch_op:
        batch_op.create_foreign_key('fk_subscriptions_source', 'sources', ['source_id'], ['id'])

    with op.batch_alter_table('source_fetch_logs', recreate='always') as batch_op:
        batch_op.create_foreign_key('fk_source_fetch_logs_source', 'sources', ['source_id'], ['id'])

    with op.batch_alter_table('feed_items', recreate='always') as batch_op:
        batch_op.create_foreign_key('fk_feed_items_source', 'sources', ['source_id'], ['id'])
