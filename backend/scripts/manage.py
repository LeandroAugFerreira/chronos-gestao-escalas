"""Chronos 1.0 — operações locais explícitas, sem criar tabelas fora do Alembic."""

import argparse
import getpass
import json
import os
from pathlib import Path
import secrets
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from alembic import command
from alembic.config import Config
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import PROJECT_ROOT, Settings
from app.core.database import build_engine, session_factory
from app.models.entities import Organization, User
from app.services.demo import load_demo
from app.services.seed import create_user, demo_id, init_rbac, restore_demo, seed_demo
from app.services.audit import audit


def configure_local(runtime):
    target = PROJECT_ROOT / ".env"
    if target.exists():
        print("Chronos 1.0: .env existente preservado; confira a configuração antes de continuar.")
        return
    runtime = Path(runtime).resolve()
    if runtime.is_relative_to(PROJECT_ROOT) or "onedrive" in str(runtime).lower():
        raise ValueError("Runtime deve ficar fora do OneDrive e do projeto")
    runtime.mkdir(parents=True, exist_ok=True)
    database = (runtime / "chronos.sqlite3").as_posix()
    with target.open("x", encoding="utf-8") as stream:
        stream.write("# Chronos 1.0 — segredo local, não versionar\n"
            f"CHRONOS_DATABASE_URL=sqlite+pysqlite:///{database}\nCHRONOS_ALLOW_SQLITE=true\n"
            f"CHRONOS_JWT_SECRET={secrets.token_urlsafe(48)}\nCHRONOS_ENVIRONMENT=development\n"
            "CHRONOS_ALLOWED_ORIGINS=http://127.0.0.1:5187,http://localhost:5187\n")
    print("Chronos 1.0: configuração local criada; segredo não exibido. Banco fora do OneDrive.")


def main():
    parser = argparse.ArgumentParser(description="Chronos 1.0 — Fase 2")
    commands = parser.add_subparsers(dest="action", required=True)
    local = commands.add_parser("init-local")
    local.add_argument("--runtime", required=True)
    commands.add_parser("migrate")
    commands.add_parser("seed-demo")
    bootstrap = commands.add_parser("create-admin")
    bootstrap.add_argument("--username", default="admin")
    restore = commands.add_parser("restore-demo")
    restore.add_argument("--confirm", required=True)
    args = parser.parse_args()
    if args.action == "init-local":
        configure_local(args.runtime)
        return
    settings = Settings()
    engine = build_engine(settings)
    if engine is None:
        raise ValueError("Configure o banco antes de continuar")
    try:
        if args.action == "migrate":
            config = Config(str(PROJECT_ROOT / "backend/alembic.ini"))
            with engine.begin() as connection:
                config.attributes["connection"] = connection
                command.upgrade(config, "head")
            print("Chronos 1.0: migrations aplicadas.")
            return
        with session_factory(engine)() as session:
            with session.begin():
                init_rbac(session)
                if args.action == "restore-demo":
                    org = session.get(Organization, demo_id("organization"))
                    if org is None:
                        raise ValueError("Demonstração não encontrada")
                    restore_demo(session, org, args.confirm, settings.environment)
                if args.action in {"seed-demo", "restore-demo"}:
                    org, changed = seed_demo(session, load_demo())
                    print("Chronos 1.0: demonstração importada." if changed else "Chronos 1.0: fixture já importada; registros preservados.")
                elif args.action == "create-admin":
                    if not settings.jwt_secret.get_secret_value():
                        raise ValueError("Configure o segredo JWT antes de criar o administrador")
                    org = session.get(Organization, demo_id("organization"))
                    if org is None:
                        raise ValueError("Execute seed-demo antes de criar o administrador")
                    password = os.getenv("CHRONOS_BOOTSTRAP_PASSWORD") or getpass.getpass("Senha do administrador (mín. 12 caracteres): ")
                    if not password:
                        raise ValueError("Senha obrigatória")
                    user = create_user(session, org, args.username, password)
                    audit(session, org.id, user.id, "auth.bootstrap", "users", user.id)
                    print("Chronos 1.0: administrador criado. Nenhuma senha foi exibida ou salva em arquivo de credenciais.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    try:
        main()
    except ValueError as error:
        raise SystemExit(str(error)) from None
    except SQLAlchemyError:
        raise SystemExit("Operação não concluída. Verifique conexão, migrations e integridade dos dados; credenciais não foram exibidas.") from None
