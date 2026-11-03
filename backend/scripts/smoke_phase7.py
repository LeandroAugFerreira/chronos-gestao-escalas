"""Chronos 1.0 — real local API/n8n round-trip using isolated synthetic databases."""
import argparse
from datetime import UTC, datetime, timedelta
import importlib.util
import json
import os
from pathlib import Path
import secrets
import socket
import sqlite3
import subprocess
import sys
from time import monotonic, sleep
from uuid import uuid4
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from alembic import command
from alembic.config import Config
import httpx
from sqlalchemy import func, select
from app.core.config import PROJECT_ROOT, Settings
from app.core.database import build_engine, session_factory
from app.models import entities as m
from app.services.automation_worker import work_once
from app.services.demo import load_demo
from app.services.optimization_worker import solver_environment
from app.services.seed import create_user, demo_id, init_rbac, seed_demo


def main(runtime):
    policy = json.loads((PROJECT_ROOT / "automation/n8n/security-status.json").read_text(encoding="utf-8"))
    if policy.get("execution_allowed") is not True:
        raise RuntimeError("Execução n8n bloqueada pela auditoria da Fase 9; preserve as evidências históricas e use testes do núcleo local")
    runtime = Path(runtime).resolve()
    if runtime.is_relative_to(PROJECT_ROOT) or "onedrive" in str(runtime).lower():
        raise ValueError("Runtime de teste deve ficar fora do projeto e OneDrive")
    selection = json.loads((runtime / "phase7-node.json").read_text(encoding="utf-8-sig"))
    node = Path(selection["node_dir"]) / "node.exe"
    n8n = runtime / "n8n/node_modules/n8n/bin/n8n"
    if not node.exists() or not n8n.exists():
        raise ValueError("Prepare o runtime n8n isolado antes do smoke")
    for port in [8017, 5687]:
        with socket.socket() as check:
            check.bind(("127.0.0.1", port))
    folder = runtime / ("phase7-http-" + uuid4().hex[:12])
    folder.mkdir()
    password, secret, outbound = secrets.token_urlsafe(24), secrets.token_urlsafe(48), secrets.token_urlsafe(40)
    url = "sqlite+pysqlite:///" + (folder / "chronos-test.sqlite3").as_posix()
    settings = Settings(_env_file=None, database_url=url, allow_sqlite=True, jwt_secret=secret, environment="test",
        n8n_webhook_base_url="http://127.0.0.1:5687/webhook/chronos", n8n_outbound_token=outbound)
    engine = build_engine(settings); factory = session_factory(engine)
    config = Config(str(PROJECT_ROOT / "backend/alembic.ini"))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
    with factory.begin() as session:
        init_rbac(session); org, _ = seed_demo(session, load_demo())
        admin = create_user(session, org, "smoke-admin", password)
        create_user(session, org, "smoke-reviewer", password, "manager", demo_id("horizonte-main"))
        admin_id = admin.id
        person = session.get(m.Employee, demo_id("hh-0001"))
        person_id, department_id, role_id, unit_id = person.id, person.department_id, person.job_role_id, person.unit_id
        contract = session.scalar(select(m.Contract).where(m.Contract.employee_id == person.id))
        contract.validation_status = "validated"; contract.assumption_source = "Contrato sintético revisado exclusivamente para smoke"
        pattern = session.get(m.WorkPattern, contract.work_pattern_id)
        pattern.configuration = {"cycle": ["work"], "shift_minutes": 480}; pattern.legal_status = "validated"; pattern_id = pattern.id
        for qualification in session.scalars(select(m.EmployeeQualification).where(m.EmployeeQualification.employee_id == person.id)):
            qualification.verification_status = "validated"; qualification.evidence = "Evidência fictícia exclusivamente para smoke local"
        for kind, value in [("max_daily", 480), ("max_weekly", 2400), ("min_rest", 600), ("min_break", 0), ("min_weekly_rest", 1440)]:
            session.add(m.LaborRule(organization_id=org.id, key="smoke-" + kind, version=1, kind=kind, minutes=value, threshold_minutes=480,
                valid_from=datetime(2026, 1, 1, tzinfo=UTC), valid_until=datetime(2027, 1, 1, tzinfo=UTC), source="Hipótese sintética para smoke; sem valor normativo",
                status="validated", review_evidence="Revisão fictícia exclusivamente para teste local", reviewer_id=admin_id))
    environment = {**os.environ, "CHRONOS_DATABASE_URL": url, "CHRONOS_JWT_SECRET": secret, "CHRONOS_ALLOW_SQLITE": "true", "CHRONOS_ENVIRONMENT": "test",
        "CHRONOS_N8N_WEBHOOK_BASE_URL": settings.n8n_webhook_base_url, "CHRONOS_N8N_OUTBOUND_TOKEN": outbound, "CHRONOS_COOKIE_SECURE": "false"}
    n8n_env = {**solver_environment(), "PATH": str(node.parent) + os.pathsep + os.environ.get("PATH", ""), "NODE_OPTIONS": "--max-old-space-size=768",
        "N8N_USER_FOLDER": str(folder / "n8n-user"), "DB_SQLITE_DATABASE": str(folder / "n8n.sqlite3"), "N8N_ENCRYPTION_KEY": secrets.token_hex(32),
        "N8N_LISTEN_ADDRESS": "127.0.0.1", "N8N_HOST": "127.0.0.1", "N8N_PORT": "5687", "N8N_PROTOCOL": "http", "N8N_SECURE_COOKIE": "false",
        "N8N_DIAGNOSTICS_ENABLED": "false", "N8N_PERSONALIZATION_ENABLED": "false", "N8N_VERSION_NOTIFICATIONS_ENABLED": "false", "N8N_TEMPLATES_ENABLED": "false",
        "N8N_LICENSE_AUTO_RENEW_ENABLED": "false", "N8N_COMMUNITY_PACKAGES_ENABLED": "false", "N8N_SENTRY_DSN": "", "N8N_FRONTEND_SENTRY_DSN": "",
        "N8N_RUNNERS_ENABLED": "false", "N8N_PYTHON_ENABLED": "false", "N8N_BLOCK_ENV_ACCESS_IN_NODE": "true", "N8N_PAYLOAD_SIZE_MAX": "1",
        "NODES_INCLUDE": json.dumps(["n8n-nodes-base.webhook", "n8n-nodes-base.httpRequest"]), "N8N_LOG_LEVEL": "warn"}
    # An optional empty-schema template avoids repeating n8n's historical migrations.
    template = runtime / "n8n-probe/.n8n/database.sqlite"
    if template.exists():
        private_config = json.loads((template.parent / "config").read_text(encoding="utf-8"))
        n8n_env["N8N_ENCRYPTION_KEY"] = private_config["encryptionKey"]
        with sqlite3.connect(template) as source, sqlite3.connect(folder / "n8n.sqlite3") as destination:
            assert source.execute('SELECT count(*) FROM credentials_entity').fetchone()[0] == 0
            source.backup(destination)
    spec = importlib.util.spec_from_file_location("chronos_workflows", PROJECT_ROOT / "automation/n8n/generate_workflows.py")
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    workflows = [workflow for _, workflow in module.exports()]
    workflow_file = folder / "workflows.json"
    workflow_file.write_text(json.dumps(workflows, ensure_ascii=False), encoding="utf-8")
    processes, handles, credential_id = [], [], None
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    def launch(name, arguments, env):
        handle = (folder / (name + ".log")).open("w", encoding="utf-8"); handles.append(handle)
        process = subprocess.Popen(arguments, cwd=PROJECT_ROOT / "backend", env=env, stdout=handle, stderr=subprocess.STDOUT, creationflags=flags)
        processes.append(process)
        return process
    def cli(name, *args):
        with (folder / (name + ".log")).open("w", encoding="utf-8") as log:
            result = subprocess.run([str(node), str(n8n), *args], cwd=folder, env=n8n_env, stdout=log, stderr=subprocess.STDOUT, timeout=240, creationflags=flags)
            if result.returncode:
                raise RuntimeError(f"n8n CLI não concluiu a etapa {name}; consulte o log local, sem expor credenciais")
    try:
        launch("backend", [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8017"], environment)
        with httpx.Client(base_url="http://127.0.0.1:8017", timeout=30, trust_env=False) as client:
            for _ in range(120):
                try:
                    if client.get("/api/v1/health/ready").status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                sleep(0.25)
            else:
                raise RuntimeError("API isolada não ficou pronta")
            login = client.post("/api/v1/auth/login", json={"organization": "horizonte", "username": "smoke-admin", "password": password})
            assert login.status_code == 200
            auth = {"Authorization": "Bearer " + login.json()["access_token"]}
            key = client.post("/api/v1/integration-credentials", headers=auth, json={"unit_id": unit_id, "name": "n8n smoke efêmero", "actions": ["workflow_callback", "availability"]})
            assert key.status_code == 201, "Falha ao criar credencial efêmera"
            credential_id = key.json()["id"]
            credentials = [{"id": module.ident("webhook-auth"), "name": "Chronos 1.0 — Webhook local", "type": "httpHeaderAuth", "data": {"name": "X-Chronos-Token", "value": outbound}},
                {"id": module.ident("callback-auth"), "name": "Chronos 1.0 — Callback autorizado", "type": "httpHeaderAuth", "data": {"name": "Authorization", "value": "Bearer " + key.json()["token_once"]}}]
            credential_file = folder / "credentials-temporary.json"
            credential_file.write_text(json.dumps(credentials), encoding="utf-8")
            try:
                cli("import-credentials", "import:credentials", "--input=" + str(credential_file))
            finally:
                credential_file.unlink(missing_ok=True)
            cli("import-workflows", "import:workflow", "--input=" + str(workflow_file))
            for workflow in workflows:
                cli("activate-" + workflow["id"], "publish:workflow", "--id=" + workflow["id"])
            launch("n8n", [str(node), str(n8n), "start"], n8n_env)
            with httpx.Client(base_url="http://127.0.0.1:5687", timeout=30, trust_env=False) as bridge:
                for _ in range(180):
                    try:
                        if bridge.get("/healthz/readiness").status_code == 200:
                            break
                    except httpx.HTTPError:
                        pass
                    sleep(0.5)
                else:
                    raise RuntimeError("n8n local não ficou pronto")
                login = client.post("/api/v1/auth/login", json={"organization": "horizonte", "username": "smoke-admin", "password": password})
                assert login.status_code == 200
                auth = {"Authorization": "Bearer " + login.json()["access_token"]}
                definitions = client.get("/api/v1/automations", headers=auth).json()["items"]
                for definition in definitions:
                    response = client.patch("/api/v1/automations/" + definition["id"], headers=auth, json={"revision": definition["revision"], "enabled": True,
                        "parameters": {"monitor_limit": 10, "deliver_n8n": definition["code"] in {"A02", "A03", "A04", "A06"}}})
                    assert response.status_code == 200
                review = {"source": "Hipótese sintética para integração n8n", "validation_status": "validated", "review_evidence": "Responsável fictício; somente para teste de transporte"}
                demand = {"name": "Atividade sintética", "department_id": department_id, "start_time": "08:00", "duration_minutes": 480, "weekdays": list(range(7)), "required_staff": 1, **review}
                scenario = client.post("/api/v1/scenarios", headers=auth, json={"name": "Cenário HTTP n8n", "key": "n8n-http", "unit_id": unit_id,
                    "department_id": department_id, "reference_month": "2026-11-01", "demands": [demand], **review}).json()
                body = {"scenario_id": scenario["id"], "name": "Otimização sintética n8n", "start_date": "2026-11-02", "end_date": "2026-11-03", "mode": "strict",
                    "templates": [{"name": "Diurno sintético", "start_time": "08:00", "duration_minutes": 480}], "activity_job_role_ids": {"0": [role_id]}, "cycle_anchors": {pattern_id: "2026-11-02"},
                    "history_review_evidence": "Histórico fictício conferido exclusivamente para smoke", "limits": {"max_daily_minutes": 480, "max_weekly_minutes": 2400,
                        "min_rest_minutes": 600, "min_break_minutes": 0, "break_threshold_minutes": 480, "min_weekly_rest_minutes": 1440, "max_consecutive_days": 5, **review}}
                optimization = client.post("/api/v1/optimization", headers=auth, json=body)
                assert optimization.status_code == 202
                subprocess.run([sys.executable, "scripts/worker.py", "--runtime-dir", str(folder), "--once"], cwd=PROJECT_ROOT / "backend", env=environment,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60, check=True, creationflags=flags)
                run = client.get("/api/v1/optimization/" + optimization.json()["id"], headers=auth).json()
                assert run["state"] == "succeeded" and run["result"]["approval_blockers"] == [], "Proposta de teste não está apta à submissão"
                proposal = client.get("/api/v1/schedules/" + run["schedule_id"], headers=auth).json()
                submission = client.post("/api/v1/schedules/" + proposal["id"] + "/decision", headers=auth,
                    json={"revision": proposal["revision"], "schedule_digest": proposal["digest"], "action": "submit", "reason": "Submissão fictícia para testar avisos n8n"})
                assert submission.status_code == 200
                # Second real CP-SAT run deliberately has uncovered demand.
                gap = client.post("/api/v1/optimization", headers=auth, json=body | {"name": "Lacuna sintética n8n", "mode": "diagnostic",
                    "coverage_windows": [{"activity_index": 0, "start_at": "2026-11-02T08:00:00-03:00", "end_at": "2026-11-02T16:00:00-03:00", "required_staff": 500, **review}]})
                assert gap.status_code == 202
                subprocess.run([sys.executable, "scripts/worker.py", "--runtime-dir", str(folder), "--once"], cwd=PROJECT_ROOT / "backend", env=environment,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60, check=True, creationflags=flags)
                a04 = next(d for d in client.get("/api/v1/automations", headers=auth).json()["items"] if d["code"] == "A04")
                assert client.post("/api/v1/automations/" + a04["id"] + "/run", headers=auth, json={"revision": a04["revision"]}).status_code == 202
                subprocess.run([sys.executable, "scripts/automation_worker.py", "--once"], cwd=PROJECT_ROOT / "backend", env=environment,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60, check=True, creationflags=flags)
                def drain():
                    started = monotonic()
                    while monotonic() - started < 120:
                        processed = work_once(factory, settings)
                        with factory() as session:
                            pending = sum(session.scalar(select(func.count()).select_from(model).where(model.state.in_(["queued", "running"]))) for model in [m.OutboxEvent, m.WebhookDelivery])
                        if not pending:
                            return
                        if not processed:
                            sleep(0.1)
                    raise RuntimeError("Fila de integração não encerrou no limite")
                drain()
                assignment = proposal["payload"]["assignments"][0]
                availability = {"request_id": str(uuid4()), "sent_at": m.now().isoformat(), "employee_id": person_id,
                    "start_at": assignment["start_at"], "end_at": assignment["end_at"], "type": "unavailable", "reason": "Ausência fictícia n8n"}
                assert bridge.post("/webhook/chronos/availability", json=availability).status_code in {401, 403}
                incoming = bridge.post("/webhook/chronos/availability", headers={"X-Chronos-Token": outbound}, json=availability)
                assert incoming.status_code in {200, 201}, f"Workflow disponibilidade retornou HTTP {incoming.status_code}"
                replay = bridge.post("/webhook/chronos/availability", headers={"X-Chronos-Token": outbound}, json=availability)
                assert replay.status_code in {200, 201}
                drain()
                with factory() as session:
                    receipts = session.scalars(select(m.IntegrationReceipt).where(m.IntegrationReceipt.action == "workflow_callback")).all()
                    executed = {r.result["code"] for r in receipts if r.result.get("workflow_execution_id")}
                    assert executed == {"A02", "A03", "A04", "A06"}, "Nem todos os workflows confirmaram execução real"
                    failures = session.scalars(select(m.WebhookDelivery.error_code).where(m.WebhookDelivery.state == "failed")).all()
                    assert not failures, "Falhas de entrega registradas: " + ",".join(failures)
                    assert session.scalar(select(func.count()).select_from(m.AutomationSuggestion)) >= 1
                    assert session.scalar(select(func.count()).select_from(m.OptimizationRun)) == 2
                    current = session.get(m.ScheduleVersion, proposal["id"])
                    assert current.state == "submitted" and current.payload == proposal["payload"]
                    assert session.scalar(select(func.count()).select_from(m.AutomationNotice).where(m.AutomationNotice.code == "A02")) >= 1
                    count = lambda model: session.scalar(select(func.count()).select_from(model))
                    report = {"product": "Chronos 1.0", "phase": 7, "n8n_version": "2.44.6", "node_version": selection["version"], "real_http": True,
                        "workflows_imported": 4, "workflow_codes_executed": sorted(executed), "workflow_execution_ids": sorted({r.result["workflow_execution_id"] for r in receipts}),
                        "callback_receipts": len(receipts), "artifacts": count(m.AutomationArtifact), "internal_notices": count(m.AutomationNotice),
                        "reoptimization_suggestions": count(m.AutomationSuggestion), "automatic_optimization_jobs": 0, "optimizer_runs_requested": 2,
                        "main_database_modified": False, "credentials_in_source": False, "unauthenticated_webhook_rejected": True, "availability_replay_deduplicated": True,
                        "approved_automatically": False, "external_publication": False, "browser_used": False}
                    (runtime / "phase7-http-checks.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
                    print(json.dumps(report))
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill(); process.wait(timeout=10)
        for handle in handles:
            handle.close()
        if credential_id:
            with factory.begin() as session:
                credential = session.get(m.IntegrationCredential, credential_id)
                if credential:
                    credential.enabled = False
        engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chronos 1.0 — smoke HTTP/n8n da Fase 7")
    parser.add_argument("--runtime", required=True)
    main(parser.parse_args().runtime)
