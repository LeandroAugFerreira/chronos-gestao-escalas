import asyncio
import base64
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
from uuid import uuid4
import zipfile
import io
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url
from app.core.config import PROJECT_ROOT, Settings
from app.core.database import build_engine, session_factory
from app.core.request_limits import RequestLimits
from app.main import create_app
from app.models import entities as m
from app.services.recovery import backup_sqlite, file_sha, outside_sync, quiesce_restored_copy, restore_isolated
from app.services.optimization_worker import work_once
from app.services.seed import demo_id
from test_phase2 import context, headers, user_for
from test_phase5 import create_scenario, run_financial
from test_phase6 import enqueue
from test_phase7 import configure, queue, drain, integration_key
from test_optimizer import snapshot


def test_api_security_headers_and_body_limit(context):
    client = context["client"]
    for path in ["/api/v1/health", "/api/v1/employees", "/api/v1/not-found"]:
        response = client.get(path)
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["x-frame-options"] == "DENY"
        assert response.headers["referrer-policy"] == "no-referrer"
        assert response.headers["cache-control"] == "no-store"
    with context["factory"]() as session:
        before = session.scalar(select(func.count()).select_from(m.AuditLog))
    result = client.post("/api/v1/auth/login", content=b"x" * (context["settings"].max_request_bytes + 1), headers={"Content-Type": "application/json"})
    assert result.status_code == 413 and result.json()["code"] == "REQUEST_TOO_LARGE"
    assert result.headers["x-correlation-id"] == result.json()["correlation_id"]
    with context["factory"]() as session:
        assert session.scalar(select(func.count()).select_from(m.AuditLog)) == before


@pytest.mark.parametrize("headers_in,chunks,status", [([], [b"123", b"456"], 413), ([(b"content-length", b"2")], [b"123"], 400),
    ([(b"content-length", b"bad")], [], 400), ([(b"content-length", b"1"), (b"content-length", b"1")], [], 400),
    ([(b"content-encoding", b"gzip")], [], 415), ([], [b"123", b"45"], 204)])
def test_streamed_body_is_bounded_before_application(headers_in, chunks, status):
    async def exercise():
        called = []
        async def endpoint(scope, receive, send):
            called.append((await receive())["body"])
            await send({"type": "http.response.start", "status": 204, "headers": []})
            await send({"type": "http.response.body", "body": b""})
        items = [{"type": "http.request", "body": c, "more_body": i < len(chunks)-1} for i,c in enumerate(chunks)]
        async def receive():
            return items.pop(0) if items else {"type": "http.request", "body": b""}
        sent = []
        async def send(message): sent.append(message)
        await RequestLimits(endpoint, 5, 1)({"type": "http", "path": "/api/v1/test", "headers": headers_in}, receive, send)
        assert sent[0]["status"] == status
        assert called == [b"12345"] if status == 204 else not called
    asyncio.run(exercise())


def test_request_body_timeout():
    async def exercise():
        called = []
        async def endpoint(*_): called.append(True)
        async def receive(): await asyncio.sleep(1)
        sent = []
        async def send(message): sent.append(message)
        await RequestLimits(endpoint, 1024, .01)({"type": "http", "path": "/api/v1/test", "headers": []}, receive, send)
        assert sent[0]["status"] == 408 and not called
    asyncio.run(exercise())


@pytest.mark.parametrize("origin", ["*", "null", "https://user:secret@example.test", "https://example.test/path", "https://example.test?token=secret"])
def test_unsafe_origin_configuration_is_rejected(origin):
    with pytest.raises(ValueError): Settings(_env_file=None, allowed_origins=origin)


