"""Importação idempotente e restauração restrita da demonstração, em transação."""

import hashlib
import json
import re
from datetime import UTC, date, datetime
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import delete, select

from app.core.security import ROLE_PERMISSIONS, hash_password
from app.models.entities import (AvailabilityRule, Contract, Department, Employee, EmployeeQualification,
    EmployeeSkill, JobRole, Organization, Permission, Qualification, Role, RolePermission, RoleQualification,
    RoleSkill, Skill, Unit, User, UserRole, WorkPattern)
from app.services.audit import audit


def demo_id(value):
    return str(uuid5(NAMESPACE_URL, "chronos/horizonte/" + value))


def init_rbac(session):
    for name, codes in ROLE_PERMISSIONS.items():
        role = session.scalar(select(Role).where(Role.name == name))
        if not role:
            role = Role(id=str(uuid5(NAMESPACE_URL, "chronos/role/" + name)), name=name)
            session.add(role)
            session.flush()
        for code in sorted(codes):
            permission = session.scalar(select(Permission).where(Permission.code == code))
            if not permission:
                permission = Permission(id=str(uuid5(NAMESPACE_URL, "chronos/permission/" + code)), code=code)
                session.add(permission)
                session.flush()
            if session.get(RolePermission, (role.id, permission.id)) is None:
                session.add(RolePermission(role_id=role.id, permission_id=permission.id))
    session.flush()


def seed_demo(session, data):
    org_id = demo_id("organization")
    fingerprint = hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    org = session.get(Organization, org_id)
    if org:
        if not org.is_demo or org.slug != "horizonte":
            raise ValueError("Destino não é a demonstração esperada")
        if org.fixture_hash == fingerprint:
            from app.services.automation_events import ensure_definitions
            ensure_definitions(session, org.id)
            return org, False  # Não sobrescrever alterações manuais em uma reexecução.
        if org.fixture_hash:
            raise ValueError("Fixture mudou; revise e use restauração explícita da demonstração")
    else:
        org = Organization(id=org_id, slug="horizonte", name=data["organization"]["name"], segment="hospital", operation="24x7", is_demo=True)
        session.add(org)
        session.flush()
    def insert(model, rows):
        for row in rows:
            if model is Unit and (existing := session.get(Unit, row["id"])):
                if existing.organization_id != org_id:
                    raise ValueError("Unidade fora da organização")
                for key, value in row.items():
                    setattr(existing, key, value)
                continue
            session.add(model(organization_id=org_id, **row))
        session.flush()
    insert(Unit, [{"id": demo_id(r["id"]), "name": r["name"], "operation": r["operation"]} for r in data["units"]])
    insert(Department, [{"id": demo_id(r["id"]), "unit_id": demo_id(r["unit_id"]), "name": r["name"], "group": r["group"], "operation": r["operation"], "cost_center": r["cost_center"]} for r in data["departments"]])
    for model, key in [(JobRole, "job_roles"), (Skill, "skills"), (Qualification, "qualifications")]:
        insert(model, [{"id": demo_id(r["id"]), "name": r["name"]} for r in data[key]])
    insert(WorkPattern, [{"id": demo_id(r["id"]), "name": r["name"], "description": r["description"], "legal_status": r["legal_status"]} for r in data["work_patterns"]])
    for role in data["job_roles"]:
        insert(RoleSkill, [{"job_role_id": demo_id(role["id"]), "skill_id": demo_id(s)} for s in role["required_skill_ids"]])
        insert(RoleQualification, [{"job_role_id": demo_id(role["id"]), "qualification_id": demo_id(s)} for s in role["required_qualification_ids"]])
    insert(Employee, [{"id": demo_id(r["id"]), "unit_id": demo_id(r["unit_id"]), "department_id": demo_id(r["department_id"]),
        "job_role_id": demo_id(r["job_role_id"]), "name": r["name"], "registration": r["registration"], "synthetic": True,
        "preferences": {"preferred_shift": r["preferred_shift"], "preferred_days_off": r["preferred_days_off"]}} for r in data["employees"]])
    insert(EmployeeSkill, [{"employee_id": demo_id(r["id"]), "skill_id": demo_id(s)} for r in data["employees"] for s in r["skill_ids"]])
    insert(EmployeeQualification, [{"id": demo_id(r["id"]), "employee_id": demo_id(r["employee_id"]), "qualification_id": demo_id(r["qualification_id"]),
        "valid_from": date.fromisoformat(r["valid_from"]), "valid_until": date.fromisoformat(r["valid_until"]), "verification_status": r["verification_status"], "evidence": r["evidence"]} for r in data["employee_qualifications"]])
    insert(Contract, [{"id": demo_id(r["id"]), "employee_id": demo_id(r["employee_id"]), "work_pattern_id": demo_id(r["work_pattern_id"]),
        "weekly_minutes": r["weekly_minutes"], "base_salary_cents": r["base_salary_cents"], "employment_type": r["employment_type"],
        "valid_from": date.fromisoformat(r["valid_from"]), "validation_status": r["validation_status"], "assumption_source": r["assumption_source"]} for r in data["contracts"]])
    insert(AvailabilityRule, [{"id": demo_id(r["id"]), "employee_id": demo_id(r["employee_id"]), "start_at": datetime.fromisoformat(r["start"]).astimezone(UTC),
        "end_at": datetime.fromisoformat(r["end"]).astimezone(UTC), "type": r["type"], "reason": r["reason"]} for r in data["availability_rules"]])
    org.fixture_hash = fingerprint
    audit(session, org.id, None, "demo.seed", "organizations", org.id, details={"employees": 350, "fixture_hash": fingerprint})
    from app.services.automation_events import ensure_definitions
    ensure_definitions(session, org.id)
    return org, True


