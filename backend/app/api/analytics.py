import base64
import hashlib
from datetime import date
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from app.api.dependencies import fail, get_db, require
from app.api.resources import as_dict
from app.models.entities import FinancialRun, OptimizationRun, ScenarioVersion, Unit
from app.repositories.scoped import get_scoped, page, scoped
from app.schemas.analytics import ExportInput, ReportInput
from app.services.analytics import extract
from app.services.report_exports import export_bytes
from app.services.audit import audit

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics e exportações"])


@router.get("/history")
def history(unit_id: str, reference_month: date | None = None, page_number: int = Query(1, ge=1),
            page_size: int = Query(25, ge=1, le=100), principal=Depends(require("scenario:read")), session=Depends(get_db)):
    get_scoped(session, Unit, unit_id, principal, "scenario:read", Unit.id)
    query = scoped(ScenarioVersion, principal, "scenario:read", ScenarioVersion.unit_id).where(ScenarioVersion.unit_id == unit_id)
    if reference_month:
        if reference_month.day != 1:
            fail(422, "REPORT_PERIOD", "Informe o primeiro dia do mês de referência.")
        query = query.where(ScenarioVersion.reference_month == reference_month)
    return page(session, query.order_by(ScenarioVersion.reference_month.desc(), ScenarioVersion.key, ScenarioVersion.version.desc(), ScenarioVersion.id),
        page_number, page_size, lambda row: as_dict(row, ["id", "unit_id", "name", "key", "version", "reference_month", "digest", "created_at"]))


@router.get("/options/{scenario_id}")
def options(scenario_id: str, principal=Depends(require("scenario:read")), session=Depends(get_db)):
    scenario = get_scoped(session, ScenarioVersion, scenario_id, principal, "scenario:read", ScenarioVersion.unit_id)
    def choices(model, permission):
        if not principal.permits(permission, scenario.unit_id):
            return []
        rows = session.scalars(select(model).where(model.organization_id == principal.user.organization_id,
            model.scenario_id == scenario.id).order_by(model.created_at.desc(), model.id).limit(101)).all()
        return [{"id": r.id, "name": r.name, "created_at": r.created_at, **({"state": r.state} if model is OptimizationRun else {})} for r in rows[:100]]
    return {"optimization": choices(OptimizationRun, "optimization:read"), "financial": choices(FinancialRun, "finance:read"),
        "limit_per_kind": 100, "notice": "Até 100 resultados recentes por tipo. Um ID autorizado anterior também pode ser informado na API."}


@router.post("/report")
def report(payload: ReportInput, principal=Depends(require("scenario:read")), session=Depends(get_db)):
    return extract(session, principal, payload)


@router.post("/export")
def export(payload: ExportInput, request: Request, principal=Depends(require("scenario:read")), session=Depends(get_db)):
    report = extract(session, principal, payload)
    content = export_bytes(report, payload.format)
    audit(session, principal.user.organization_id, principal.user.id, "analytics.export", "scenario_versions", payload.scenario_id,
        correlation=request.state.correlation_id,
        details={"format": payload.format, "data_sha256": report["manifest"]["data_sha256"], "byte_length": len(content),
            "include_people": payload.include_people})
    session.commit()
    return {"filename": "chronos-1.0-" + report["manifest"]["data_sha256"][:12] + (".xlsx" if payload.format == "xlsx" else ".zip"),
        "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if payload.format == "xlsx" else "application/zip",
        "encoding": "base64", "content": base64.b64encode(content).decode(), "sha256": hashlib.sha256(content).hexdigest(),
        "data_sha256": report["manifest"]["data_sha256"], "byte_length": len(content)}
