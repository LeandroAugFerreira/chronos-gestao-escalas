from copy import deepcopy
from datetime import date
from uuid import uuid4
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from app.api.dependencies import fail, get_db, require
from app.api.resources import as_dict, related
from app.api.simulation import check_permission
from app.models.entities import (Contract, Employee, EmployeeQualification, EntityReview, JobRole, OptimizationRun, Qualification,
    ScenarioVersion, ScheduleDecision, ScheduleVersion, WorkPattern, now)
from app.repositories.scoped import get_scoped, page, scoped
from app.schemas.optimization import DecisionInput, OptimizationInput, ReviewInput, RevisionInput
from app.services import idempotency
from app.services.audit import audit
from app.services.capacity import month_after
from app.services.optimization_snapshot import capture, review_digest, signed
from app.services.optimizer import approval_blockers, check_solution, midnight, prepare
from zoneinfo import ZoneInfo

router = APIRouter(prefix="/api/v1", tags=["Otimização e propostas de escala"])


def run_view(row, principal, detail=False):
    result = as_dict(row, ["id", "unit_id", "scenario_id", "actor_id", "name", "created_at", "state", "revision",
        "cancel_requested", "attempts", "started_at", "finished_at", "heartbeat_at", "input_digest", "error_code"])
    if detail:
        result.update(inputs=deepcopy(row.inputs), result=deepcopy(row.result))
        if not principal.permits("finance:read", row.unit_id):
            result["inputs"].pop("cost_source", None)
            for template in result["inputs"]["templates"]:
                template.pop("cost_cents", None)
            result["result"].pop("estimated_cost_cents", None)
            if row.inputs.get("cost_weight"):
                for stage in result["result"].get("stages", []):
                    if stage["stage"] == "cost_balance_preferences":
                        stage.pop("objective", None); stage.pop("best_bound", None)
        if not principal.permits("people:read", row.unit_id):
            result["result"].pop("assignments", None)
    return result


def schedule_view(row, principal, detail=False):
    result = as_dict(row, ["id", "unit_id", "run_id", "parent_id", "series_id", "version", "name", "state", "revision", "digest", "created_at"])
    if detail:
        result.update(payload=deepcopy(row.payload), verification=deepcopy(row.verification))
        if not principal.permits("people:read", row.unit_id):
            result["payload"].pop("assignments", None)
    return result


