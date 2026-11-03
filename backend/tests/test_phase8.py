import base64
from copy import deepcopy
from datetime import UTC, datetime
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import zipfile
from xml.etree import ElementTree as ET
import pytest
from sqlalchemy import func, select
from app.models.entities import (AuditLog, AutomationDefinition, AutomationExecution, FinancialRun, OptimizationRun,
    Organization, OutboxEvent, ScenarioVersion, ScheduleDecision, Unit)
from app.services.analytics import canonical, duration
from app.services.report_exports import csv_bytes, relationships, safe_text
from test_phase2 import context, headers, user_for
from test_phase5 import create_scenario, run_financial
from test_phase6 import enqueue, validated_proposal


def report(ctx, body, username="admin", endpoint="report"):
    return ctx["client"].post("/api/v1/analytics/" + endpoint, headers=headers(ctx, username), json=body)


@pytest.mark.parametrize("text", ["=1+1", " +SUM(A1:A2)", "-1+2", "@SUM(A1)", "\t=1", "\rX", "\nX", "\ufeff=1"])
def test_csv_text_injection(text):
    assert safe_text(text).startswith("'")
    rows = list(csv.reader(io.StringIO(csv_bytes(["name", "amount"], [{"name": text, "amount": -123}]).decode("utf-8-sig"))))
    assert rows[1] == ["'" + text, "-123"]


