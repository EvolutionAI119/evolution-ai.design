"""Alembic 迁移环境：连接串取自应用配置 settings.DATABASE_URL。

- 导入 app.database 即注册全部 ORM 模型到 Base.metadata（模型为单文件定义）
- 全新库建表：python -m alembic upgrade head
- 既有库补登记：python -m alembic stamp head
"""
from logging.config import fileConfig

from alembic import context

from app.config import settings
from app.database import Base
import app.database  # noqa: F401  确保全部 ORM 模型已注册

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """离线模式：仅生成 SQL 脚本，不连数据库"""
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线模式：直连数据库执行迁移"""
    from sqlalchemy import engine_from_config, pool

    # alembic.ini 中 url 为占位，运行时以应用配置覆盖（保持单一配置来源）
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = settings.DATABASE_URL
    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
