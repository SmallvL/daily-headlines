from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from app.core.config import settings
from app.core.database import Base
from app.modules.admin.models import (
    AuditLog,
    PushSubscription,
    SourceTemplate,
    UserGroup,
    UserGroupMember,
)
from app.modules.agent.models import AgentDraft, LlmProvider
from app.modules.agent_tokens.models import AgentToken
from app.modules.feed.models import FeedItem, UserItemState
from app.modules.preferences.models import UserPreference
from app.modules.search.models import SavedSearch
from app.modules.sources.models import Source, Subscription
from app.modules.users.models import User

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()


_ = User
_ = Source
_ = Subscription
_ = FeedItem
_ = UserItemState
_ = SavedSearch