@router.post("/optimization", status_code=202)
def enqueue(payload: OptimizationInput, request: Request, principal=Depends(require("optimization:write")), session=Depends(get_db)):
    scenario = get_scoped(session, ScenarioVersion, payload.scenario_id, principal, "scenario:read", ScenarioVersion.unit_id)
    for permission in ["optimization:write", "people:read", "schedule:read"]:
        check_permission(principal, permission, scenario.unit_id)
    if payload.start_date < scenario.reference_month or payload.end_date > month_after(scenario.reference_month):
        fail(422, "INVALID_HORIZON", "Use um horizonte dentro do mês do cenário, com fim exclusivo.")
    if not scenario.inputs["demands"]:
        fail(422, "NO_DEMAND", "Cadastre atividades e demanda no cenário.")
    for index, ids in payload.activity_job_role_ids.items():
        if not 0 <= index < len(scenario.inputs["demands"]) or not ids or len(ids) != len(set(ids)):
            fail(422, "INVALID_REFERENCE", "Mapeamento de atividades e cargos inválido.")
        for ident in ids:
            related(session, JobRole, ident, principal)
    for ident in payload.cycle_anchors:
        related(session, WorkPattern, ident, principal)
    if payload.cost_weight or any(t.cost_cents for t in payload.templates):
        check_permission(principal, "finance:read", scenario.unit_id)
    if payload.parent_schedule_id:
        parent = get_scoped(session, ScheduleVersion, payload.parent_schedule_id, principal, "optimization:write", ScheduleVersion.unit_id)
        old = session.get(OptimizationRun, parent.run_id)
        if parent.unit_id != scenario.unit_id or any(old.inputs[k] != payload.model_dump(mode="json")[k] for k in ["start_date", "end_date"]) or old.snapshot["scenario"]["department_id"] != scenario.department_id:
            fail(422, "INVALID_SUCCESSOR", "Uma nova versão exige mesma unidade, população e horizonte.")
        if sorted(p["employee_id"] for p in scenario.evidence["population"]) != sorted(p["id"] for p in old.snapshot["facts"]["employees"]):
            fail(422, "INVALID_SUCCESSOR", "A população deve ser a mesma na nova versão.")
        if parent.state == "superseded":
            fail(409, "SUPERSEDED_PARENT", "Derive a versão aprovada mais recente.")
    options = payload.model_dump(mode="json")
    snapshot = capture(session, scenario, options)
    unit = next(u for u in snapshot["facts"]["units"] if u["id"] == scenario.unit_id)
    begin, end = midnight(payload.start_date, ZoneInfo(unit["timezone"])), midnight(payload.end_date, ZoneInfo(unit["timezone"]))
    for window in payload.coverage_windows:
        if window.activity_index >= len(scenario.inputs["demands"]) or window.start_at < begin or window.end_at > end:
            fail(422, "INVALID_COVERAGE_WINDOW", "Janela fora do horizonte ou atividade inexistente.")
    existing, pending = idempotency.prepare(session, request, principal, OptimizationRun, options)
    if existing:
        return run_view(existing, principal, True)
    row = OptimizationRun(organization_id=scenario.organization_id, unit_id=scenario.unit_id, scenario_id=scenario.id,
        actor_id=principal.user.id, name=payload.name, inputs=options, snapshot=snapshot,
        input_digest=signed(snapshot, request.app.state.settings.jwt_secret.get_secret_value()))
    session.add(row); session.flush()
    idempotency.record(session, pending, row.id)
    audit(session, row.organization_id, principal.user.id, "optimization.enqueue", row.__tablename__, row.id, request.state.correlation_id, {"digest": row.input_digest})
    session.commit()
    return run_view(row, principal, True)


@router.get("/optimization")
def runs(unit_id: str | None = None, page_number: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), principal=Depends(require("optimization:read")), session=Depends(get_db)):
    query = scoped(OptimizationRun, principal, "optimization:read", OptimizationRun.unit_id)
    if unit_id:
        query = query.where(OptimizationRun.unit_id == unit_id)
    return page(session, query.order_by(OptimizationRun.created_at.desc(), OptimizationRun.id), page_number, page_size, lambda row: run_view(row, principal))


@router.get("/optimization/{id}")
def run(id: str, principal=Depends(require("optimization:read")), session=Depends(get_db)):
    row = get_scoped(session, OptimizationRun, id, principal, "optimization:read", OptimizationRun.unit_id)
    result = run_view(row, principal, True)
    result["schedule_id"] = session.scalar(select(ScheduleVersion.id).where(ScheduleVersion.run_id == row.id, ScheduleVersion.organization_id == row.organization_id))
    return result


@router.post("/optimization/{id}/cancel")
def cancel(id: str, payload: RevisionInput, request: Request, principal=Depends(require("optimization:write")), session=Depends(get_db)):
    row = get_scoped(session, OptimizationRun, id, principal, "optimization:write", OptimizationRun.unit_id)
    # The organization lock also coordinates worker finalization.
    session.refresh(row)
    if row.revision != payload.revision or row.state not in {"queued", "running"}:
        fail(409, "REVISION_CONFLICT", "Atualize o processamento antes de cancelar.")
    row.cancel_requested = True; row.revision += 1
    if row.state == "queued":
        row.state = "cancelled"; row.finished_at = now()
    audit(session, row.organization_id, principal.user.id, "optimization.cancel", row.__tablename__, row.id, request.state.correlation_id)
    session.commit()
    return run_view(row, principal, True)


@router.get("/schedules")
def schedules(unit_id: str | None = None, page_number: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), principal=Depends(require("optimization:read")), session=Depends(get_db)):
    query = scoped(ScheduleVersion, principal, "optimization:read", ScheduleVersion.unit_id)
    if unit_id:
        query = query.where(ScheduleVersion.unit_id == unit_id)
    return page(session, query.order_by(ScheduleVersion.created_at.desc(), ScheduleVersion.id), page_number, page_size, lambda row: schedule_view(row, principal))