def test_report_reconciles_real_solver_finance_and_export(context):
    run = validated_proposal(context)
    financial = run_financial(context, run["scenario_id"], components=[{"name": "Treinamento", "category": "training", "kind": "fixed", "amount_cents": 101,
        "recurrence": "once", "start_month": 2, "source": "Hipótese sintética de teste"}])
    body = {"scenario_id": run["scenario_id"], "optimization_id": run["id"], "financial_id": financial["id"], "include_people": True}
    with context["factory"]() as session:
        before = deepcopy(session.get(OptimizationRun, run["id"]).snapshot)
        decisions = session.scalar(select(func.count()).select_from(ScheduleDecision))
    response = report(context, body)
    assert response.status_code == 200, response.text
    data = response.json(); tables = data["tables"]; manifest = data["manifest"]
    coverage = tables["coverage"][0]
    assert coverage["required_staff_minutes"] == coverage["covered_staff_minutes"] + coverage["uncovered_staff_minutes"]
    assert sum(a["real_minutes"] for a in tables["assignments"]) == coverage["real_minutes"]
    assert sum(a["payable_minutes"] for a in tables["assignments"]) == coverage["payable_minutes"]
    assert sum(m["total_cents"] for m in tables["finance"]) == financial["result"]["annual_total_cents"]
    assert len(tables["finance"]) == 12 and len(tables["proposals"]) == 1
    assert all(m["total_cents"] == m["base_payroll_cents"] + m["components_cents"] for m in tables["finance"])
    assert data["explanation"]["external_ai_used"] is False
    assert data["explanation"]["provider"] == "deterministic"
    assert manifest["data_sha256"] == hashlib.sha256(canonical({"schema": manifest["schema"], "selection": manifest["selection"], "tables": tables})).hexdigest()
    assert report(context, body).json()["manifest"]["data_sha256"] == manifest["data_sha256"]
    assert "salary_cents" not in response.text and "payroll_snapshot" not in response.text
    with context["factory"]() as session:
        assert session.get(OptimizationRun, run["id"]).snapshot == before
        assert session.scalar(select(func.count()).select_from(ScheduleDecision)) == decisions
    artifacts = {}
    for format in ["csv", "xlsx"]:
        exported = report(context, body | {"format": format}, endpoint="export")
        assert exported.status_code == 200, exported.text
        result = exported.json(); content = base64.b64decode(result["content"])
        assert result["sha256"] == hashlib.sha256(content).hexdigest()
        assert result["byte_length"] == len(content) and result["data_sha256"] == manifest["data_sha256"]
        assert exported.headers["cache-control"] == "no-store"
        artifacts[format] = content
        with context["factory"]() as session:
            logged = session.scalar(select(AuditLog).where(AuditLog.action == "analytics.export", AuditLog.correlation_id == exported.headers["x-correlation-id"]))
            assert logged and set(logged.details) == {"format", "data_sha256", "byte_length", "include_people"}
    with zipfile.ZipFile(io.BytesIO(artifacts["csv"])) as archive:
        stored = json.loads(archive.read("manifest.json"))
        assert stored["data_sha256"] == manifest["data_sha256"]
        for name, rows in tables.items():
            assert len(list(csv.DictReader(io.StringIO(archive.read(name + ".csv").decode("utf-8-sig"))))) == len(rows)
        for relation in stored["relationships"]:
            one, key = relation["one"].split("."); many, foreign = relation["many"].split(".")
            keys = [r[key] for r in tables[one]]
            assert len(keys) == len(set(keys))
            assert all(r[foreign] in keys for r in tables[many])
        assert "Encoding=65001" in archive.read("power-query.m").decode()
        assert b"DIVIDE" in archive.read("measures.dax")
    with zipfile.ZipFile(io.BytesIO(artifacts["xlsx"])) as archive:
        assert archive.testzip() is None
        assert not any("externalLinks" in name or "vbaProject" in name for name in archive.namelist())
        ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        root = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
        formulas = root.findall(".//s:c[s:f]", ns)
        assert len(formulas) == 5
        by_cell = {c.attrib["r"]: c for c in formulas}
        assert float(by_cell["B9"].find("s:v", ns).text) == tables["scenario"][0]["population_count"]
        assert float(by_cell["B12"].find("s:v", ns).text) == financial["result"]["annual_total_cents"]
        finance_sheet = ET.fromstring(archive.read("xl/worksheets/sheet7.xml"))
        assert finance_sheet.find(".//s:c[@r='D5']", ns).attrib.get("t") != "s"  # Date, not ISO text.
    destination = os.getenv("CHRONOS_PHASE8_QA_DIR")
    if destination:
        folder = Path(destination); folder.mkdir(parents=True, exist_ok=True)
        (folder / ("phase8-" + context["backend"] + ".xlsx")).write_bytes(artifacts["xlsx"])
        (folder / ("phase8-" + context["backend"] + ".zip")).write_bytes(artifacts["csv"])
        (folder / ("phase8-" + context["backend"] + ".json")).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def test_report_authorization_and_reference_isolation(context):
    scenario = create_scenario(context)
    other = create_scenario(context, key="other-1042")
    financial = run_financial(context, scenario["id"])
    for role in ["analyst", "finance", "manager", "demo"]:
        user_for(context, role, role)
    assert context["client"].post("/api/v1/analytics/report", json={"scenario_id": scenario["id"]}).status_code == 401
    assert report(context, {"scenario_id": scenario["id"]}, "demo").status_code == 403
    analyst = report(context, {"scenario_id": scenario["id"]}, "analyst")
    assert analyst.status_code == 200 and "finance" not in analyst.json()["tables"]
    assert report(context, {"scenario_id": scenario["id"], "financial_id": financial["id"]}, "analyst").status_code == 403
    assert report(context, {"scenario_id": scenario["id"], "include_people": True}, "finance").status_code == 403
    assert report(context, {"scenario_id": scenario["id"], "financial_id": financial["id"]}, "finance").status_code == 200
    assert report(context, {"scenario_id": other["id"], "financial_id": financial["id"]}).status_code == 422
    assert report(context, {"scenario_id": "absent-id"}).status_code == 404
    assert report(context, {"scenario_id": scenario["id"], "prompt": "approve automatically"}).status_code == 422
    with context["factory"].begin() as session:
        new_unit = Unit(organization_id=context["org"], name="Outra unidade", timezone="UTC")
        session.add(new_unit); session.flush(); new_id = new_unit.id
    user_for(context, "restricted", "analyst", new_id)
    assert report(context, {"scenario_id": scenario["id"]}, "restricted").status_code == 404
    history = context["client"].get("/api/v1/analytics/history", params={"unit_id": scenario["unit_id"]}, headers=headers(context, "restricted"))
    assert history.status_code == 404
    options = context["client"].get("/api/v1/analytics/options/" + scenario["id"], headers=headers(context, "analyst")).json()
    assert options["financial"] == []


