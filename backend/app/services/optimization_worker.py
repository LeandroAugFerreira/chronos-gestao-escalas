"""Persistent local queue with lease fencing and a separately bounded solver process."""
import json
import os
import platform
import subprocess
import sys
import tempfile
from contextlib import ExitStack
from datetime import timedelta
from pathlib import Path
from time import monotonic, sleep
from uuid import uuid4
from sqlalchemy import and_, func, or_, select, update
from app.models.entities import OptimizationRun, ScheduleVersion, now
from app.core.config import PROJECT_ROOT
from app.services.audit import audit
from app.services.optimization_snapshot import signed
from app.services.organization_lock import lock_organization

LEASE_SECONDS = 30
MAX_ATTEMPTS = 3


def solver_environment():
    # Pass only runtime variables, so integration/test credentials cannot be inherited.
    allowed = {"PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "USERPROFILE", "HOME", "HOMEDRIVE", "HOMEPATH",
        "LOCALAPPDATA", "APPDATA", "PROGRAMFILES", "PROGRAMFILES(X86)", "COMMONPROGRAMFILES", "VIRTUAL_ENV",
        "LANG", "LC_ALL", "LC_CTYPE", "PYTHONUTF8", "PYTHONIOENCODING", "PYTHONDONTWRITEBYTECODE"}
    return {k: v for k, v in os.environ.items() if k.upper() in allowed}


def claim(factory):
    with factory() as session:
        stamp = now()
        eligible = or_(OptimizationRun.state == "queued", and_(OptimizationRun.state == "running", OptimizationRun.lease_until < stamp))
        row = session.scalar(select(OptimizationRun).where(eligible).order_by(OptimizationRun.created_at, OptimizationRun.id).limit(1))
        if row is None:
            return None
        ident, org = row.id, row.organization_id
        lock_organization(session, org)
        session.refresh(row)
        if row.state not in {"queued", "running"} or row.state == "running" and row.lease_until is not None and _aware(row.lease_until) >= stamp:
            return None
        if row.cancel_requested or row.attempts >= MAX_ATTEMPTS:
            row.state = "cancelled" if row.cancel_requested else "failed"
            row.error_code = None if row.cancel_requested else "LEASE_RETRIES_EXHAUSTED"
            row.finished_at = stamp; row.lease_token = None; row.lease_until = None; row.revision += 1
            session.commit()
            return {"skipped": True, "id": ident}
        token = str(uuid4())
        row.state = "running"; row.attempts += 1; row.revision += 1
        row.lease_token = token; row.lease_until = stamp + timedelta(seconds=LEASE_SECONDS)
        row.heartbeat_at = stamp; row.started_at = row.started_at or stamp
        task = {"id": ident, "organization_id": org, "token": token, "snapshot": row.snapshot, "seconds": row.inputs["seconds"]}
        audit(session, org, None, "optimization.claim", row.__tablename__, ident, details={"attempt": row.attempts})
        session.commit()
        return task


def _aware(value):
    from datetime import UTC
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def heartbeat(factory, task):
    with factory() as session:
        stamp = now()
        affected = session.execute(update(OptimizationRun).where(OptimizationRun.id == task["id"],
            OptimizationRun.organization_id == task["organization_id"], OptimizationRun.state == "running",
            OptimizationRun.lease_token == task["token"], OptimizationRun.cancel_requested.is_(False), OptimizationRun.lease_until > stamp)
            .values(heartbeat_at=stamp, lease_until=stamp + timedelta(seconds=LEASE_SECONDS)))
        session.commit()
        return affected.rowcount == 1