@router.get("/schedules/{id}")
def schedule(id: str, principal=Depends(require("optimization:read")), session=Depends(get_db)):
    row = get_scoped(session, ScheduleVersion, id, principal, "optimization:read", ScheduleVersion.unit_id)
    result = schedule_view(row, principal, True)
    result["decisions"] = [as_dict(d, ["id", "actor_id", "action", "reason", "schedule_digest", "input_digest", "created_at"]) for d in session.scalars(select(ScheduleDecision).where(ScheduleDecision.organization_id == row.organization_id, ScheduleDecision.schedule_id == row.id).order_by(ScheduleDecision.created_at, ScheduleDecision.id))]
    return result


@router.post("/schedules/{id}/decision")
def decision(id: str, payload: DecisionInput, request: Request, principal=Depends(require("optimization:read")), session=Depends(get_db)):
    row = get_scoped(session, ScheduleVersion, id, principal, "optimization:read", ScheduleVersion.unit_id)
    check_permission(principal, "optimization:write" if payload.action == "submit" else "schedule:approve", row.unit_id)
    if row.revision != payload.revision or row.digest != payload.schedule_digest:
        fail(409, "REVISION_CONFLICT", "Proposta foi alterada; atualize a tela.")
    if payload.action == "submit" and row.state != "draft" or payload.action in {"approve", "reject"} and row.state != "submitted":
        fail(409, "INVALID_TRANSITION", "Transição indisponível para esta proposta.")
    run = session.get(OptimizationRun, row.run_id)
    if payload.action == "approve" and principal.user.id == run.actor_id:
        fail(403, "SECOND_REVIEWER_REQUIRED", "Outro responsável deve aprovar a proposta.")
    secret = request.app.state.settings.jwt_secret.get_secret_value()
    if payload.action != "reject":
        scenario = session.get(ScenarioVersion, run.scenario_id)
        if signed(capture(session, scenario, run.inputs), secret) != run.input_digest:
            fail(409, "STALE_INPUTS", "Dados mudaram desde o cálculo. Gere uma nova versão.")
        data = prepare(deepcopy(run.snapshot))
        ids = [a["candidate_id"] for a in row.payload["assignments"]]
        check = check_solution(data, ids)
        blocked = approval_blockers(data, ids)
        # Bind the independently checked identifiers to the complete immutable payload.
        if signed(row.payload, secret) != row.digest or row.payload["assignments"] != run.result.get("assignments"):
            fail(409, "INVALID_PROPOSAL", "Conteúdo da proposta não corresponde ao cálculo.")
        if not check["valid"] or check.get("uncovered_staff_minutes") or blocked:
            fail(409, "APPROVAL_BLOCKED", "Resolva as premissas e lacunas em uma nova execução antes de submeter.")
    if payload.action == "approve" and row.parent_id:
        parent = session.get(ScheduleVersion, row.parent_id)
        if parent.state == "superseded":
            fail(409, "SUPERSEDED_PARENT", "Uma outra versão já substituiu esta proposta.")
        if parent.state == "approved":
            parent.state = "superseded"; parent.revision += 1
    row.state = {"submit": "submitted", "approve": "approved", "reject": "rejected"}[payload.action]
    row.revision += 1
    session.add(ScheduleDecision(organization_id=row.organization_id, schedule_id=row.id, actor_id=principal.user.id,
        action=payload.action, reason=payload.reason, schedule_digest=row.digest, input_digest=run.input_digest))
    audit(session, row.organization_id, principal.user.id, "schedule." + payload.action, row.__tablename__, row.id, request.state.correlation_id, {"digest": row.digest})
    session.commit()
    return schedule_view(row, principal, True)


REVIEW_MODELS = {"contract": Contract, "work_pattern": WorkPattern, "qualification": EmployeeQualification, "scenario": ScenarioVersion}


