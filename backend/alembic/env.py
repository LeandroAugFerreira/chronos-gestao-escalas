from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

from app.core.config import Settings
from app.core.database import build_engine
from app.models.entities import Base

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata
override = config.attributes.get("connection")


def run(connection):
    context.configure(connection=connection, target_metadata=target_metadata,
                      compare_type=True, render_as_batch=connection.dialect.name == "sqlite")
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    url = config.attributes.get("database_url") or Settings().database_url.get_secret_value()
    if not url:
        raise ValueError("Configure DATABASE_URL antes de executar Alembic")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()
elif override is not None:
    run(override)
else:
    engine = build_engine(Settings())
    if engine is None:
        raise ValueError("Configure DATABASE_URL antes de executar Alembic")
    with engine.connect() as connection:
        run(connection)
    engine.dispose()
