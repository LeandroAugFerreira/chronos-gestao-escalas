from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select, update
from app.api.dependencies import aware, fail, get_db, require
from app.api.resources import as_dict, commit_created, related, require_global
from app.models.entities import (CalendarShift, Contract, Department, Employee, JobRole, LaborRule,
    ScheduleEvaluation, Unit, WorkPattern)
from app.repositories.scoped import get_scoped, page, scoped
from app.schemas.scheduling import CancelInput, PatternInput, RuleInput, ShiftEdit, ShiftInput, ShiftSave, instant
from app.services import idempotency
from app.services.audit import audit
from app.services.labor_rules import evaluate

router = APIRouter(prefix="/api/v1", tags=["Jornadas e LaborRules"])
RULE_FIELDS = ["id", "key", "version", "supersedes_id", "kind", "minutes", "threshold_minutes", "unit_id", "job_role_id", "contract_id", "agreement", "valid_from", "valid_until", "source", "status", "review_evidence", "reviewer_id"]
SHIFT_FIELDS = ["id", "employee_id", "unit_id", "department_id", "start_at", "end_at", "breaks", "label", "state", "revision", "evaluation"]


@router.get("/labor-rules")
def rules(page_number: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), principal=Depends(require("rules:read")), session=Depends(get_db)):
    query = scoped(LaborRule, principal, "rules:read", LaborRule.unit_id)
    # Regras globais da organização também são legíveis por usuários com escopo local.
    scope = principal.scopes["rules:read"]
    if scope is not None:
        query = select(LaborRule).where(LaborRule.organization_id == principal.user.organization_id, (LaborRule.unit_id.is_(None) | LaborRule.unit_id.in_(scope)))
        visible_contracts = select(Contract.id).join(Employee, Employee.id == Contract.employee_id).where(Contract.organization_id == principal.user.organization_id,
            Employee.organization_id == principal.user.organization_id, Employee.unit_id.in_(scope))
        query = query.where(LaborRule.contract_id.is_(None) | LaborRule.contract_id.in_(visible_contracts))
    return page(session, query.order_by(LaborRule.key, LaborRule.version), page_number, page_size, lambda r: as_dict(r, RULE_FIELDS))


@router.post("/labor-rules", status_code=201)
def create_rule(payload: RuleInput, request: Request, principal=Depends(require("rules:write")), session=Depends(get_db)):
    # Alterar política exige escopo global; gestores de unidade podem editar só plantões.
    require_global(principal, "rules:write")
    if payload.supersedes_id:
        previous = related(session, LaborRule, payload.supersedes_id, principal)
        if any(getattr(previous, field) != getattr(payload, field) for field in ["key", "kind", "unit_id", "job_role_id", "contract_id", "agreement"]) or payload.version != previous.version + 1 or payload.valid_from < aware(previous.valid_from) or payload.valid_until != aware(previous.valid_until):
            fail(422, "INVALID_SUCCESSOR", "Substituição exige mesma chave, critério e escopo, versão seguinte, início igual/posterior e mesmo fim de vigência.")
    for model, value in [(Unit, payload.unit_id), (JobRole, payload.job_role_id), (Contract, payload.contract_id)]:
        if value:
            related(session, model, value, principal)
    if payload.contract_id and payload.unit_id:
        contract = related(session, Contract, payload.contract_id, principal)
        person = related(session, Employee, contract.employee_id, principal)
        if person.unit_id != payload.unit_id:
            fail(422, "INVALID_REFERENCE", "Contrato e unidade incompatíveis.")
    row = LaborRule(organization_id=principal.user.organization_id, **payload.model_dump(), reviewer_id=principal.user.id if payload.status == "validated" else None)
    row = commit_created(session, row, principal, request, "rule.version.create")
    return as_dict(row, RULE_FIELDS)


