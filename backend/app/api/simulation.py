from copy import deepcopy
import hashlib
import hmac
from datetime import date
from fastapi import APIRouter, Depends, Query, Request
from pydantic import Field
from sqlalchemy import select
from app.api.dependencies import fail, get_db, require
from app.api.resources import as_dict, related
from app.models.entities import (Department, FinancialRun, Qualification, ScenarioVersion, Skill, Unit, WorkPattern)
from app.repositories.scoped import get_scoped, page, scoped
from app.schemas.scheduling import Strict
from app.schemas.simulation import ComparisonInput, FinancialInput, ScenarioInput
from app.services import idempotency
from app.services.audit import audit
from app.services.capacity import build_scenario, digest
from app.services.financial import cents, difference, project

router = APIRouter(prefix="/api/v1", tags=["Cenários e simulador financeiro"])


def scenario_view(row, detail=False):
    fields = ["id", "unit_id", "department_id", "actor_id", "key", "version", "parent_id", "name", "reference_month", "created_at", "digest"]
    if detail:
        fields += ["inputs", "capacity"]
    return as_dict(row, fields)


def financial_view(row, detail=False):
    fields = ["id", "unit_id", "scenario_id", "actor_id", "name", "created_at", "digest"]
    if detail:
        fields += ["assumptions", "result"]
    return as_dict(row, fields)


def check_permission(principal, permission, unit):
    if not principal.permits(permission, unit):
        fail(403, "FORBIDDEN", "Permissão ou escopo insuficiente para esta unidade.")


@router.get("/scenarios")
def scenarios(unit_id: str | None = None, page_number: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), principal=Depends(require("scenario:read")), session=Depends(get_db)):
    query = scoped(ScenarioVersion, principal, "scenario:read", ScenarioVersion.unit_id)
    if unit_id:
        query = query.where(ScenarioVersion.unit_id == unit_id)
    return page(session, query.order_by(ScenarioVersion.created_at.desc(), ScenarioVersion.id), page_number, page_size, scenario_view)


@router.post("/scenarios", status_code=201)
def create_scenario(payload: ScenarioInput, request: Request, principal=Depends(require("scenario:write")), session=Depends(get_db)):
    check_permission(principal, "scenario:read", payload.unit_id)
    check_permission(principal, "scenario:write", payload.unit_id)
    related(session, Unit, payload.unit_id, principal)
    if payload.department_id:
        dept = related(session, Department, payload.department_id, principal)
        if dept.unit_id != payload.unit_id:
            fail(422, "INVALID_REFERENCE", "Setor fora da unidade selecionada.")
    if payload.parent_id:
        parent = get_scoped(session, ScenarioVersion, payload.parent_id, principal, "scenario:write", ScenarioVersion.unit_id)
        if (parent.key, parent.unit_id, parent.department_id, parent.reference_month, parent.version + 1) != (payload.key, payload.unit_id, payload.department_id, payload.reference_month, payload.version):
            fail(422, "INVALID_SUCCESSOR", "Nova versão exige mesmo grupo, unidade, setor e mês, com número seguinte.")
    if payload.work_pattern_id:
        related(session, WorkPattern, payload.work_pattern_id, principal)
    for demand in payload.demands:
        dept = related(session, Department, demand.department_id, principal)
        if dept.unit_id != payload.unit_id or payload.department_id and dept.id != payload.department_id:
            fail(422, "INVALID_REFERENCE", "Demanda fora da população selecionada.")
        for model, ids in [(Skill, demand.skill_ids), (Qualification, demand.qualification_ids)]:
            for ident in ids:
                related(session, model, ident, principal)
    content = payload.model_dump(mode="json")
    existing, pending = idempotency.prepare(session, request, principal, ScenarioVersion, content)
    if existing:
        return scenario_view(existing, True)
    capacity, evidence, payroll = build_scenario(session, principal.user.organization_id, payload)
    row = ScenarioVersion(organization_id=principal.user.organization_id, unit_id=payload.unit_id, department_id=payload.department_id, actor_id=principal.user.id,
        key=payload.key, version=payload.version, parent_id=payload.parent_id, name=payload.name, reference_month=payload.reference_month,
        inputs=content, capacity=capacity, evidence=evidence, payroll_snapshot=payroll,
        digest=hmac.new(request.app.state.settings.jwt_secret.get_secret_value().encode(), digest({"inputs": content, "capacity": capacity, "evidence": evidence, "payroll": payroll}).encode(), hashlib.sha256).hexdigest())
    session.add(row)
    session.flush()
    idempotency.record(session, pending, row.id)
    audit(session, row.organization_id, principal.user.id, "scenario.create", row.__tablename__, row.id, request.state.correlation_id, {"version": row.version, "digest": row.digest})
    session.commit()
    return scenario_view(row, True)