def create_user(session, org, username, password, role_name="admin", unit_id=None):
    from app.services.organization_lock import lock_organization
    lock_organization(session, org.id)
    username = username.lower().strip()
    if not re.fullmatch(r"[a-z0-9][a-z0-9._@+-]{2,79}", username):
        raise ValueError("Nome de usuário inválido")
    if len(password) < 12 or len(password) > 128:
        raise ValueError("Senha deve ter entre 12 e 128 caracteres")
    if session.scalar(select(User.id).where(User.organization_id == org.id, User.username == username)):
        raise ValueError("Usuário já existe; senha não foi alterada")
    if unit_id and not session.scalar(select(Unit.id).where(Unit.id == unit_id, Unit.organization_id == org.id)):
        raise ValueError("Unidade fora da organização")
    role = session.scalar(select(Role).where(Role.name == role_name))
    if role is None:
        raise ValueError("Perfil inválido")
    user = User(organization_id=org.id, username=username, password_hash=hash_password(password))
    session.add(user)
    session.flush()
    session.add(UserRole(organization_id=org.id, user_id=user.id, role_id=role.id, unit_id=unit_id))
    session.flush()
    return user


def restore_demo(session, org, confirmation, environment):
    if environment not in {"development", "test"} or not org.is_demo or org.id != demo_id("organization") or org.slug != "horizonte" or confirmation != org.name:
        raise ValueError("Restauração permitida somente no Hospital Horizonte marcado como demonstração e com confirmação exata")
    # Preservar usuários, permissões, sessões e auditoria. Recriar somente dados de negócio demo.
    from app.services.organization_lock import lock_organization
    lock_organization(session, org.id)
    from app.models.entities import (AutomationArtifact, AutomationDefinition, AutomationExecution, AutomationNotice, AutomationSuggestion,
        IntegrationCredential, IntegrationReceipt, OutboxEvent, WebhookDelivery, CalendarShift, EntityReview, FinancialRun, LaborRule, OptimizationRun, ScenarioVersion, ScheduleDecision, ScheduleEvaluation, ScheduleVersion)
    for model in [IntegrationReceipt, WebhookDelivery, IntegrationCredential, AutomationSuggestion, AutomationArtifact, AutomationNotice, AutomationExecution, OutboxEvent, AutomationDefinition,
        ScheduleDecision, ScheduleVersion, OptimizationRun, EntityReview, FinancialRun, ScenarioVersion, ScheduleEvaluation, CalendarShift, LaborRule, AvailabilityRule, Contract, EmployeeQualification, EmployeeSkill, Employee, RoleQualification, RoleSkill, Department, WorkPattern, Qualification, Skill, JobRole]:
        session.execute(delete(model).where(model.organization_id == org.id))
    # Preservar unidades e escopos de acesso. A unidade principal recebe os dados da fixture.
    org.fixture_hash = None
    audit(session, org.id, None, "demo.restore", "organizations", org.id)
