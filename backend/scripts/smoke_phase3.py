"""Chronos 1.0: integração HTTP API/proxy/cookies, sem navegador ou dados reais.

Cria DB de teste independente, contas efêmeras, inicia servidores próprios em loopback
e os encerra em finally. Não modifica o banco local configurado no .env.
"""

from pathlib import Path
import argparse
import json
import os
import secrets
import socket
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from alembic import command
from alembic.config import Config
import httpx

from app.core.config import PROJECT_ROOT, Settings
from app.core.database import build_engine, session_factory
from app.services.demo import load_demo
from app.services.seed import create_user, demo_id, init_rbac, seed_demo


def main(runtime, phase=3):
    runtime = Path(runtime).resolve()
    if runtime.is_relative_to(PROJECT_ROOT) or "onedrive" in str(runtime).lower():
        raise ValueError("Use runtime fora do projeto e OneDrive")
    runtime.mkdir(parents=True, exist_ok=True)
    database = runtime / (f"http-phase{phase}-" + secrets.token_hex(6) + ".sqlite3")
    secret = secrets.token_urlsafe(48)
    password = secrets.token_urlsafe(24)
    value = "sqlite+pysqlite:///" + database.as_posix()
    settings = Settings(_env_file=None, database_url=value, jwt_secret=secret, allow_sqlite=True, environment="test")
    engine = build_engine(settings)
    config = Config(str(PROJECT_ROOT / "backend/alembic.ini"))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
    with session_factory(engine).begin() as session:
        init_rbac(session)
        org, _ = seed_demo(session, load_demo())
        create_user(session, org, "smoke-admin", password)
    engine.dispose()
    for port in [8017, 5187]:
        with socket.socket() as check:
            check.bind(("127.0.0.1", port))
    environment = {**os.environ, "CHRONOS_DATABASE_URL": value, "CHRONOS_JWT_SECRET": secret,
        "CHRONOS_ALLOW_SQLITE": "true", "CHRONOS_ENVIRONMENT": "test", "CHRONOS_COOKIE_SECURE": "false"}
    processes = []
    handles = []
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    try:
        for name, command_line, cwd in [
            ("backend", [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8017"], PROJECT_ROOT / "backend"),
            ("frontend", ["node", str(PROJECT_ROOT / "frontend/node_modules/vite/bin/vite.js"), "--host", "127.0.0.1", "--strictPort"], PROJECT_ROOT / "frontend"),
        ]:
            output = (runtime / f"phase{phase}-{name}-smoke.log").open("w", encoding="utf-8")
            handles.append(output)
            processes.append(subprocess.Popen(command_line, cwd=cwd, env=environment, stdout=output, stderr=subprocess.STDOUT, creationflags=flags))
        with httpx.Client(base_url="http://127.0.0.1:5187", timeout=15) as client:
            for _ in range(80):
                if any(process.poll() is not None for process in processes):
                    raise RuntimeError("Servidor de teste encerrou antes da verificação")
                try:
                    if client.get("/api/v1/health/ready").status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(.25)
            else:
                raise RuntimeError("Timeout esperando servidores locais")
            origin = {"Origin": "http://127.0.0.1:5187"}
            def csrf():
                return {**origin, "X-CSRF-Token": client.get("/api/v1/session/csrf", headers=origin).json()["csrf_token"]}
            result = client.post("/api/v1/session/login", headers=csrf(), json={"organization": "horizonte", "username": "smoke-admin", "password": password})
            assert result.status_code == 200 and "refresh_token" not in result.json()
            assert all("HttpOnly" in cookie for cookie in result.headers.get_list("set-cookie"))
            token = result.json()["access_token"]
            authorization = {"Authorization": "Bearer " + token}
            overview = client.get("/api/v1/analytics/overview", headers=authorization).json()
            assert overview["employee_count"] == 350
            create = client.post("/api/v1/employees", headers={**authorization, "Idempotency-Key": "phase3-http-person"},
                json={"unit_id": demo_id("horizonte-main"), "department_id": demo_id("management"), "job_role_id": demo_id("director"),
                      "name": "Pessoa Sintética HTTP", "registration": "HTTP001"})
            assert create.status_code == 201
            changed = client.get("/api/v1/analytics/overview", headers=authorization).json()
            assert changed["employee_count"] == 351
            calendar_report = {}
            if phase >= 4:
                person = client.get("/api/v1/employees/" + demo_id("hh-0001"), headers=authorization).json()
                shift = {"employee_id": person["id"], "department_id": person["department_id"], "label": "Plantão HTTP",
                    "start_at": "2026-11-02T08:00:00-03:00", "end_at": "2026-11-02T17:00:00-03:00",
                    "breaks": [{"start_at": "2026-11-02T12:00:00-03:00", "end_at": "2026-11-02T13:00:00-03:00", "paid": False}]}
                initial = client.post("/api/v1/calendar/preview", headers=authorization, json=shift)
                assert initial.status_code == 200 and initial.json()["actual_minutes"] == 480
                rule = client.post("/api/v1/labor-rules", headers=authorization, json={"key": "hipotese_http", "version": 1, "kind": "max_daily", "minutes": 420,
                    "valid_from": "2026-01-01T00:00:00Z", "valid_until": "2027-01-01T00:00:00Z", "source": "Hipótese sintética para teste HTTP", "status": "pending_review"})
                assert rule.status_code == 201
                stale = client.post("/api/v1/calendar", headers=authorization, json=shift | {"preview_digest": initial.json()["digest"]})
                assert stale.status_code == 409 and stale.json()["code"] == "PREVIEW_EXPIRED"
                evaluated = client.post("/api/v1/calendar/preview", headers=authorization, json=shift).json()
                assert evaluated["status"] == "nonconform"
                saved = client.post("/api/v1/calendar", headers=authorization, json=shift | {"preview_digest": evaluated["digest"]})
                assert saved.status_code == 201
                listing = client.get("/api/v1/calendar", headers=authorization, params={"start": "2026-11-01T00:00:00-03:00", "end": "2026-12-01T00:00:00-03:00"})
                assert listing.status_code == 200 and listing.json()["total"] == 1
                url = "/api/v1/calendar/" + saved.json()["id"]
                assert client.post(url + "/cancel", headers=authorization, json={"revision": 1}).status_code == 200
                history = client.get(url + "/evaluations", headers=authorization)
                assert history.status_code == 200 and len(history.json()["items"]) == 2
                calendar_report = {"calendar_preview": 200, "stale_preview": 409, "rule_version": 201, "draft_save": 201, "month_listing": 1, "cancel": 200, "evaluation_snapshots": 2}
            if phase >= 5:
                pattern = client.post("/api/v1/work-patterns", headers=authorization, json={"name": "Ciclo HTTP 5x2", "description": "Hipótese sintética de ciclo", "configuration": {"cycle": ["work"] * 5 + ["rest"] * 2, "shift_minutes": 540}})
                assert pattern.status_code == 201
                started = time.perf_counter()
                scenario = client.post("/api/v1/scenarios", headers={**authorization, "Idempotency-Key": "phase5-http-scenario"}, timeout=60,
                    json={"name": "Hospital completo HTTP", "key": "hospital-http", "unit_id": demo_id("horizonte-main"), "reference_month": "2026-11-01",
                        "mode": "cycle", "work_pattern_id": pattern.json()["id"], "cycle_anchor": "2026-11-02", "break_minutes": 60,
                        "target_weekly_minutes": 2400, "eligibility": "hypothesis", "source": "Hipótese sintética para testar os 350 colaboradores",
                        "demands": ([{"name": "Atendimento de teste", "department_id": demo_id("management"), "start_time": "08:00", "duration_minutes": 420,
                            "weekdays": list(range(7)), "required_staff": 1, "source": "Demanda hipotética para integração HTTP"}] if phase >= 6 else [])})
                assert scenario.status_code == 201, scenario.text[:200]
                elapsed = round(time.perf_counter() - started, 3)
                # O smoke também criou uma pessoa efêmera: 350 fixture + 1, sem contrato.
                assert scenario.json()["capacity"]["population_count"] == 351
                assert "payroll_snapshot" not in scenario.json() and "salary_cents" not in scenario.text
                financial = {"scenario_id": scenario.json()["id"], "name": "Projeção HTTP", "source": "Premissas hipotéticas de projeção"}
                baseline = client.post("/api/v1/financial/preview", headers=authorization, json=financial)
                assert baseline.status_code == 200 and baseline.json()["annual_total_cents"] > 0
                financial["components"] = [{"name": "Transição única", "kind": "fixed", "category": "training", "amount_cents": 10000, "recurrence": "once", "source": "Orçamento hipotético de transição"}]
                saved = client.post("/api/v1/financial", headers={**authorization, "Idempotency-Key": "phase5-http-financial"}, json=financial)
                assert saved.status_code == 201
                assert saved.json()["result"]["annual_total_cents"] - baseline.json()["annual_total_cents"] == 10000
                sensitivity = client.post("/api/v1/financial/" + saved.json()["id"] + "/sensitivity", headers=authorization, json={"driver": "fixed_costs", "delta_bps": 1000})
                assert sensitivity.status_code == 200 and sensitivity.json()["annual_total_cents"]["delta"] == 1000
                comparison = client.post("/api/v1/financial/compare", headers=authorization, json={"left_id": saved.json()["id"], "right_id": saved.json()["id"]})
                assert comparison.status_code == 200 and comparison.json()["annual_total_cents"]["delta"] == 0
                calendar_report.update({"scenario_create": 201, "scenario_population": 351, "scenario_seconds": elapsed, "financial_preview": 200, "financial_save": 201,
                    "one_time_increment_cents": 10000, "sensitivity_delta_cents": 1000, "financial_comparison": 200})
            if phase >= 6:
                payload = {"scenario_id": scenario.json()["id"], "name": "Otimização HTTP", "start_date": "2026-11-02", "end_date": "2026-11-03",
                    "mode": "diagnostic", "eligibility": "hypothesis", "templates": [{"name": "Diurno HTTP", "start_time": "08:00", "duration_minutes": 420}],
                    "limits": {"max_daily_minutes": 420, "max_weekly_minutes": 2400, "min_rest_minutes": 660, "min_break_minutes": 0,
                        "break_threshold_minutes": 420, "min_weekly_rest_minutes": 1440, "max_consecutive_days": 5, "source": "Limites sintéticos para teste de transporte"}}
                queued = client.post("/api/v1/optimization", headers=authorization, json=payload)
                assert queued.status_code == 202 and queued.json()["state"] == "queued", queued.text[:200]
                worker_start = time.perf_counter()
                # Separate CLI process, exactly as used by the local runtime.
                worker_output = (runtime / "phase6-worker-smoke.log").open("w", encoding="utf-8")
                handles.append(worker_output)
                worker = subprocess.Popen([sys.executable, "scripts/worker.py", "--runtime-dir", str(runtime), "--once"],
                    cwd=PROJECT_ROOT / "backend", env=environment, stdout=worker_output, stderr=subprocess.STDOUT, creationflags=flags)
                processes.append(worker)
                worker.wait(timeout=60)
                assert worker.returncode == 0
                result = client.get("/api/v1/optimization/" + queued.json()["id"], headers=authorization).json()
                assert result["state"] == "succeeded", result.get("error_code")
                assert result["result"]["verification"]["valid"] and result["result"]["verification"]["uncovered_staff_minutes"] == 0
                assert result["result"]["assignments"] and result["schedule_id"]
                proposal = client.get("/api/v1/schedules/" + result["schedule_id"], headers=authorization).json()
                rejected = client.post("/api/v1/schedules/" + proposal["id"] + "/decision", headers=authorization,
                    json={"revision": proposal["revision"], "schedule_digest": proposal["digest"], "action": "submit", "reason": "Tentativa com premissas ainda pendentes"})
                assert rejected.status_code == 409 and rejected.json()["code"] == "APPROVAL_BLOCKED"
                assert client.get("/otimizacao").status_code == 200
                calendar_report.update({"optimization_enqueue": 202, "worker_cli": "passed", "worker_seconds": round(time.perf_counter() - worker_start, 3),
                    "solver_status": result["result"]["solver_status"], "solver_population": 351, "coverage_staff_minutes": 420,
                    "uncovered_staff_minutes": 0, "schedule_proposal": "draft", "pending_approval_blocked": 409, "optimization_spa_route": 200})
            if phase >= 9:
                import base64, hashlib, io, zipfile
                selection = {"scenario_id":scenario.json()["id"],"optimization_id":queued.json()["id"],"financial_id":saved.json()["id"]}
                analytics = client.post("/api/v1/analytics/report",headers=authorization,json=selection)
                assert analytics.status_code == 200
                assert sum(m["total_cents"] for m in analytics.json()["tables"]["finance"]) == saved.json()["result"]["annual_total_cents"]
                for format in ["csv","xlsx"]:
                    exported = client.post("/api/v1/analytics/export",headers=authorization,json=selection|{"format":format})
                    assert exported.status_code == 200
                    artifact = exported.json(); content = base64.b64decode(artifact["content"])
                    assert hashlib.sha256(content).hexdigest() == artifact["sha256"]
                    with zipfile.ZipFile(io.BytesIO(content)) as archive:
                        assert archive.testzip() is None
                assert client.get("/api/v1/health").headers["x-content-type-options"] == "nosniff"
                calendar_report.update(analytics=200,csv_export=200,xlsx_export=200,download_hashes_verified=True,n8n_started=False)
            renewed = client.post("/api/v1/session/refresh", headers=csrf())
            assert renewed.status_code == 200 and "refresh_token" not in renewed.json()
            assert client.post("/api/v1/session/logout", headers=csrf()).status_code == 204
            assert client.get("/api/v1/employees", headers=authorization).status_code == 401
            assert client.cookies.get("chronos-refresh") is None
            report = {"product": "Chronos 1.0", "phase": phase, "transport": "real-http-vite-proxy-fastapi", "browser_used": False,
                "login": 200, "create_employee": 201, "dashboard_before": 350, "dashboard_after": 351,
                "cookie_http_only": True, "refresh": 200, "logout": 204, "access_after_logout": 401,
                "main_database_modified": False, **calendar_report}
            (runtime / f"phase{phase}-http-checks.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(report, ensure_ascii=False))
    finally:
        for process in reversed(processes):
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        for handle in handles:
            handle.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chronos 1.0 — smoke HTTP isolado da Fase 3")
    parser.add_argument("--runtime", required=True)
    main(parser.parse_args().runtime)
