from loguru import logger
from sqlalchemy import engine_from_config, pool

from alembic import context

from app.utils.config import Config, load_config


def _load_runtime_config() -> Config:
    """读取 Alembic -x 自定义参数，根据指定路径加载配置文件。
    当 -x config=<path> 存在时仅从 app.utils.config 加载，不依赖 config.yaml；
    否则使用 app.core.config 的 global_config_loaded_from_config_yaml（需 config.yaml 存在）。
    """
    x_args = context.get_x_argument(as_dictionary=True)
    config_path = x_args.get("config", None)
    if config_path:
        logger.info(f"[ALEMBIC] 使用自定义配置文件: {config_path}")
        return load_config(config_path)
    logger.info("[ALEMBIC] 使用默认配置文件: config.yaml")
    from app.core.config import global_config_loaded_from_config_yaml

    return global_config_loaded_from_config_yaml


runtime_config = _load_runtime_config()

# 导入所有模型，app/models/__init__.py 会将所有表定义连同 base 一起导入
from app.models import Base

target_metadata = Base.metadata
db_url = runtime_config.database.url
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