def test_production_profile_closes_documentation_and_requires_https():
    values = {"_env_file": None, "environment": "production", "database_url": "postgresql+psycopg://invalid@127.0.0.1/unused", "jwt_secret": "test-only-production-settings-very-long", "cookie_secure": True}
    with pytest.raises(ValueError): Settings(**values, allowed_origins="http://example.test")
    app = create_app(Settings(**values, allowed_origins="https://chronos.example.test"))
    try:
        with TestClient(app) as client:
            assert client.get("/docs").status_code == 404
            assert client.get("/openapi.json").status_code == 404
    finally: app.state.engine.dispose()


def test_unexpected_error_is_correlated_without_secret(context):
    @context["app"].get("/api/v1/test-unexpected-error")
    def broken(): raise RuntimeError("NEVER-EXPOSE-THIS-SECRET")
    with TestClient(context["app"], raise_server_exceptions=False) as client:
        result = client.get("/api/v1/test-unexpected-error")
    assert result.status_code == 500 and result.json()["code"] == "INTERNAL_ERROR"
    assert "NEVER-EXPOSE" not in result.text and "RuntimeError" not in result.text
    assert result.headers["x-correlation-id"] == result.json()["correlation_id"]
    assert result.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("role,allowed", [("admin", {"employees","financial","scenarios","optimization","automation-artifacts","users","audit"}),
    ("hr", {"employees","financial","scenarios","optimization","automation-artifacts"}),
    ("manager", {"employees","scenarios","optimization","automation-artifacts"}),
    ("analyst", {"scenarios","optimization","automation-artifacts"}), ("finance", {"financial","scenarios","automation-artifacts"}), ("demo", set())])
def test_role_matrix_is_enforced_by_api(context, role, allowed):
    user_for(context, "matrix-" + role, role)
    auth = headers(context, "matrix-" + role)
    for endpoint in ["employees","financial","scenarios","optimization","automation-artifacts","users","audit"]:
        response = context["client"].get("/api/v1/" + endpoint, headers=auth)
        assert response.status_code == (200 if endpoint in allowed else 403), (role, endpoint, response.text)


