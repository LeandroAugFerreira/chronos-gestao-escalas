"""Captura de fatos atuais e vínculo explícito com a população congelada do cenário."""
import hashlib
import hmac
from datetime import date, datetime
from sqlalchemy import inspect, select
from app.api.dependencies import aware, fail
from app.models.entities import (AvailabilityRule, CalendarShift, Contract, Department, Employee, EmployeeQualification,
    EmployeeSkill, EntityReview, JobRole, LaborRule, Organization, Qualification, RoleQualification, RoleSkill,
    ScenarioVersion, ScheduleVersion, Skill, Unit, WorkPattern)
from app.services.capacity import digest


def record(row, exclude=()):
    result = {}
    for column in inspect(type(row)).column_attrs:
        if column.key in exclude:
            continue
        value = getattr(row, column.key)
        result[column.key] = aware(value).isoformat() if isinstance(value, datetime) else value.isoformat() if isinstance(value, date) else value
    return result


def signed(value, secret):
    return hmac.new(secret.encode(), digest(value).encode(), hashlib.sha256).hexdigest()


def capture(session, scenario, options):
    org = scenario.organization_id
    ids = sorted(p["employee_id"] for p in scenario.evidence["population"])
    if len(ids) > 500:
        fail(422, "MODEL_LIMIT", "Escolha uma população de até 500 pessoas para o worker local.")
    models = [Organization, Unit, Department, Employee, Contract, WorkPattern, EmployeeSkill, EmployeeQualification,
              RoleSkill, RoleQualification, Qualification, JobRole, Skill, AvailabilityRule, CalendarShift, LaborRule]
    facts = {}
    for model in models:
        query = select(model).where(model.id == org) if model is Organization else select(model).where(model.organization_id == org)
        if model is Employee:
            query = query.where(Employee.id.in_(ids))
        if model in {Contract, EmployeeSkill, EmployeeQualification, AvailabilityRule, CalendarShift}:
            query = query.where(model.employee_id.in_(ids))
        rows = session.scalars(query.order_by(model.id)).all()
        if len(rows) > 20000:
            fail(422, "MODEL_LIMIT", "Quantidade de fatos excede o limite do worker local.")
        facts[model.__tablename__] = [record(row, {"base_salary_cents", "currency", "fixture_hash"}) for row in rows]
    reviews = session.scalars(select(EntityReview).where(EntityReview.organization_id == org, EntityReview.entity_kind == "scenario", EntityReview.entity_id == scenario.id).order_by(EntityReview.id)).all()
    facts["scenario_reviews"] = [record(r) for r in reviews]
    approved = session.scalars(select(ScheduleVersion).where(ScheduleVersion.organization_id == org, ScheduleVersion.state == "approved").order_by(ScheduleVersion.id)).all()
    facts["approved_schedules"] = [{"id": r.id, "unit_id": r.unit_id, "digest": r.digest, "revision": r.revision,
        "assignments": [a for a in r.payload["assignments"] if a["employee_id"] in ids]} for r in approved]
    return {"algorithm_version": "chronos-cpsat-1.0", "scenario": {"id": scenario.id, "unit_id": scenario.unit_id,
        "department_id": scenario.department_id, "digest": scenario.digest, "inputs": scenario.inputs}, "options": options, "facts": facts}


def review_digest(row, secret):
    if isinstance(row, ScenarioVersion):
        return row.digest
    return signed(record(row), secret)
