"""Capacidade agregada de um mês. Não atribui pessoas a postos nem prova cobertura."""
import hashlib
import json
from collections import Counter
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal, ROUND_FLOOR
from zoneinfo import ZoneInfo
from sqlalchemy import select
from app.api.dependencies import aware, fail
from app.models.entities import (AvailabilityRule, CalendarShift, Contract, Department, Employee,
    EmployeeQualification, EmployeeSkill, RoleQualification, RoleSkill, Unit, WorkPattern)
from app.schemas.scheduling import BreakInput, ShiftInput
from app.services.labor_rules import clipped_total, evaluate, minutes, overlap, segments


def month_after(day, count=1):
    ordinal = day.year * 12 + day.month - 1 + count
    return date(ordinal // 12, ordinal % 12 + 1, 1)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def merge(spans):
    result = []
    for start, end in sorted(spans):
        if start >= end:
            continue
        if result and start <= result[-1][1]:
            result[-1] = (result[-1][0], max(result[-1][1], end))
        else:
            result.append((start, end))
    return result


def subtract(spans, absences):
    result = spans
    for a, b in merge(absences):
        next_result = []
        for s, e in result:
            if not overlap(s, e, a, b):
                next_result.append((s, e))
            else:
                if s < a:
                    next_result.append((s, a))
                if b < e:
                    next_result.append((b, e))
        result = next_result
    return result


def civil(day, clock, tz):
    wall = datetime.combine(day, time.fromisoformat(clock))
    values = {wall.replace(tzinfo=tz, fold=fold).astimezone(UTC) for fold in [0, 1]
              if wall.replace(tzinfo=tz, fold=fold).astimezone(UTC).astimezone(tz).replace(tzinfo=None) == wall}
    if len(values) != 1:
        fail(422, "AMBIGUOUS_TIME", "Horário inexistente ou ambíguo no mês/fuso escolhido. Ajuste o início do turno.")
    return values.pop()


def build_scenario(session, org, payload):
    unit = session.get(Unit, payload.unit_id)
    tz = ZoneInfo(unit.timezone)
    first, last = payload.reference_month, month_after(payload.reference_month)
    begin, end = civil(first, "00:00", tz), civil(last, "00:00", tz)
    people_query = select(Employee).where(Employee.organization_id == org, Employee.unit_id == unit.id, Employee.status == "active").order_by(Employee.id)
    if payload.department_id:
        people_query = people_query.where(Employee.department_id == payload.department_id)
    people = session.scalars(people_query).all()
    if len(people) > 1000:
        fail(422, "COHORT_LIMIT", "Selecione um setor com até 1.000 pessoas nesta simulação síncrona.")
    ids = [p.id for p in people]
    contracts = session.scalars(select(Contract).where(Contract.organization_id == org, Contract.employee_id.in_(ids),
        Contract.valid_from < month_after(first, 12), (Contract.valid_until.is_(None) | (Contract.valid_until > first))).order_by(Contract.employee_id, Contract.valid_from, Contract.id)).all()
    qualifications = session.scalars(select(EmployeeQualification).where(EmployeeQualification.organization_id == org, EmployeeQualification.employee_id.in_(ids))).all()
    skills = session.scalars(select(EmployeeSkill).where(EmployeeSkill.organization_id == org, EmployeeSkill.employee_id.in_(ids))).all()
    role_skills = session.scalars(select(RoleSkill).where(RoleSkill.organization_id == org)).all()
    role_quals = session.scalars(select(RoleQualification).where(RoleQualification.organization_id == org)).all()
    absences = session.scalars(select(AvailabilityRule).where(AvailabilityRule.organization_id == org, AvailabilityRule.employee_id.in_(ids), AvailabilityRule.type == "unavailable",
        AvailabilityRule.start_at < end, AvailabilityRule.end_at > begin)).all()
    shifts = session.scalars(select(CalendarShift).where(CalendarShift.organization_id == org, CalendarShift.employee_id.in_(ids), CalendarShift.state == "draft",
        CalendarShift.start_at < end, CalendarShift.end_at > begin).order_by(CalendarShift.start_at, CalendarShift.id)).all() if payload.mode == "calendar" else []
    if len(shifts) > 2000:
        fail(422, "CALENDAR_LIMIT", "Selecione um setor com até 2.000 plantões no mês para avaliação síncrona.")
    pattern = session.get(WorkPattern, payload.work_pattern_id) if payload.mode == "cycle" else None
    if pattern and (not pattern.configuration or not pattern.configuration.get("cycle") or pattern.configuration.get("shift_minutes", 0) <= payload.break_minutes):
        fail(422, "PATTERN_CONFIGURATION_REQUIRED", "Cadastre um ciclo estruturado e uma duração superior ao intervalo.")
    template = []
    if pattern:
        day = first - timedelta(days=3)
        while day < last:
            cycle = pattern.configuration["cycle"]
            if cycle[(day - payload.cycle_anchor).days % len(cycle)] == "work":
                start = civil(day, payload.start_time, tz)
                finish = start + timedelta(minutes=pattern.configuration["shift_minutes"])
                pauses = []
                if payload.break_minutes:
                    pause_start = start + timedelta(minutes=(pattern.configuration["shift_minutes"] - payload.break_minutes) // 2)
                    pauses = [BreakInput(start_at=pause_start, end_at=pause_start + timedelta(minutes=payload.break_minutes), paid=False)]
                template.append((start, finish, pauses))
            day += timedelta(days=1)
    labor, details, populations, raw_total, payable_total, budget_total = [], [], {}, 0, 0, 0
    flags = Counter()
    for person in people:
        own_contracts = [c for c in contracts if c.employee_id == person.id]
        own_skills = {s.skill_id for s in skills if s.employee_id == person.id}
        own_quals = [q for q in qualifications if q.employee_id == person.id]
        required_skills = {r.skill_id for r in role_skills if r.job_role_id == person.job_role_id}
        required_quals = {r.qualification_id for r in role_quals if r.job_role_id == person.job_role_id}
        missing_skills = bool(required_skills - own_skills)
        person_shifts = [s for s in shifts if s.employee_id == person.id]
        raw, paid, by_department = [], [], {}
        if pattern:
            for a, b, pauses in template:
                pause_json = [p.model_dump(mode="json") for p in pauses]
                raw.extend(segments(a, b, pause_json))
                by_department.setdefault(person.department_id, []).extend(segments(a, b, pause_json))
                paid.extend(segments(a, b, pause_json, include_paid=True))
            if template:
                a, b, pauses = next(((a, b, p) for a, b, p in template if b > begin), template[0])
                proposed = ShiftInput(employee_id=person.id, department_id=person.department_id, start_at=a, end_at=b, breaks=pauses)
                dept = session.get(Department, person.department_id)
                labor.append(evaluate(session, person, dept, proposed))
        else:
            for row in person_shifts:
                raw.extend(segments(aware(row.start_at), aware(row.end_at), row.breaks))
                by_department.setdefault(row.department_id, []).extend(segments(aware(row.start_at), aware(row.end_at), row.breaks))
                paid.extend(segments(aware(row.start_at), aware(row.end_at), row.breaks, include_paid=True))
                proposed = ShiftInput(employee_id=person.id, department_id=row.department_id, start_at=aware(row.start_at), end_at=aware(row.end_at), breaks=row.breaks)
                labor.append(evaluate(session, person, session.get(Department, row.department_id), proposed, row.id))
        own_absences = [(aware(a.start_at), aware(a.end_at)) for a in absences if a.employee_id == person.id]
        raw = subtract(merge([(max(a, begin), min(b, end)) for a, b in raw if overlap(a, b, begin, end)]), own_absences)
        paid = subtract(merge([(max(a, begin), min(b, end)) for a, b in paid if overlap(a, b, begin, end)]), own_absences)
        qualified_spans = []
        weekly_numerator = 0
        day = first
        while day < last:
            left, right = civil(day, "00:00", tz), civil(day + timedelta(days=1), "00:00", tz)
            current = [c for c in own_contracts if c.valid_from <= day and (c.valid_until is None or c.valid_until > day)]
            if len(current) != 1:
                flags["contract_days_missing_or_ambiguous"] += 1
                day += timedelta(days=1)
                continue
            contract = current[0]
            weekly_numerator += min(contract.weekly_minutes, payload.target_weekly_minutes or contract.weekly_minutes)
            if contract.validation_status != "validated":
                flags["contract_days_pending_review"] += 1
            has_quals = all(any(q.qualification_id == ident and q.valid_from <= day < q.valid_until and
                (payload.eligibility == "hypothesis" or q.verification_status == "validated") for q in own_quals) for ident in required_quals)
            if has_quals and not missing_skills:
                qualified_spans.extend((max(a, left), min(b, right)) for a, b in raw if overlap(a, b, left, right))
            else:
                flags["ineligible_person_days"] += 1
            day += timedelta(days=1)
        available = sum(minutes(a, b) for a, b in qualified_spans)
        budget = min(available, weekly_numerator // 7)
        raw_total += sum(minutes(a, b) for a, b in raw)
        payable_total += sum(minutes(a, b) for a, b in paid)
        budget_total += budget
        department_spans = {dept_id: merge([(max(a, s), min(b, e)) for a, b in spans for s, e in qualified_spans if overlap(a, b, s, e)]) for dept_id, spans in by_department.items()}
        populations[person.id] = {"person": person, "spans": qualified_spans, "department_spans": department_spans, "budget": budget, "skills": own_skills, "qualifications": own_quals}
        details.append({"employee_id": person.id, "revision": person.revision, "department_id": person.department_id, "job_role_id": person.job_role_id,
            "available_minutes": available, "contract_budget_minutes": str(Decimal(weekly_numerator) / 7), "contract_budget_floor_minutes": weekly_numerator // 7, "effective_budget_minutes": budget,
            "available_segments": [[a.isoformat(), b.isoformat()] for a, b in raw], "payable_segments": [[a.isoformat(), b.isoformat()] for a, b in paid],
            "eligible_segments": [[a.isoformat(), b.isoformat()] for a, b in qualified_spans],
            "contracts": [{"id": c.id, "weekly_minutes": c.weekly_minutes, "from": str(c.valid_from), "until": str(c.valid_until), "validation_status": c.validation_status} for c in own_contracts],
            "skills": sorted(own_skills), "required_skills": sorted(required_skills), "required_qualifications": sorted(required_quals),
            "qualifications": [{"id": q.id, "qualification_id": q.qualification_id, "from": str(q.valid_from), "until": str(q.valid_until), "verification_status": q.verification_status} for q in own_quals]})
    demand_results = []
    for demand in payload.demands:
        windows, day = [], first - timedelta(days=1)
        while day < last:
            if day.weekday() in demand.weekdays:
                a = civil(day, demand.start_time, tz)
                b = a + timedelta(minutes=demand.duration_minutes)
                if overlap(a, b, begin, end):
                    windows.append((max(a, begin), min(b, end)))
            day += timedelta(days=1)
        required = sum(minutes(a, b) for a, b in windows) * demand.required_staff
        available = 0
        for record in populations.values():
            person = record["person"]
            if demand.department_id not in record["department_spans"] or set(demand.skill_ids) - record["skills"]:
                continue
            contributions = []
            for a, b in windows:
                day = a.astimezone(tz).date()
                while civil(day, "00:00", tz) < b:
                    left, right = max(a, civil(day, "00:00", tz)), min(b, civil(day + timedelta(days=1), "00:00", tz))
                    eligible = all(any(q.qualification_id == ident and q.valid_from <= day < q.valid_until and
                        (payload.eligibility == "hypothesis" or q.verification_status == "validated") for q in record["qualifications"]) for ident in demand.qualification_ids)
                    if eligible:
                        contributions.extend((max(s, left), min(e, right)) for s, e in record["department_spans"][demand.department_id] if overlap(s, e, left, right))
                    day += timedelta(days=1)
            available += min(record["budget"], sum(minutes(s, e) for s, e in merge(contributions)))
        demand_results.append({"name": demand.name, "required_staff_minutes": required, "eligible_upper_bound_minutes": available,
            "gap_lower_bound_minutes": max(0, required - available), "source": demand.source, "validation_status": demand.validation_status})
    required_total = sum(d["required_staff_minutes"] for d in demand_results)
    statuses = Counter(r["status"] for r in labor)
    public = {"algorithm_version": "capacity-1.0", "population_count": len(people), "mode": payload.mode, "eligibility": payload.eligibility, "timezone": unit.timezone,
        "raw_available_minutes": raw_total, "raw_payable_minutes": payable_total, "effective_budget_minutes": budget_total,
        "required_staff_minutes": required_total, "aggregate_gap_lower_bound_minutes": max(0, required_total - budget_total), "demands": demand_results,
        "labor_summary": {"evaluations": len(labor), "statuses": dict(statuses), "scope": "Amostra de um plantão por pessoa" if pattern else "Plantões persistidos no mês, reavaliados"},
        "flags": dict(flags), "validation_status": "pending_review",
        "notices": ["Capacidade agregada e limites inferiores de lacuna não comprovam cobertura por posto/turno.",
            "Pessoas podem ser elegíveis para atividades simultâneas; capacidades por atividade não podem ser somadas.",
            "Orçamento mensal usa limite semanal por dia/7, sem montar escala ou ratear salário por redução de jornada.",
            "Ciclos são hipóteses sincronizadas pela âncora; a amostra LaborRules não avalia a escala hipotética completa." if pattern else "Somente o planejamento já cadastrado contribui para a capacidade.",
            "Contratações financeiras não aumentam esta capacidade automaticamente."]}
    evidence = {"population": details, "labor_evaluations": labor, "pattern": {"id": pattern.id, "configuration": pattern.configuration, "legal_status": pattern.legal_status} if pattern else None,
        "absences": [{"id": a.id, "employee_id": a.employee_id, "start": aware(a.start_at).isoformat(), "end": aware(a.end_at).isoformat()} for a in absences]}
    payroll = {"employees": [{"employee_id": p.id, "contracts": [{"id": c.id, "salary_cents": c.base_salary_cents, "currency": c.currency,
        "valid_from": str(c.valid_from), "valid_until": str(c.valid_until) if c.valid_until else None, "validation_status": c.validation_status,
        "source": c.assumption_source} for c in contracts if c.employee_id == p.id]} for p in people]}
    return public, evidence, payroll