@router.post("/scenarios/compare")
def compare_scenarios(payload: ComparisonInput, principal=Depends(require("scenario:read")), session=Depends(get_db)):
    left, right = [get_scoped(session, ScenarioVersion, ident, principal, "scenario:read", ScenarioVersion.unit_id) for ident in [payload.left_id, payload.right_id]]
    if (left.unit_id, left.department_id, left.reference_month) != (right.unit_id, right.department_id, right.reference_month):
        fail(422, "INCOMPARABLE", "Compare cenários da mesma unidade, população e mês.")
    return {"left_id": left.id, "right_id": right.id, "metrics": {key: difference(left.capacity[key], right.capacity[key]) for key in
        ["population_count", "raw_available_minutes", "effective_budget_minutes", "required_staff_minutes", "aggregate_gap_lower_bound_minutes"]}, "scope": "Comparação agregada; não demonstra viabilidade ou cobertura operacional."}


@router.get("/scenarios/{id}")
def scenario(id: str, principal=Depends(require("scenario:read")), session=Depends(get_db)):
    return scenario_view(get_scoped(session, ScenarioVersion, id, principal, "scenario:read", ScenarioVersion.unit_id), True)


@router.get("/scenarios/{id}/evidence")
def scenario_evidence(id: str, principal=Depends(require("scenario:read")), session=Depends(get_db)):
    row = get_scoped(session, ScenarioVersion, id, principal, "scenario:read", ScenarioVersion.unit_id)
    check_permission(principal, "people:read", row.unit_id)
    return row.evidence  # Nunca retorna payroll_snapshot.


def financial_context(payload, principal, session):
    scenario = get_scoped(session, ScenarioVersion, payload.scenario_id, principal, "scenario:read", ScenarioVersion.unit_id)
    check_permission(principal, "finance:read", scenario.unit_id)
    check_permission(principal, "finance:simulate", scenario.unit_id)
    return scenario


@router.post("/financial/preview")
def financial_preview(payload: FinancialInput, principal=Depends(require("scenario:read")), session=Depends(get_db)):
    row = financial_context(payload, principal, session)
    return project(row.reference_month, row.payroll_snapshot, payload)


@router.post("/financial", status_code=201)
def create_financial(payload: FinancialInput, request: Request, principal=Depends(require("scenario:read")), session=Depends(get_db)):
    row = financial_context(payload, principal, session)
    content = payload.model_dump(mode="json")
    existing, pending = idempotency.prepare(session, request, principal, FinancialRun, content)
    if existing:
        return financial_view(existing, True)
    result = project(row.reference_month, row.payroll_snapshot, payload)
    run = FinancialRun(organization_id=row.organization_id, unit_id=row.unit_id, scenario_id=row.id, actor_id=principal.user.id, name=payload.name,
        assumptions=content, result=result, digest=digest({"scenario_digest": row.digest, "assumptions": content, "result": result}))
    session.add(run)
    session.flush()
    idempotency.record(session, pending, run.id)
    audit(session, run.organization_id, principal.user.id, "financial.create", run.__tablename__, run.id, request.state.correlation_id, {"digest": run.digest})
    session.commit()
    return financial_view(run, True)


@router.get("/financial")
def financial_runs(scenario_id: str | None = None, page_number: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), principal=Depends(require("finance:read")), session=Depends(get_db)):
    query = scoped(FinancialRun, principal, "finance:read", FinancialRun.unit_id)
    if scenario_id:
        query = query.where(FinancialRun.scenario_id == scenario_id)
    return page(session, query.order_by(FinancialRun.created_at.desc(), FinancialRun.id), page_number, page_size, financial_view)