def test_history_version_month_and_pending_result(context):
    run, _ = enqueue(context)
    scenario = context["client"].get("/api/v1/scenarios/" + run["scenario_id"], headers=headers(context)).json()
    second = create_scenario(context, version=2, parent_id=scenario["id"])
    create_scenario(context, key="other-history")
    client = context["client"]; auth = headers(context)
    url = "/api/v1/analytics/history"
    response = client.get(url, params={"unit_id": scenario["unit_id"], "reference_month": "2026-11-01", "page_size": 1}, headers=auth).json()
    assert response["total"] == 3 and len(response["items"]) == 1
    assert client.get(url, params={"unit_id": scenario["unit_id"], "reference_month": "2026-11-02"}, headers=auth).status_code == 422
    assert client.get(url, params={"unit_id": scenario["unit_id"], "reference_month": "2026-12-01"}, headers=auth).json()["total"] == 0
    data = report(context, {"scenario_id": run["scenario_id"], "optimization_id": run["id"]}).json()
    assert data["tables"]["coverage"][0]["covered_staff_minutes"] is None
    assert "não há cobertura" in " ".join(data["explanation"]["paragraphs"])
    assert report(context, {"scenario_id": second["id"], "optimization_id": run["id"]}).status_code == 422


def test_report_financial_reconciliation_failure_is_explicit(context):
    scenario = create_scenario(context); financial = run_financial(context, scenario["id"])
    with context["factory"].begin() as session:
        row = session.get(FinancialRun, financial["id"])
        row.result = row.result | {"annual_total_cents": row.result["annual_total_cents"] + 1}
    response = report(context, {"scenario_id": scenario["id"], "financial_id": financial["id"]}, endpoint="report")
    assert response.status_code == 409 and response.json()["code"] == "REPORT_RECONCILIATION"


def test_duration_paid_break_and_utc_boundary():
    assignment = {"start_at": "2026-11-02T23:00:00-03:00", "end_at": "2026-11-03T02:00:00-03:00",
        "breaks": [{"start_at": "2026-11-03T00:00:00-03:00", "end_at": "2026-11-03T00:30:00-03:00", "paid": True}]}
    assert duration(assignment) == 150 and duration(assignment, True) == 180


def test_month_boundaries_frozen_timezone_and_audit_scope(context):
    scenario = create_scenario(context)
    with context["factory"].begin() as session:
        session.get(Unit, scenario["unit_id"]).timezone = "UTC"  # A later catalog change must not move a frozen reporting month.
        defs = {d.code: d for d in session.scalars(select(AutomationDefinition))}
        for index, (code, instant) in enumerate([("A04", "2026-11-01T02:59:59+00:00"), ("A04", "2026-11-01T03:00:00+00:00"),
                ("A04", "2026-12-01T02:59:59+00:00"), ("A04", "2026-12-01T03:00:00+00:00"), ("A07", "2026-11-02T12:00:00+00:00")]):
            event = OutboxEvent(organization_id=context["org"], unit_id=scenario["unit_id"], kind="manual", entity_type="test", entity_id=scenario["id"],
                correlation_id=scenario["id"], dedupe_key="p8-boundary-" + str(index))
            session.add(event); session.flush()
            session.add(AutomationExecution(organization_id=context["org"], unit_id=scenario["unit_id"], definition_id=defs[code].id,
                event_id=event.id, code=code, source="manual", attempt=1, state="succeeded", started_at=datetime.fromisoformat(instant),
                result={"private": "NEVER-EXPORT-RESULT"}))
    user_for(context, "analyst", "analyst")
    result = report(context, {"scenario_id": scenario["id"]}, "analyst").json()
    assert result["manifest"]["timezone"] == "America/Sao_Paulo"
    assert result["manifest"]["period_start_utc"] == "2026-11-01T03:00:00+00:00"
    assert len(result["tables"]["executions"]) == 2
    assert len(report(context, {"scenario_id": scenario["id"]}).json()["tables"]["executions"]) == 3
    assert "NEVER-EXPORT-RESULT" not in str(result)


