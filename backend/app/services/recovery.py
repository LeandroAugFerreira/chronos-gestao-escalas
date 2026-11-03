"""Local SQLite copies; restore only into a new directory, never over a live DB."""
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import sqlite3
from uuid import uuid4
from sqlalchemy import select, update
from app.core.config import PROJECT_ROOT, Settings
from app.core.database import build_engine, session_factory
from app.models import entities as m
from app.services.audit import audit

FORMAT = "chronos-sqlite-backup-1.0"
SUPPORTED_HEADS = {"009_automations", "010_pattern_revision"}


def outside_sync(path):
    path = Path(path).resolve()
    if path.is_relative_to(PROJECT_ROOT) or "onedrive" in str(path).lower():
        raise ValueError("Backup e recuperação devem ficar fora do projeto e OneDrive")
    return path


def file_sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_copy(path):
    with sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True) as db:
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok" or db.execute("PRAGMA foreign_key_check").fetchone():
            raise ValueError("Cópia sem integridade verificável")
        head = db.execute("SELECT version_num FROM alembic_version").fetchone()[0]
        if head not in SUPPORTED_HEADS:
            raise ValueError("Schema não suportado por esta versão de recuperação")
        counts = {name: db.execute('SELECT count(*) FROM "' + name + '"').fetchone()[0] for name in
            ["employees", "departments", "scenario_versions", "financial_runs", "optimization_runs", "schedule_versions", "schedule_decisions", "audit_logs"]}
    return {"schema": head, "integrity": "ok", "counts": counts}


def backup_sqlite(source, directory):
    source, directory = outside_sync(source), outside_sync(directory)
    if not source.is_file():
        raise ValueError("Banco de origem inexistente")
    directory.mkdir(parents=True, exist_ok=True)
    stem = "chronos-1.0-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:12]
    target = directory / (stem + ".sqlite3")
    with target.open("xb"):
        pass
    with sqlite3.connect(source.as_uri() + "?mode=ro", uri=True) as original, sqlite3.connect(target) as copy:
        original.backup(copy)
    result = {"format": FORMAT, "created_at": datetime.now(UTC).isoformat(), "sha256": file_sha(target), **inspect_copy(target)}
    manifest = directory / (stem + ".json")
    with manifest.open("x", encoding="utf-8") as output:
        json.dump(result, output, ensure_ascii=False, indent=2)
    return {"backup": str(target), "manifest": str(manifest), **result}


def quiesce_restored_copy(session):
    """Call only on a separately created restoration, before starting services."""
    stamp = m.now()
    changes = {}
    changes["sessions_revoked"] = session.execute(update(m.RefreshSession).where(m.RefreshSession.revoked_at.is_(None)).values(revoked_at=stamp)).rowcount
    changes["credentials_disabled"] = session.execute(update(m.IntegrationCredential).where(m.IntegrationCredential.enabled.is_(True)).values(enabled=False, revision=m.IntegrationCredential.revision + 1)).rowcount
    changes["automations_disabled"] = session.execute(update(m.AutomationDefinition).where(m.AutomationDefinition.enabled.is_(True)).values(enabled=False, next_run_at=None, revision=m.AutomationDefinition.revision + 1)).rowcount
    for model in [m.OptimizationRun, m.OutboxEvent, m.WebhookDelivery]:
        values = {"state": "cancelled", "lease_token": None, "lease_until": None, "finished_at": stamp,
            "error_code": "RESTORED_REQUIRES_REVIEW", "revision": model.revision + 1}
        if model is m.OptimizationRun:
            values["cancel_requested"] = True
        changes[model.__tablename__ + "_cancelled"] = session.execute(update(model).where(model.state.in_(["queued", "running"])).values(**values)).rowcount
    changes["interrupted_executions"] = session.execute(update(m.AutomationExecution).where(m.AutomationExecution.state == "running").values(
        state="failed", finished_at=stamp, error_code="RESTORED_INTERRUPTED")).rowcount
    for org in session.scalars(select(m.Organization.id)):
        audit(session, org, None, "recovery.restore", "organizations", org, details=changes)
    return changes


def restore_isolated(backup, manifest, directory):
    backup, manifest, directory = outside_sync(backup), outside_sync(manifest), outside_sync(directory)
    if not backup.is_file() or not manifest.is_file() or manifest.stat().st_size > 65536:
        raise ValueError("Arquivos de backup inválidos")
    info = json.loads(manifest.read_text(encoding="utf-8"))
    if info.get("format") != FORMAT or info.get("sha256") != file_sha(backup):
        raise ValueError("Hash ou formato de backup divergente")
    checked = inspect_copy(backup)
    if checked["counts"] != info.get("counts") or checked["schema"] != info.get("schema"):
        raise ValueError("Manifest não corresponde ao banco")
    directory.mkdir(parents=True, exist_ok=False)  # Never overwrite any existing directory or database.
    target = directory / "chronos-restored.sqlite3"
    with sqlite3.connect(backup.as_uri() + "?mode=ro", uri=True) as original, sqlite3.connect(target) as copy:
        original.backup(copy)
    engine = build_engine(Settings(_env_file=None, database_url="sqlite+pysqlite:///" + target.as_posix(), allow_sqlite=True, environment="test"))
    try:
        with session_factory(engine).begin() as session:
            changes = quiesce_restored_copy(session)
    finally:
        engine.dispose()
    return {"restored": str(target), "source_sha256": info["sha256"], "restored_sha256": file_sha(target),
        "safety_changes": changes, **inspect_copy(target)}