def finish(factory, task, secret, result=None, error=None):
    with factory() as session:
        lock_organization(session, task["organization_id"])
        row = session.get(OptimizationRun, task["id"])
        if row is None or row.state != "running" or row.lease_token != task["token"] or _aware(row.lease_until) <= now():
            return False
        if row.cancel_requested:
            row.state = "cancelled"
        elif error:
            row.state = "failed"; row.error_code = error
        else:
            row.state = "succeeded"; row.result = result
            if result.get("solver_status") in {"OPTIMAL", "FEASIBLE"} and result.get("verification", {}).get("valid"):
                parent = session.get(ScheduleVersion, row.inputs["parent_schedule_id"]) if row.inputs["parent_schedule_id"] else None
                series = parent.series_id if parent else str(uuid4())
                version = (session.scalar(select(func.max(ScheduleVersion.version)).where(ScheduleVersion.organization_id == row.organization_id, ScheduleVersion.series_id == series)) or 0) + 1
                payload = {"assignments": result["assignments"], "input_digest": row.input_digest,
                    "start_date": row.inputs["start_date"], "end_date": row.inputs["end_date"], "algorithm_version": result["algorithm_version"]}
                proposal = ScheduleVersion(organization_id=row.organization_id, unit_id=row.unit_id, run_id=row.id,
                    parent_id=parent.id if parent else None, series_id=series, version=version, name=row.name, payload=payload,
                    verification={**result["verification"], "approval_blockers": result["approval_blockers"]}, digest=signed(payload, secret))
                session.add(proposal); session.flush()
                audit(session, row.organization_id, None, "schedule.propose", proposal.__tablename__, proposal.id, details={"version": version, "digest": proposal.digest})
        row.finished_at = now(); row.lease_token = None; row.lease_until = None; row.revision += 1
        audit(session, row.organization_id, None, "optimization." + row.state, row.__tablename__, row.id,
            details={"solver_status": (result or {}).get("solver_status"), "error_code": row.error_code})
        session.commit()
        return True


def work_once(factory, settings, runtime_dir, stop_event=None):
    if stop_event is not None and stop_event.is_set():
        return False
    task = claim(factory)
    if not task or task.get("skipped"):
        return bool(task)
    directory = Path(runtime_dir).resolve()
    project = PROJECT_ROOT
    if directory == project or project in directory.parents:
        raise ValueError("Runtime do worker deve ficar fora da árvore do projeto sincronizado")
    directory.mkdir(parents=True, exist_ok=True)
    environment = solver_environment()
    child = None
    error, result = None, None
    try:
        with ExitStack() as stack, tempfile.TemporaryFile(dir=directory) as source, tempfile.TemporaryFile(dir=directory) as output, tempfile.TemporaryFile(dir=directory) as errors:
            source.write(json.dumps(task["snapshot"]).encode()); source.seek(0)
            frozen = getattr(sys, "frozen", False)
            if frozen:
                for key in ("_PYI_APPLICATION_HOME_DIR", "_PYI_ARCHIVE_FILE", "_PYI_PARENT_PROCESS_LEVEL"):
                    if key in os.environ:
                        environment[key] = os.environ[key]
                job = Path(stack.enter_context(tempfile.TemporaryDirectory(dir=directory)))
                incoming, outgoing = job / "input.json", job / "output.json"
                incoming.write_text(json.dumps(task["snapshot"]), encoding="utf-8")
                command = [sys.executable, "--chronos-solver", str(incoming), str(outgoing)]
            else:
                command = [sys.executable, str(project / "backend" / "scripts" / "solver_child.py")]
            child = subprocess.Popen(command,
                cwd=project / "backend", stdin=subprocess.DEVNULL if frozen else source, stdout=subprocess.DEVNULL if frozen else output, stderr=errors, env=environment,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            started, last = monotonic(), monotonic()
            while child.poll() is None:
                if stop_event is not None and stop_event.is_set():
                    error = "WORKER_SHUTDOWN"; child.kill(); break
                if monotonic() - started > task["seconds"] + 30:
                    error = "WORKER_TIMEOUT"; child.kill(); break
                if monotonic() - last >= 2:
                    last = monotonic()
                    if not heartbeat(factory, task):
                        error = "LEASE_LOST_OR_CANCELLED"; child.kill(); break
                sleep(0.1)
            child.wait(timeout=10)
            if frozen and outgoing.is_file():
                with outgoing.open("rb") as stream:
                    raw = stream.read(16000001)
            else:
                output.seek(0)
                raw = output.read(16000001)
            if not error:
                if child.returncode or len(raw) > 16000000:
                    error = "WORKER_FAILED"
                else:
                    envelope = json.loads(raw)
                    error = envelope.get("error_code"); result = envelope.get("result")
                    if not error and not isinstance(result, dict):
                        error = "INVALID_WORKER_RESULT"
                    if result is not None:
                        result["hardware"] = {"system": platform.system(), "machine": platform.machine(), "logical_cpus": os.cpu_count()}
    except (OSError, ValueError, subprocess.SubprocessError):
        error = "WORKER_FAILED"
    finally:
        if child and child.poll() is None:
            child.kill(); child.wait(timeout=10)
    finish(factory, task, settings.jwt_secret.get_secret_value(), result, error)
    return True