def review_unit(session, row):
    if isinstance(row, WorkPattern):
        return None
    if isinstance(row, (Contract, EmployeeQualification)):
        return session.get(Employee, row.employee_id).unit_id
    return row.unit_id


@router.get("/optimization-review-targets")
def targets(kind: str, request: Request, unit_id: str | None = None, page_number: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), principal=Depends(require("rules:write")), session=Depends(get_db)):
    if kind not in REVIEW_MODELS:
        fail(422, "INVALID_KIND", "Tipo de revisão inválido.")
    model = REVIEW_MODELS[kind]
    # Global catalogs can only be reviewed with a global grant.
    if kind == "work_pattern" and not principal.permits("rules:write"):
        fail(403, "FORBIDDEN", "Revisão de catálogo exige permissão global.")
    query = select(model).where(model.organization_id == principal.user.organization_id)
    if kind in {"contract", "qualification"}:
        permission = "finance:read" if kind == "contract" else "people:read"
        employee_query = scoped(Employee, principal, permission, Employee.unit_id)
        if unit_id:
            employee_query = employee_query.where(Employee.unit_id == unit_id)
        query = query.where(model.employee_id.in_(employee_query.with_only_columns(Employee.id)))
    elif kind == "scenario":
        query = scoped(model, principal, "scenario:read", model.unit_id)
        if unit_id:
            query = query.where(model.unit_id == unit_id)
    secret = request.app.state.settings.jwt_secret.get_secret_value()
    def view(row):
        name = getattr(row, "name", row.id)
        if isinstance(row, (Contract, EmployeeQualification)):
            person = session.get(Employee, row.employee_id)
            subject = session.get(WorkPattern, row.work_pattern_id).name if isinstance(row, Contract) else session.get(Qualification, row.qualification_id).name
            name = f"{person.name} · {subject} · desde {row.valid_from}"
        return {"id": row.id, "name": name, "kind": kind,
            "entity_digest": review_digest(row, secret), "status": getattr(row, "validation_status", getattr(row, "verification_status", getattr(row, "legal_status", "immutable")))}
    return page(session, query.order_by(model.id), page_number, page_size, view)


@router.post("/optimization-reviews", status_code=201)
def review(payload: ReviewInput, request: Request, principal=Depends(require("rules:write")), session=Depends(get_db)):
    row = related(session, REVIEW_MODELS[payload.kind], payload.entity_id, principal)
    unit = review_unit(session, row)
    check_permission(principal, "rules:write", unit)
    if payload.kind in {"contract", "qualification"}:
        check_permission(principal, "people:write", unit)
    if payload.kind == "contract":
        check_permission(principal, "finance:read", unit)
    if payload.kind == "scenario":
        check_permission(principal, "scenario:read", unit)
    secret = request.app.state.settings.jwt_secret.get_secret_value()
    if review_digest(row, secret) != payload.entity_digest:
        fail(409, "STALE_REVIEW", "O registro mudou. Revise o conteúdo atual antes de confirmar.")
    if payload.kind == "contract":
        row.validation_status = "validated"; row.assumption_source = payload.source
    elif payload.kind == "qualification":
        row.verification_status = "validated"; row.evidence = payload.evidence
    elif payload.kind == "work_pattern":
        if not row.configuration.get("cycle"):
            fail(422, "PATTERN_UNSTRUCTURED", "Configure o ciclo da jornada antes da revisão.")
        row.legal_status = "validated"
        row.revision += 1
    session.flush()
    annotation = EntityReview(organization_id=row.organization_id, unit_id=unit, actor_id=principal.user.id, entity_kind=payload.kind,
        entity_id=row.id, entity_digest=review_digest(row, secret), source=payload.source, evidence=payload.evidence)
    session.add(annotation); session.flush()
    audit(session, row.organization_id, principal.user.id, "optimization.review", annotation.__tablename__, annotation.id, request.state.correlation_id, {"kind": payload.kind, "entity_id": row.id})
    session.commit()
    return {"id": annotation.id, "entity_digest": annotation.entity_digest, "scope": "Revisão humana registrada; não certifica validade jurídica."}