def test_integrated_review_finance_solver_approval_automation_export_restart(context, tmp_path):
    user_for(context, "reviewer", "manager")
    auth = headers(context); client = context["client"]
    with context["factory"]() as session:
        person = session.get(m.Employee, demo_id("hh-0001")); unit, department, role = person.unit_id, person.department_id, person.job_role_id
        ids = list(session.scalars(select(m.Employee.id).where(m.Employee.department_id == department)))
        contracts = list(session.scalars(select(m.Contract).where(m.Contract.employee_id.in_(ids))))
        contract_ids = {c.id for c in contracts}
        qualification_ids = set(session.scalars(select(m.EmployeeQualification.id).where(m.EmployeeQualification.employee_id.in_(ids))))
    # Configure and review synthetic inputs through the same API used by the app.
    response = client.post("/api/v1/work-patterns", headers=auth, json={"name":"Ciclo sintético integrado", "description":"Hipótese exclusivamente para teste integrado",
        "configuration": {"cycle": ["work"], "shift_minutes": 480}})
    assert response.status_code == 201, response.text
    pattern_id = response.json()["id"]
    # Link legacy seeded contracts to this synthetic pattern in the isolated fixture.
    from sqlalchemy import update
    with context["factory"].begin() as session:
        session.execute(update(m.Contract).where(m.Contract.id.in_(contract_ids)).values(work_pattern_id=pattern_id))
    for kind, selected in [("work_pattern", {pattern_id}), ("contract", contract_ids), ("qualification", qualification_ids)]:
        candidates = []; page = 1
        while True:
            response = client.get("/api/v1/optimization-review-targets", headers=auth, params={"kind":kind,"page_number": page, "page_size": 100, "unit_id": unit}).json()
            candidates.extend(response["items"])
            if len(candidates) >= response["total"]: break
            page += 1
        for candidate in candidates:
            if candidate["id"] in selected:
                response = client.post("/api/v1/optimization-reviews", headers=auth, json={"kind": kind, "entity_id": candidate["id"], "entity_digest": candidate["entity_digest"],
                    "source": "Hipótese sintética de integração", "evidence": "Revisão fictícia sem valor normativo"})
                assert response.status_code == 201, response.text
                if kind == "work_pattern":
                    # Even an already validated pattern receives a new persisted revision.
                    fresh = client.get("/api/v1/optimization-review-targets",headers=auth,params={"kind":kind}).json()["items"]
                    current = next(c for c in fresh if c["id"] == pattern_id)
                    repeated = {"kind":kind,"entity_id":pattern_id,"entity_digest":current["entity_digest"],
                        "source":"Revisão sintética repetida","evidence":"Segunda conferência fictícia do mesmo conteúdo"}
                    assert client.post("/api/v1/optimization-reviews",headers=auth,json=repeated).status_code == 201
                    assert client.post("/api/v1/optimization-reviews",headers=auth,json=repeated).status_code == 409
                    with context["factory"]() as session:
                        assert session.get(m.WorkPattern,pattern_id).revision == 3
    # Explicit test-only rule assumptions, not universal professional or legal minima.
    from datetime import UTC, datetime
    with context["factory"].begin() as session:
        for kind,value in [("max_daily",480),("max_weekly",2400),("min_rest",600),("min_break",0),("min_weekly_rest",1440)]:
            session.add(m.LaborRule(organization_id=context["org"], key="phase9-"+kind, version=1, kind=kind, minutes=value, threshold_minutes=480,
                valid_from=datetime(2026,1,1,tzinfo=UTC), valid_until=datetime(2027,1,1,tzinfo=UTC), source="Hipótese para teste integrado", status="validated",
                review_evidence="Hipótese fictícia conferida exclusivamente para teste", reviewer_id=context["user"]))
    scenario = create_scenario(context, demands=[{"name":"Atividade sintética", "department_id":department,"start_time":"08:00","duration_minutes":480,"weekdays":list(range(7)),
        "required_staff":1,"source":"Demanda sintética de teste","validation_status":"validated","review_evidence":"Hipótese exclusiva de teste"}])
    candidate = client.get("/api/v1/optimization-review-targets", headers=auth,params={"kind":"scenario"}).json()["items"][0]
    assert client.post("/api/v1/optimization-reviews", headers=auth, json={"kind":"scenario","entity_id":scenario["id"],"entity_digest":candidate["entity_digest"],
        "source":"Demanda sintética de teste","evidence":"Demanda e histórico fictícios conferidos"}).status_code == 201
    financial = run_financial(context, scenario["id"])
    body = snapshot()["options"] | {"scenario_id":scenario["id"], "eligibility":"verified", "activity_job_role_ids":{"0":[role]}, "cycle_anchors":{pattern_id:"2026-11-02"}}
    response = client.post("/api/v1/optimization", headers=auth, json=body)
    assert response.status_code == 202, response.text
    assert work_once(context["factory"], context["settings"], tmp_path)
    run = client.get("/api/v1/optimization/" + response.json()["id"], headers=auth).json()
    assert run["state"] == "succeeded" and run["result"]["approval_blockers"] == [], run
    proposal = client.get("/api/v1/schedules/"+run["schedule_id"], headers=auth).json()
    decision = {"revision":1,"schedule_digest":proposal["digest"],"action":"submit","reason":"Submissão sintética integrada"}
    url = "/api/v1/schedules/"+proposal["id"]+"/decision"
    assert client.post(url,headers=auth,json=decision).status_code == 200
    decision.update(revision=2,action="approve")
    assert client.post(url,headers=auth,json=decision).status_code == 403
    assert client.post(url,headers=headers(context,"reviewer"),json=decision).status_code == 200
    definition = configure(context,"A04"); queue(context,definition); drain(context,limit=300)
    assert client.get("/api/v1/automation-artifacts",headers=auth).json()["total"] == 1
    selection = {"scenario_id":scenario["id"],"optimization_id":run["id"],"financial_id":financial["id"],"include_people":True}
    result = client.post("/api/v1/analytics/report",headers=auth,json=selection).json()
    assert result["tables"]["proposals"][0]["state"] == "approved"
    assert sum(r["total_cents"] for r in result["tables"]["finance"]) == financial["result"]["annual_total_cents"]
    for format in ["csv","xlsx"]:
        exported = client.post("/api/v1/analytics/export",headers=auth,json=selection | {"format":format})
        assert exported.status_code == 200
        with zipfile.ZipFile(io.BytesIO(base64.b64decode(exported.json()["content"]))) as file: assert file.testzip() is None
    restarted = create_app(context["settings"])
    try:
        with TestClient(restarted) as other:
            persisted = other.get("/api/v1/schedules/"+proposal["id"],headers=auth).json()
            assert persisted["state"] == "approved" and persisted["digest"] == proposal["digest"]
    finally: restarted.state.engine.dispose()