@router.post("/work-patterns", status_code=201)
def create_pattern(payload: PatternInput, request: Request, principal=Depends(require("rules:write")), session=Depends(get_db)):
    require_global(principal, "rules:write")
    row = commit_created(session, WorkPattern(organization_id=principal.user.organization_id, **payload.model_dump(exclude={"configuration"}), configuration=payload.configuration.model_dump() if payload.configuration else {}, legal_status="pending_review"), principal, request)
    return as_dict(row, ["id", "name", "description", "legal_status", "configuration"])


@router.get("/calendar")
def calendar(start: datetime, end: datetime, unit_id: str | None = None, department_id: str | None = None, employee_id: str | None = None,
             page_number: int = Query(1, ge=1), page_size: int = Query(100, ge=1, le=100), principal=Depends(require("schedule:read")), session=Depends(get_db)):
    if start.tzinfo is None or end.tzinfo is None or not timedelta(0) < end - start <= timedelta(days=62):
        fail(422, "INVALID_RANGE", "Informe período de até 62 dias com fuso horário.")
    query = scoped(CalendarShift, principal, "schedule:read", CalendarShift.unit_id).where(CalendarShift.start_at < end, CalendarShift.end_at > start, CalendarShift.state == "draft")
    for column, value in [(CalendarShift.unit_id, unit_id), (CalendarShift.department_id, department_id), (CalendarShift.employee_id, employee_id)]:
        if value:
            query = query.where(column == value)
    return page(session, query.order_by(CalendarShift.start_at, CalendarShift.id), page_number, page_size, lambda r: as_dict(r, SHIFT_FIELDS))


def target(payload, principal, session, permission, exclude_id=None):
    person = get_scoped(session, Employee, payload.employee_id, principal, permission, Employee.unit_id)
    dept = related(session, Department, payload.department_id, principal)
    # Serializa alterações concorrentes do calendário da pessoa no PostgreSQL.
    session.execute(select(Employee.id).where(Employee.id == person.id, Employee.organization_id == principal.user.organization_id).with_for_update())
    session.refresh(person)
    session.refresh(dept)
    if dept.unit_id != person.unit_id or not principal.permits(permission, dept.unit_id):
        fail(403, "FORBIDDEN", "Plantão exige lotação e destino na unidade autorizada.")
    return person, dept, evaluate(session, person, dept, payload, exclude_id)


@router.post("/calendar/preview")
def preview(payload: ShiftInput, shift_id: str | None = None, principal=Depends(require("schedule:write")), session=Depends(get_db)):
    if shift_id:
        get_scoped(session, CalendarShift, shift_id, principal, "schedule:write", CalendarShift.unit_id)
    return target(payload, principal, session, "schedule:write", shift_id)[2]


def snapshot(session, row, result, principal, request, action):
    session.flush()
    session.add(ScheduleEvaluation(organization_id=row.organization_id, shift_id=row.id, actor_id=principal.user.id, shift_revision=row.revision, snapshot=result))
    audit(session, row.organization_id, principal.user.id, action, "calendar_shifts", row.id, request.state.correlation_id,
          {"revision": row.revision, "status": result.get("status"), "digest": result.get("digest")})


@router.post("/calendar", status_code=201)
def create_shift(payload: ShiftSave, request: Request, principal=Depends(require("schedule:write")), session=Depends(get_db)):
    content = payload.model_dump(mode="json")
    existing, pending = idempotency.prepare(session, request, principal, CalendarShift, content)
    if existing:
        if not principal.permits("schedule:write", existing.unit_id):
            fail(403, "FORBIDDEN", "Unidade fora do escopo permitido.")
        return as_dict(existing, SHIFT_FIELDS)
    pure = ShiftInput.model_validate(payload.model_dump(exclude={"preview_digest"}))
    person, dept, result = target(pure, principal, session, "schedule:write")
    if result["digest"] != payload.preview_digest:
        fail(409, "PREVIEW_EXPIRED", "Dados mudaram após a prévia. Avalie novamente antes de salvar.")
    row = CalendarShift(organization_id=person.organization_id, unit_id=dept.unit_id, **pure.model_dump(exclude={"breaks"}), breaks=[p.model_dump(mode="json") for p in pure.breaks], evaluation=result)
    session.add(row)
    snapshot(session, row, result, principal, request, "schedule.create")
    idempotency.record(session, pending, row.id)
    session.commit()
    return as_dict(row, SHIFT_FIELDS)


