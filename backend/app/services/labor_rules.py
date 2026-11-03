"""Avaliadores tipados; intervalos [início,fim), minutos UTC e dias civis locais.

Avalia planejamento conhecido, sem certificar ponto realizado ou legislação completa.
Nenhuma expressão executável é aceita no cadastro de regras.
"""
import hashlib
import json
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy import select
from app.api.dependencies import aware
from app.models.entities import (AvailabilityRule, CalendarShift, Contract, EmployeeQualification,
    EmployeeSkill, LaborRule, RoleQualification, RoleSkill, Unit, WorkPattern)

LABELS = {"conform": "Conforme com as regras configuradas", "nonconform": "Não conforme com as regras configuradas",
          "pending": "Pendente de validação jurídica", "missing": "Não avaliado por ausência de regra aplicável"}
KINDS = {"max_daily", "max_weekly", "min_break", "min_rest", "min_weekly_rest"}


def minutes(a, b):
    return int((b - a).total_seconds() // 60)


def overlap(a, b, c, d):
    return a < d and c < b


def segments(start, end, breaks, include_paid=False):
    cursor = start
    result = []
    for pause in breaks:
        a, b = datetime.fromisoformat(pause["start_at"]), datetime.fromisoformat(pause["end_at"])
        if include_paid and pause["paid"]:
            continue
        if cursor < a:
            result.append((cursor, a))
        cursor = b
    if cursor < end:
        result.append((cursor, end))
    return result


def clipped_total(spans, a, b):
    return sum(minutes(max(start, a), min(end, b)) for start, end in spans if overlap(start, end, a, b))


def evaluate(session, employee, department, payload, exclude_id=None):
    org = employee.organization_id
    start, end = payload.start_at, payload.end_at
    tz = ZoneInfo(session.get(Unit, department.unit_id).timezone)
    pauses = [p.model_dump(mode="json") for p in payload.breaks]
    working = segments(start, end, pauses)
    payable = segments(start, end, pauses, include_paid=True)
    shifts = session.scalars(select(CalendarShift).where(CalendarShift.organization_id == org,
        CalendarShift.employee_id == employee.id, CalendarShift.state == "draft").order_by(CalendarShift.start_at, CalendarShift.id)).all()
    shifts = [s for s in shifts if s.id != exclude_id]
    # Histórico completo conhecido da pessoa, inclusive antes/depois da janela exibida.
    occupied = [(aware(s.start_at), aware(s.end_at)) for s in shifts] + [(start, end)]
    work = list(working)
    for row in shifts:
        work.extend(segments(aware(row.start_at), aware(row.end_at), row.breaks))
    contracts = session.scalars(select(Contract).where(Contract.organization_id == org, Contract.employee_id == employee.id)).all()
    first_day, last_day = start.astimezone(tz).date(), (end - timedelta(microseconds=1)).astimezone(tz).date()
    applicable_contracts = [c for c in contracts if c.valid_from <= last_day and (c.valid_until is None or c.valid_until > first_day)]
    rules = session.scalars(select(LaborRule).where(LaborRule.organization_id == org).order_by(LaborRule.key, LaborRule.version)).all()
    successors = {r.supersedes_id: r for r in rules if r.supersedes_id}
    rules = [r for r in rules if (r.unit_id is None or r.unit_id == department.unit_id)
             and (r.job_role_id is None or r.job_role_id == employee.job_role_id)
             and (r.contract_id is None or r.contract_id in {c.id for c in applicable_contracts})]
    def effective_range(rule):
        left, right = aware(rule.valid_from), aware(rule.valid_until)
        if rule.id in successors:
            right = min(right, aware(successors[rule.id].valid_from))
        if rule.contract_id:
            contract = next(c for c in applicable_contracts if c.id == rule.contract_id)
            left = max(left, datetime.combine(contract.valid_from, time.min, tz).astimezone(UTC))
            if contract.valid_until:
                right = min(right, datetime.combine(contract.valid_until, time.min, tz).astimezone(UTC))
        return left, right
    rules = [r for r in rules if effective_range(r)[1] > effective_range(r)[0] and overlap(start, end, *effective_range(r))]
    findings = []

    def add(code, status, message, **evidence):
        findings.append({"code": code, "status": status, "message": message, "evidence": evidence})

    if employee.status != "active":
        add("EMPLOYEE_INACTIVE", "nonconform", "Colaborador inativo.")
    for row in shifts:
        if overlap(start, end, aware(row.start_at), aware(row.end_at)):
            add("SHIFT_OVERLAP", "nonconform", "Plantões sobrepostos, mesmo que em outro setor.", shift_id=row.id)
    unavailable = session.scalars(select(AvailabilityRule).where(AvailabilityRule.organization_id == org,
        AvailabilityRule.employee_id == employee.id, AvailabilityRule.type == "unavailable",
        AvailabilityRule.start_at < end, AvailabilityRule.end_at > start)).all()
    for row in unavailable:
        add("UNAVAILABLE", "nonconform", "Plantão coincide com indisponibilidade.", id=row.id, start=aware(row.start_at).isoformat(), end=aware(row.end_at).isoformat())
    cursor = first_day
    while cursor <= last_day:
        current = [c for c in applicable_contracts if c.valid_from <= cursor and (c.valid_until is None or cursor < c.valid_until)]
        if len(current) != 1:
            add("CONTRACT_SCOPE", "pending", "Contrato ausente ou ambíguo no dia.", day=str(cursor))
        elif current[0].validation_status != "validated" or session.get(WorkPattern, current[0].work_pattern_id).legal_status != "validated":
            add("CONTRACT_REVIEW", "pending", "Contrato ou regime aguarda revisão.", day=str(cursor), contract_id=current[0].id)
        cursor += timedelta(days=1)
    # Limite contratual preservado mesmo quando a interpretação normativa está pendente.
    for contract in applicable_contracts:
        monday = first_day - timedelta(days=first_day.weekday())
        while monday <= last_day:
            left = datetime.combine(monday, time.min, tz).astimezone(UTC)
            right = datetime.combine(monday + timedelta(days=7), time.min, tz).astimezone(UTC)
            actual = clipped_total(work, left, right)
            add("CONTRACT_WEEKLY", "conform" if actual <= contract.weekly_minutes else "nonconform", "Comparação com carga semanal contratada, sem compensação automática.",
                contract_id=contract.id, actual_minutes=actual, limit_minutes=contract.weekly_minutes, week=str(monday))
            monday += timedelta(days=7)
    required_skills = set(session.scalars(select(RoleSkill.skill_id).where(RoleSkill.organization_id == org, RoleSkill.job_role_id == employee.job_role_id)))
    actual_skills = set(session.scalars(select(EmployeeSkill.skill_id).where(EmployeeSkill.organization_id == org, EmployeeSkill.employee_id == employee.id)))
    for skill in sorted(required_skills - actual_skills):
        add("SKILL_MISSING", "nonconform", "Competência exigida pela função ausente.", skill_id=skill)
    required_quals = set(session.scalars(select(RoleQualification.qualification_id).where(RoleQualification.organization_id == org, RoleQualification.job_role_id == employee.job_role_id)))
    qualifications = session.scalars(select(EmployeeQualification).where(EmployeeQualification.organization_id == org, EmployeeQualification.employee_id == employee.id)).all()
    for q in sorted(required_quals):
        valid = [r for r in qualifications if r.qualification_id == q and r.valid_from <= first_day and r.valid_until > last_day]
        if not valid:
            add("QUALIFICATION_MISSING", "nonconform", "Habilitação ausente ou vencida no plantão.", qualification_id=q)
        elif not any(r.verification_status == "validated" for r in valid):
            add("QUALIFICATION_REVIEW", "pending", "Habilitação sintética ou sem comprovação validada.", qualification_id=q)
    boundaries = sorted({start, end, *[t for r in rules for t in effective_range(r) if start < t < end]})
    for a, b in zip(boundaries, boundaries[1:]):
        for kind in sorted(KINDS):
            active = [r for r in rules if r.kind == kind and effective_range(r)[0] <= a and effective_range(r)[1] >= b]
            if not active:
                add("RULE_MISSING", "missing", "Não existe regra aplicável para esta família e vigência.", kind=kind, start=a.isoformat(), end=b.isoformat())
            if len({(r.minutes, r.threshold_minutes) for r in active}) > 1:
                add("RULE_CONFLICT", "pending", "Parâmetros divergentes: todas as evidências são preservadas, sem precedência automática.", kind=kind, rules=[r.id for r in active])
    for rule in rules:
        evidence = {"rule_id": rule.id, "key": rule.key, "version": rule.version, "source": rule.source,
                    "limit_minutes": rule.minutes, "valid_from": aware(rule.valid_from).isoformat(), "valid_until": aware(rule.valid_until).isoformat()}
        if rule.status != "validated":
            add("RULE_REVIEW", "pending", "Regra pendente de revisão; cálculo é hipótese.", **evidence)
        a, b = max(start, effective_range(rule)[0]), min(end, effective_range(rule)[1])
        checks = []
        if rule.kind in {"max_daily", "max_weekly", "min_weekly_rest"}:
            day = a.astimezone(tz).date()
            if rule.kind != "max_daily":
                day -= timedelta(days=day.weekday())
            while datetime.combine(day, time.min, tz).astimezone(UTC) < b:
                left = datetime.combine(day, time.min, tz).astimezone(UTC)
                right = datetime.combine(day + timedelta(days=1 if rule.kind == "max_daily" else 7), time.min, tz).astimezone(UTC)
                if effective_range(rule)[0] > left or effective_range(rule)[1] < right:
                    add("WINDOW_TRANSITION", "pending", "Vigência parcial na janela: comparação conservadora sem rateio automático; revisão necessária.", window=str(day), **evidence)
                if rule.kind == "min_weekly_rest":
                    intervals = sorted((max(s, left), min(e, right)) for s, e in occupied if overlap(s, e, left, right))
                    cursor, gaps = left, []
                    for s, e in intervals:
                        gaps.append(max(0, minutes(cursor, s)))
                        cursor = max(cursor, e)
                    actual = max([*gaps, max(0, minutes(cursor, right))])
                    checks.append((actual >= rule.minutes, actual, str(day)))
                else:
                    actual = clipped_total(work, left, right)
                    checks.append((actual <= rule.minutes, actual, str(day)))
                day += timedelta(days=1 if rule.kind == "max_daily" else 7)
        elif rule.kind == "min_break":
            merged = []
            for pause in payload.breaks:
                if merged and merged[-1][1] == pause.start_at:
                    merged[-1] = (merged[-1][0], pause.end_at)
                else:
                    merged.append((pause.start_at, pause.end_at))
            actual = max([minutes(s, e) for s, e in merged] or [0])
            checks.append((sum(minutes(s, e) for s, e in working) <= rule.threshold_minutes or actual >= rule.minutes, actual, "plantão"))
        elif rule.kind == "min_rest":
            before = [e for s, e in occupied[:-1] if e <= start]
            after = [s for s, e in occupied[:-1] if s >= end]
            if before:
                actual = minutes(max(before), start)
                checks.append((actual >= rule.minutes, actual, "anterior"))
            if after:
                actual = minutes(end, min(after))
                checks.append((actual >= rule.minutes, actual, "posterior"))
            if not before and not after:
                add("REST_HISTORY", "pending", "Sem plantão adjacente conhecido; descanso real não comprovado.", **evidence)
        for ok, actual, window in checks:
            add(rule.kind.upper(), "conform" if ok else "nonconform", "Critério atendido." if ok else "Limite configurado violado.", actual_minutes=actual, window=window, **evidence)
    statuses = {f["status"] for f in findings}
    status = next((s for s in ["nonconform", "pending", "missing"] if s in statuses), "conform")
    # Informações suficientes para detectar qualquer alteração relevante no preview.
    result = {"status": status, "label": LABELS[status], "findings": findings,
        "actual_minutes": sum(minutes(s, e) for s, e in working), "payable_minutes": sum(minutes(s, e) for s, e in payable),
        "elapsed_minutes": minutes(start, end), "timezone": str(tz), "scope": "Planejamento conhecido; sem certificação jurídica ou cálculo de adicional/hora noturna.",
        "input": payload.model_dump(mode="json"), "employee_revision": employee.revision, "department_revision": department.revision,
        "history": [{"id": s.id, "revision": s.revision} for s in shifts],
        "rules": [{"id": r.id, "key": r.key, "version": r.version, "kind": r.kind, "minutes": r.minutes, "threshold_minutes": r.threshold_minutes,
                   "status": r.status, "source": r.source, "supersedes_id": r.supersedes_id, "effective_from": effective_range(r)[0].isoformat(), "effective_until": effective_range(r)[1].isoformat(), "agreement": r.agreement, "unit_id": r.unit_id, "job_role_id": r.job_role_id, "contract_id": r.contract_id, "reviewer_id": r.reviewer_id, "review_evidence": r.review_evidence,
                   "valid_from": aware(r.valid_from).isoformat(), "valid_until": aware(r.valid_until).isoformat()} for r in rules],
        "contracts": [{"id": c.id, "status": c.validation_status, "weekly_minutes": c.weekly_minutes, "pattern": c.work_pattern_id, "from": str(c.valid_from), "until": str(c.valid_until)} for c in applicable_contracts]}
    result["digest"] = hashlib.sha256(json.dumps(result, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return result