def test_database_recovery_preserves_data_and_disables_effects(context, tmp_path):
    if context["backend"] != "sqlite":
        from recovery_helpers import verify_postgres_recovery
        return verify_postgres_recovery(context, tmp_path)
    run,_ = enqueue(context); auth = headers(context); configure(context,"A04")
    key = integration_key(context)
    source = Path(context["engine"].url.database)
    source_hash = file_sha(source)
    result = backup_sqlite(source,tmp_path/"backups")
    restored = restore_isolated(result["backup"],result["manifest"],tmp_path/"restored")
    assert restored["counts"]["employees"] == 350 and restored["counts"]["scenario_versions"] == 1
    assert restored["safety_changes"]["sessions_revoked"] > 0
    assert restored["safety_changes"]["credentials_disabled"] == 1
    assert restored["safety_changes"]["automations_disabled"] == 1
    assert restored["safety_changes"]["optimization_runs_cancelled"] == 1
    settings = Settings(_env_file=None,database_url="sqlite+pysqlite:///"+Path(restored["restored"]).as_posix(),allow_sqlite=True,environment="test",jwt_secret=context["settings"].jwt_secret)
    app = create_app(settings)
    try:
        with TestClient(app) as client:
            assert client.get("/api/v1/employees",headers=auth).status_code == 401
        with app.state.session_factory() as session:
            assert session.get(m.OptimizationRun,run["id"]).state == "cancelled"
            assert session.scalar(select(func.count()).select_from(m.IntegrationCredential).where(m.IntegrationCredential.enabled.is_(True))) == 0
    finally: app.state.engine.dispose()
    assert file_sha(source) == source_hash and file_sha(result["backup"]) == result["sha256"]
    with pytest.raises(FileExistsError): restore_isolated(result["backup"],result["manifest"],tmp_path/"restored")
    metadata = Path(result["manifest"]); info=json.loads(metadata.read_text()); info["sha256"]="0"*64; metadata.write_text(json.dumps(info))
    with pytest.raises(ValueError): restore_isolated(result["backup"],metadata,tmp_path/"corrupt")
    assert not (tmp_path/"corrupt").exists()


def test_recovery_refuses_project_or_sync_destination():
    for destination in [PROJECT_ROOT/"backup",Path.home()/"OneDrive"/"backup"]:
        with pytest.raises(ValueError): outside_sync(destination)


def test_known_n8n_runtime_is_blocked_for_development():
    policy = json.loads((PROJECT_ROOT/"automation/n8n/security-status.json").read_text())
    assert policy["execution_allowed"] is False and policy["candidate_audit"]["critical"] > 0
    with pytest.raises(ValueError,match="n8n bloqueada"):
        Settings(_env_file=None, environment="development", n8n_webhook_base_url="http://127.0.0.1:5687/webhook/chronos",
            n8n_outbound_token="test-only-outbound-token-with-at-least-32-characters")