@router.patch("/calendar/{id}")
def edit_shift(id: str, payload: ShiftEdit, request: Request, principal=Depends(require("schedule:write")), session=Depends(get_db)):
    row = get_scoped(session, CalendarShift, id, principal, "schedule:write", CalendarShift.unit_id)
    # Não permite transferir um plantão para outra pessoa, preservando auditoria e lock.
    if row.employee_id != payload.employee_id or row.state != "draft":
        fail(409, "INVALID_TRANSITION", "Cancele e crie outro plantão para mudar a pessoa.")
    pure = ShiftInput.model_validate(payload.model_dump(exclude={"preview_digest", "revision"}))
    _, dept, result = target(pure, principal, session, "schedule:write", id)
    if result["digest"] != payload.preview_digest:
        fail(409, "PREVIEW_EXPIRED", "Dados mudaram após a prévia. Avalie novamente.")
    values = pure.model_dump(exclude={"breaks"}) | {"breaks": [p.model_dump(mode="json") for p in pure.breaks], "unit_id": dept.unit_id, "evaluation": result}
    changed = session.execute(update(CalendarShift).where(CalendarShift.id == id, CalendarShift.organization_id == principal.user.organization_id,
        CalendarShift.revision == payload.revision, CalendarShift.state == "draft").values(**values, revision=CalendarShift.revision + 1).execution_options(synchronize_session=False))
    if changed.rowcount != 1:
        fail(409, "STALE_VERSION", "Plantão alterado por outra operação. Recarregue.")
    session.refresh(row)
    snapshot(session, row, result, principal, request, "schedule.update")
    session.commit()
    return as_dict(row, SHIFT_FIELDS)


@router.post("/calendar/{id}/cancel")
def cancel_shift(id: str, payload: CancelInput, request: Request, principal=Depends(require("schedule:write")), session=Depends(get_db)):
    row = get_scoped(session, CalendarShift, id, principal, "schedule:write", CalendarShift.unit_id)
    get_scoped(session, Employee, row.employee_id, principal, "schedule:write", Employee.unit_id)
    session.execute(select(Employee.id).where(Employee.id == row.employee_id).with_for_update())
    changed = session.execute(update(CalendarShift).where(CalendarShift.id == id, CalendarShift.organization_id == principal.user.organization_id,
        CalendarShift.revision == payload.revision, CalendarShift.state == "draft").values(state="cancelled", revision=CalendarShift.revision + 1).execution_options(synchronize_session=False))
    if changed.rowcount != 1:
        fail(409, "STALE_VERSION", "Plantão alterado ou já cancelado.")
    session.refresh(row)
    snapshot(session, row, {"status": "cancelled", "previous_evaluation": row.evaluation}, principal, request, "schedule.cancel")
    session.commit()
    return as_dict(row, SHIFT_FIELDS)


@router.get("/calendar/{id}/evaluations")
def evaluations(id: str, principal=Depends(require("schedule:read")), session=Depends(get_db)):
    get_scoped(session, CalendarShift, id, principal, "schedule:read", CalendarShift.unit_id)
    rows = session.scalars(select(ScheduleEvaluation).where(ScheduleEvaluation.organization_id == principal.user.organization_id, ScheduleEvaluation.shift_id == id).order_by(ScheduleEvaluation.shift_revision))
    return {"items": [as_dict(r, ["id", "shift_revision", "created_at", "snapshot"]) for r in rows]}