@router.get("/financial/{id}")
def financial_run(id: str, principal=Depends(require("finance:read")), session=Depends(get_db)):
    return financial_view(get_scoped(session, FinancialRun, id, principal, "finance:read", FinancialRun.unit_id), True)


@router.post("/financial/compare")
def compare_financial(payload: ComparisonInput, principal=Depends(require("finance:read")), session=Depends(get_db)):
    left, right = [get_scoped(session, FinancialRun, ident, principal, "finance:read", FinancialRun.unit_id) for ident in [payload.left_id, payload.right_id]]
    a, b = [session.get(ScenarioVersion, r.scenario_id) for r in [left, right]]
    if (a.unit_id, a.department_id, a.reference_month) != (b.unit_id, b.department_id, b.reference_month):
        fail(422, "INCOMPARABLE", "Compare projeções da mesma unidade, população e mês de origem.")
    salary_maps = [{e["employee_id"]: e["contracts"] for e in s.payroll_snapshot["employees"]} for s in [a, b]]
    common = salary_maps[0].keys() & salary_maps[1].keys()
    decreases, comparable_count = 0, 0
    for ident in common:
        decreased, comparable = False, False
        for old in salary_maps[0][ident]:
            for new in salary_maps[1][ident]:
                if max(old["valid_from"], new["valid_from"], str(a.reference_month)) < min(old["valid_until"] or "9999-12-31", new["valid_until"] or "9999-12-31"):
                    comparable = True
                    decreased |= new["salary_cents"] < old["salary_cents"]
        decreases += int(decreased)
        comparable_count += int(comparable)
    return {"annual_total_cents": difference(left.result["annual_total_cents"], right.result["annual_total_cents"]),
        "months": [{"month": l["month"], **difference(l["total_cents"], r["total_cents"])} for l, r in zip(left.result["months"], right.result["months"])],
        "salary_check": {"common_employees": len(common), "comparable_employees": comparable_count, "decreases_detected": decreases, "preserved": decreases == 0 if comparable_count else None,
            "scope": "Compara salários nominais em vigências contratuais sobrepostas; não certifica remuneração integral ou continuidade do vínculo."}}


class SensitivityInput(Strict):
    driver: str = Field(pattern="^(hours_volume|fixed_costs|charges_rate)$")
    delta_bps: int = Field(ge=-5000, le=5000)


@router.post("/financial/{id}/sensitivity")
def sensitivity(id: str, payload: SensitivityInput, principal=Depends(require("finance:read")), session=Depends(get_db)):
    row = get_scoped(session, FinancialRun, id, principal, "finance:read", FinancialRun.unit_id)
    check_permission(principal, "finance:simulate", row.unit_id)
    data = deepcopy(row.assumptions)
    from decimal import Decimal
    for component in data["components"]:
        if payload.driver == "hours_volume" and component["kind"] == "hours":
            component["real_minutes_by_month"] = [cents(Decimal(m) * (10000 + payload.delta_bps) / 10000) for m in component["real_minutes_by_month"]]
        if payload.driver == "fixed_costs" and component["kind"] == "fixed":
            component["amount_cents"] = cents(Decimal(component["amount_cents"]) * (10000 + payload.delta_bps) / 10000)
        if payload.driver == "charges_rate" and component["kind"] == "percent" and component["category"] == "charge":
            component["rate_bps"] = cents(Decimal(component["rate_bps"]) * (10000 + payload.delta_bps) / 10000)
    from pydantic import ValidationError
    try:
        assumptions = FinancialInput.model_validate(data)
    except ValidationError:
        fail(422, "SENSITIVITY_LIMIT", "Variação excede limites dos componentes. Ajuste as premissas.")
    scenario = session.get(ScenarioVersion, row.scenario_id)
    result = project(scenario.reference_month, scenario.payroll_snapshot, assumptions)
    return {"driver": payload.driver, "delta_bps": payload.delta_bps, "annual_total_cents": difference(row.result["annual_total_cents"], result["annual_total_cents"]), "result": result, "saved": False}
