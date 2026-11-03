"""Fresh per-install demo configuration; never copies a developer database or account."""
import json
import os
from pathlib import Path
import secrets

DEMO_USERNAME = "demo"
DEMO_PASSWORD = "ChronosDemo@2026"


def data_folder(value=None):
    from app.core.config import PROJECT_ROOT
    path = Path(value) if value else Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Chronos" / "1.0-demo"
    path = path.resolve()
    if path.is_relative_to(PROJECT_ROOT) or "onedrive" in str(path).lower():
        raise ValueError("Escolha uma pasta de dados fora do projeto, do executável e do OneDrive.")
    path.mkdir(parents=True, exist_ok=True)
    return path


def prepare(folder, origin):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import select
    from app.core.config import PROJECT_ROOT, Settings
    from app.core.database import build_engine, session_factory
    from app.models.entities import Organization, User
    from app.services.seed import init_rbac, seed_demo, create_user, demo_id
    from app.services.demo import load_demo
    from app.services.audit import audit

    config_file = folder / "settings.json"
    if not config_file.exists():
        with config_file.open("x", encoding="utf-8") as stream:
            json.dump({"schema": 1, "jwt_secret": secrets.token_urlsafe(48)}, stream)
    config = json.loads(config_file.read_text(encoding="utf-8"))
    assert config.get("schema") == 1 and len(config.get("jwt_secret", "")) >= 32
    # Drop inherited application credentials; only this process environment is changed.
    for key in list(os.environ):
        if key.upper().startswith("CHRONOS_") or key.upper() in {"DATABASE_URL", "JWT_SECRET"}:
            os.environ.pop(key, None)
    Settings.model_config["env_file"] = None
    settings = Settings(_env_file=None, database_url="sqlite+pysqlite:///" + (folder / "chronos-demo.sqlite3").as_posix(),
        jwt_secret=config["jwt_secret"], environment="development", allow_sqlite=True, allowed_origins=origin,
        cookie_secure=False, n8n_webhook_base_url="", n8n_outbound_token="")
    engine = build_engine(settings); factory = session_factory(engine)
    try:
        alembic = Config()
        alembic.set_main_option("script_location", str(PROJECT_ROOT / "backend/alembic"))
        with engine.begin() as connection:
            alembic.attributes["connection"] = connection
            command.upgrade(alembic, "head")
        with factory.begin() as session:
            init_rbac(session)
            org, _ = seed_demo(session, load_demo())
            if not session.scalar(select(User.id).where(User.organization_id == org.id, User.username == DEMO_USERNAME)):
                account = create_user(session, org, DEMO_USERNAME, DEMO_PASSWORD, "demo")
                audit(session, org.id, None, "auth.desktop_demo_created", "users", account.id)
        return settings
    finally:
        engine.dispose()


def has_administrator(factory):
    from sqlalchemy import select
    from app.models.entities import Role, UserRole
    from app.services.seed import demo_id
    with factory() as session:
        return session.scalar(select(UserRole.id).join(Role, UserRole.role_id == Role.id).where(
            UserRole.organization_id == demo_id("organization"), Role.name == "admin")) is not None


def create_administrator(factory, username, password):
    from app.models.entities import Organization
    from app.services.seed import create_user, demo_id
    from app.services.audit import audit
    from app.services.organization_lock import lock_organization
    with factory.begin() as session:
        org = session.get(Organization, demo_id("organization"))
        lock_organization(session, org.id)
        if has_administrator(factory):
            raise ValueError("Já existe administrador local. Crie novos acessos pela conta autorizada na plataforma.")
        user = create_user(session, org, username, password, "admin")
        audit(session, org.id, user.id, "auth.desktop_bootstrap", "users", user.id)
        return user.username
