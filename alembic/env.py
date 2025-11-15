import logging
import os

from sqlalchemy import engine_from_config, pool

from alembic import context

CONFIG_PATH_ENV_VAR = "INTY_CONFIG_PATH"
CONFIG_OVERRIDE_KEYS = (
    "config",
    "config_file",
    "config-file",
    "config_path",
    "config-path",
    "app_config",
    "app-config",
)
logger = logging.getLogger("alembic.env")


def _apply_app_config_override_from_cli() -> None:
    x_args = context.get_x_argument(as_dictionary=True)
    if not isinstance(x_args, dict):
        return

    for key in CONFIG_OVERRIDE_KEYS:
        override_path = x_args.get(key)
        if not override_path:
            continue

        os.environ[CONFIG_PATH_ENV_VAR] = override_path
        logger.info("Using app config file override from -x %s=%s", key, override_path)
        break


_apply_app_config_override_from_cli()

from app.core.config import global_config_loaded_from_config_yaml

# 导入所有模型，app/models/__init__.py 会将所有表定义连同 base 一起导入
from app.models import Base

target_metadata = Base.metadata
db_url = global_config_loaded_from_config_yaml.database.url
# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config
# 设置数据库URL
config.set_main_option("sqlalchemy.url", db_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