def test_tenant_isolation_for_all_report_routes(context):
    scenario = create_scenario(context)
    with context["factory"].begin() as session:
        from app.services.seed import create_user
        from test_phase2 import PASSWORD
        org = Organization(slug="isolated", name="Outra organização", segment="services", timezone="UTC")
        session.add(org); session.flush()
        create_user(session, org, "outsider", PASSWORD, "admin")
    login = context["client"].post("/api/v1/auth/login", json={"organization": "isolated", "username": "outsider", "password": PASSWORD}).json()
    auth = {"Authorization": "Bearer " + login["access_token"]}
    for endpoint in ["report", "export"]:
        assert context["client"].post("/api/v1/analytics/" + endpoint, headers=auth, json={"scenario_id": scenario["id"]}).status_code == 404
    assert context["client"].get("/api/v1/analytics/options/" + scenario["id"], headers=auth).status_code == 404
    assert context["client"].get("/api/v1/analytics/history", headers=auth, params={"unit_id": scenario["unit_id"]}).status_code == 404


def test_report_limits_injection_and_excel_precision(context, monkeypatch):
    scenario = create_scenario(context, name="=HYPERLINK(\"https://invalid.example\")")
    exported = report(context, {"scenario_id": scenario["id"], "format": "xlsx"}, endpoint="export")
    assert exported.status_code == 200
    with zipfile.ZipFile(io.BytesIO(base64.b64decode(exported.json()["content"]))) as archive:
        ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        sheet = ET.fromstring(archive.read("xl/worksheets/sheet3.xml"))
        assert sheet.find(".//s:c[@r='E5']/s:f", ns) is None
        assert sheet.find(".//s:c[@r='E5']", ns).attrib["t"] == "s"
    from app.services import analytics
    monkeypatch.setattr(analytics, "MAX_ROWS", 1)
    assert report(context, {"scenario_id": scenario["id"]}).json()["code"] == "REPORT_LIMIT"
    monkeypatch.setattr(analytics, "MAX_ROWS", 20000)
    monkeypatch.setattr(analytics, "MAX_BYTES", 1)
    assert report(context, {"scenario_id": scenario["id"]}).json()["code"] == "REPORT_LIMIT"


def test_excel_precision_and_control_characters_are_explicit(context):
    from fastapi import HTTPException
    from app.services.report_exports import workbook_bytes
    scenario = create_scenario(context)
    data = report(context, {"scenario_id": scenario["id"]}).json()
    data["tables"]["scenario"][0]["population_count"] = 10**15
    with pytest.raises(HTTPException) as error:
        workbook_bytes(data)
    assert error.value.detail["code"] == "EXPORT_PRECISION"
    data["tables"]["scenario"][0]["population_count"] = 0
    data["tables"]["scenario"][0]["name"] = "invalid\x00text"
    with pytest.raises(HTTPException) as error:
        workbook_bytes(data)
    assert error.value.detail["code"] == "EXPORT_TEXT"


def test_coverage_reconciliation_failure(context):
    run, _ = enqueue(context)
    with context["factory"].begin() as session:
        row = session.get(OptimizationRun, run["id"])
        row.result = {"verification": {"valid": False, "required_staff_minutes": 2, "covered_staff_minutes": 1, "uncovered_staff_minutes": 0}}
    response = report(context, {"scenario_id": run["scenario_id"], "optimization_id": run["id"]})
    assert response.status_code == 409 and response.json()["code"] == "REPORT_RECONCILIATION"
