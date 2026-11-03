from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import PROJECT_ROOT, Settings


def build_engine(settings: Settings):
    value = settings.database_url.get_secret_value()
    if not value:
        return None
    url = make_url(value)
    if url.get_backend_name() not in {"postgresql", "sqlite"}:
        raise ValueError("Use PostgreSQL ou o perfil SQLite explicitamente habilitado")
    options = {"pool_pre_ping": True}
    if url.get_backend_name() == "sqlite":
        if not settings.allow_sqlite or settings.environment == "production":
            raise ValueError("SQLite exige CHRONOS_ALLOW_SQLITE=true em desenvolvimento/teste")
        if not url.database or url.database == ":memory:":
            raise ValueError("Use arquivo SQLite fora do projeto para verificar persistência")
        database = Path(url.database).resolve()
        if database.is_relative_to(PROJECT_ROOT) or "onedrive" in str(database).lower():
            raise ValueError("Banco ativo deve ficar fora do OneDrive e do projeto")
        database.parent.mkdir(parents=True, exist_ok=True)
        options["connect_args"] = {"check_same_thread": False, "timeout": 10}
    engine = create_engine(url, **options)
    if url.get_backend_name() == "sqlite":
        @event.listens_for(engine, "connect")
        def sqlite_integrity(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA busy_timeout=10000")
    return engine


def session_factory(engine):
    return sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
