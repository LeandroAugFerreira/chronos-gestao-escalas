from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Header, Query, Request
from sqlalchemy import func, inspect, select, update

from app.api.dependencies import fail, get_db, require
from app.core.security import ROLE_PERMISSIONS
from app.models.entities import (AuditLog, AvailabilityRule, Contract, Department, Employee,
    EmployeeQualification, EmployeeSkill, JobRole, Organization, Qualification, Role,
    Skill, Unit, User, WorkPattern)
from app.repositories.scoped import get_scoped, page, scoped
from app.repositories.people import employee_query
from app.schemas.people_export import PeopleExportInput
from app.services.people_exports import export_people
from app.schemas.phase2 import (AvailabilityInput, CatalogInput, ContractInput, DepartmentInput,
    EmployeeInput, EmployeeOutput, EmployeePage, EmployeePatch, QualificationInput, SkillInput, UnitInput, UserInput,
    UnitPatch, DepartmentPatch, CatalogPatch)
from app.services.audit import audit
from app.services.seed import create_user
from app.services import idempotency

def idempotency_header(idempotency_key: str | None = Header(None, max_length=128)):
    return idempotency_key


router = APIRouter(prefix="/api/v1", tags=["Cadastros protegidos"], dependencies=[Depends(idempotency_header)])
Page = Query(1, ge=1)
Size = Query(25, ge=1, le=100)


def as_dict(entity, fields):
    from app.api.dependencies import aware
    return {field: aware(value) if isinstance(value := getattr(entity, field), datetime) else value for field in fields}


def employee_view(employee):
    return as_dict(employee, ["id", "organization_id", "unit_id", "department_id", "job_role_id", "name", "registration", "status", "synthetic", "revision"])


def related(session, model, id, principal):
    row = session.scalar(select(model).where(model.organization_id == principal.user.organization_id, model.id == id))
    if row is None:
        fail(422, "INVALID_REFERENCE", "Referência inválida para esta organização.")
    return row


def commit_created(session, row, principal, request, action="create"):
    payload = {column.key: getattr(row, column.key) for column in inspect(type(row)).column_attrs if column.key not in {"id", "created_at"}}
    existing, pending = idempotency.prepare(session, request, principal, type(row), payload)
    if existing is not None:
        return existing
    session.add(row)
    session.flush()
    idempotency.record(session, pending, row.id)
    audit(session, principal.user.organization_id, principal.user.id, action, row.__tablename__, row.id, request.state.correlation_id)
    session.commit()
    return row


def require_global(principal, permission):
    if principal.scopes[permission] is not None:
        fail(403, "GLOBAL_SCOPE_REQUIRED", "Esta ação exige permissão em toda a organização.")


def update_revision(session, row, payload, principal, request):
    changes = payload.model_dump(exclude={"revision"}, exclude_none=True)
    model = type(row)
    changed = session.execute(update(model).where(model.id == row.id, model.organization_id == principal.user.organization_id,
        model.revision == payload.revision).values(**changes, revision=model.revision + 1).execution_options(synchronize_session=False))
    if changed.rowcount != 1:
        fail(409, "STALE_VERSION", "Registro alterado por outra operação. Recarregue antes de salvar.")
    audit(session, principal.user.organization_id, principal.user.id, "update", row.__tablename__, row.id, request.state.correlation_id, {"fields": sorted(changes)})
    session.commit()
    session.refresh(row)
    return row


@router.get("/organizations")
def organizations(principal=Depends(require("org:read")), session=Depends(get_db)):
    org = session.get(Organization, principal.user.organization_id)
    return {"items": [as_dict(org, ["id", "slug", "name", "segment", "timezone", "operation", "is_demo"])], "total": 1}


@router.get("/organizations/{id}")
def organization(id: str, principal=Depends(require("org:read")), session=Depends(get_db)):
    if id != principal.user.organization_id:
        fail(404, "NOT_FOUND", "Registro não encontrado.")
    return organizations(principal, session)["items"][0]


@router.get("/units")
def units(page_number: int = Page, page_size: int = Size, search: str = Query("", max_length=120),
          principal=Depends(require("org:read")), session=Depends(get_db)):
    query = scoped(Unit, principal, "org:read", Unit.id).where(Unit.name.ilike(f"%{search}%"))
    return page(session, query.order_by(Unit.name, Unit.id), page_number, page_size,
                lambda r: as_dict(r, ["id", "name", "operation", "timezone", "revision"]))


@router.post("/units", status_code=201)
def create_unit(payload: UnitInput, request: Request, principal=Depends(require("org:write")), session=Depends(get_db)):
    require_global(principal, "org:write")
    row = commit_created(session, Unit(organization_id=principal.user.organization_id, **payload.model_dump()), principal, request)
    return as_dict(row, ["id", "name", "operation", "timezone", "revision"])


@router.patch("/units/{id}")
def patch_unit(id: str, payload: UnitPatch, request: Request, principal=Depends(require("org:write")), session=Depends(get_db)):
    row = get_scoped(session, Unit, id, principal, "org:write", Unit.id)
    row = update_revision(session, row, payload, principal, request)
    return as_dict(row, ["id", "name", "operation", "timezone", "revision"])


@router.get("/departments")
def departments(page_number: int = Page, page_size: int = Size, unit_id: str | None = None,
                search: str = Query("", max_length=120), principal=Depends(require("org:read")), session=Depends(get_db)):
    query = scoped(Department, principal, "org:read", Department.unit_id).where(Department.name.ilike(f"%{search}%"))
    if unit_id:
        query = query.where(Department.unit_id == unit_id)
    return page(session, query.order_by(Department.name, Department.id), page_number, page_size,
                lambda r: as_dict(r, ["id", "unit_id", "name", "group", "operation", "cost_center", "revision"]))


@router.post("/departments", status_code=201)
def create_department(payload: DepartmentInput, request: Request, principal=Depends(require("org:write")), session=Depends(get_db)):
    related(session, Unit, payload.unit_id, principal)
    if not principal.permits("org:write", payload.unit_id):
        fail(403, "FORBIDDEN", "Unidade fora do escopo permitido.")
    row = commit_created(session, Department(organization_id=principal.user.organization_id, **payload.model_dump()), principal, request)
    return as_dict(row, ["id", "unit_id", "name", "group", "operation", "cost_center", "revision"])


@router.patch("/departments/{id}")
def patch_department(id: str, payload: DepartmentPatch, request: Request, principal=Depends(require("org:write")), session=Depends(get_db)):
    row = get_scoped(session, Department, id, principal, "org:write", Department.unit_id)
    related(session, Unit, payload.unit_id, principal)
    if not principal.permits("org:write", payload.unit_id):
        fail(403, "FORBIDDEN", "Unidade fora do escopo permitido.")
    if row.unit_id != payload.unit_id and session.scalar(select(Employee.id).where(Employee.organization_id == principal.user.organization_id, Employee.department_id == id).limit(1)):
        fail(409, "DEPARTMENT_IN_USE", "Transfira os colaboradores antes de alterar a unidade do setor.")
    row = update_revision(session, row, payload, principal, request)
    return as_dict(row, ["id", "unit_id", "name", "group", "operation", "cost_center", "revision"])


CATALOGS = {"job-roles": JobRole, "skills": Skill, "qualifications": Qualification, "work-patterns": WorkPattern}


@router.get("/catalogs/{kind}")
def catalogs(kind: str, page_number: int = Page, page_size: int = Size,
             principal=Depends(require("catalog:read")), session=Depends(get_db)):
    model = CATALOGS.get(kind)
    if model is None:
        fail(404, "NOT_FOUND", "Catálogo não encontrado.")
    query = scoped(model, principal, "catalog:read").order_by(model.name, model.id)
    return page(session, query, page_number, page_size, lambda r: as_dict(r, ["id", "name", "description", "legal_status", "configuration"] if model is WorkPattern else ["id", "name", "revision"]))


@router.post("/catalogs/{kind}", status_code=201)
def create_catalog(kind: str, payload: CatalogInput, request: Request, principal=Depends(require("catalog:write")), session=Depends(get_db)):
    model = CATALOGS.get(kind)
    if model not in {JobRole, Skill, Qualification}:
        fail(422, "INVALID_CATALOG", "Cadastre jornadas em /work-patterns e critérios em /labor-rules.")
    require_global(principal, "catalog:write")
    row = commit_created(session, model(organization_id=principal.user.organization_id, name=payload.name), principal, request)
    return as_dict(row, ["id", "name", "revision"])


@router.patch("/catalogs/{kind}/{id}")
def patch_catalog(kind: str, id: str, payload: CatalogPatch, request: Request, principal=Depends(require("catalog:write")), session=Depends(get_db)):
    model = CATALOGS.get(kind)
    if model not in {JobRole, Skill, Qualification}:
        fail(422, "INVALID_CATALOG", "Catálogo não permite esta alteração.")
    require_global(principal, "catalog:write")
    row = get_scoped(session, model, id, principal, "catalog:write")
    row = update_revision(session, row, payload, principal, request)
    return as_dict(row, ["id", "name", "revision"])


@router.get("/employees", response_model=EmployeePage)
def employees(page_number: int = Page, page_size: int = Size, unit_id: str | None = None,
              department_id: str | None = None, status: str | None = Query(None, pattern="^(active|inactive)$"),
              search: str = Query("", max_length=120), sort: str = Query("name", pattern="^(name|registration|status)$"),
              descending: bool = False, principal=Depends(require("people:read")), session=Depends(get_db)):
    query = employee_query(principal, unit_id=unit_id, department_id=department_id, status=status,
                           search=search, sort=sort, descending=descending)
    return page(session, query, page_number, page_size, employee_view)


@router.post("/employees/export")
def export_employees(payload: PeopleExportInput, request: Request,
                     principal=Depends(require("people:read")), session=Depends(get_db)):
    return export_people(session, principal, payload, request.state.correlation_id)


@router.get("/employees/{id}", response_model=EmployeeOutput)
def employee(id: str, principal=Depends(require("people:read")), session=Depends(get_db)):
    return employee_view(get_scoped(session, Employee, id, principal, "people:read", Employee.unit_id))


@router.post("/employees", status_code=201, response_model=EmployeeOutput)
def create_employee(payload: EmployeeInput, request: Request, principal=Depends(require("people:write")), session=Depends(get_db)):
    department = related(session, Department, payload.department_id, principal)
    related(session, JobRole, payload.job_role_id, principal)
    if department.unit_id != payload.unit_id:
        fail(422, "INVALID_REFERENCE", "Setor e unidade incompatíveis.")
    if not principal.permits("people:write", payload.unit_id):
        fail(403, "FORBIDDEN", "Unidade fora do escopo permitido.")
    row = commit_created(session, Employee(organization_id=principal.user.organization_id, **payload.model_dump()), principal, request)
    return employee_view(row)


@router.patch("/employees/{id}", response_model=EmployeeOutput)
def patch_employee(id: str, payload: EmployeePatch, request: Request, principal=Depends(require("people:write")), session=Depends(get_db)):
    row = get_scoped(session, Employee, id, principal, "people:write", Employee.unit_id)
    if payload.unit_id:
        department = related(session, Department, payload.department_id, principal)
        if department.unit_id != payload.unit_id:
            fail(422, "INVALID_REFERENCE", "Setor e unidade incompatíveis.")
        if not principal.permits("people:write", payload.unit_id):
            fail(403, "FORBIDDEN", "Unidade de destino fora do escopo permitido.")
    if payload.job_role_id:
        related(session, JobRole, payload.job_role_id, principal)
    changes = payload.model_dump(exclude={"revision"}, exclude_none=True)
    changed = session.execute(update(Employee).where(Employee.id == row.id, Employee.organization_id == principal.user.organization_id,
        Employee.revision == payload.revision).values(**changes, revision=Employee.revision + 1).execution_options(synchronize_session=False))
    if changed.rowcount != 1:
        fail(409, "STALE_VERSION", "Registro alterado por outra operação. Recarregue antes de salvar.")
    audit(session, principal.user.organization_id, principal.user.id, "update", "employees", row.id, request.state.correlation_id, {"fields": sorted(changes)})
    session.commit()
    session.refresh(row)
    return employee_view(row)


@router.get("/employees/{id}/contracts")
def contracts(id: str, principal=Depends(require("finance:read")), session=Depends(get_db)):
    get_scoped(session, Employee, id, principal, "finance:read", Employee.unit_id)
    rows = session.scalars(select(Contract).where(Contract.organization_id == principal.user.organization_id, Contract.employee_id == id).order_by(Contract.valid_from))
    return {"items": [as_dict(r, ["id", "weekly_minutes", "base_salary_cents", "currency", "work_pattern_id", "employment_type", "valid_from", "valid_until", "validation_status", "assumption_source"]) for r in rows]}


@router.post("/employees/{id}/contracts", status_code=201)
def create_contract(id: str, payload: ContractInput, request: Request, principal=Depends(require("people:write")), session=Depends(get_db)):
    person = get_scoped(session, Employee, id, principal, "people:write", Employee.unit_id)
    if not principal.permits("finance:read", person.unit_id):
        fail(403, "FORBIDDEN", "Permissão financeira necessária para registrar salário.")
    related(session, WorkPattern, payload.work_pattern_id, principal)
    row = Contract(organization_id=principal.user.organization_id, employee_id=id, **payload.model_dump())
    content = {column.key: getattr(row, column.key) for column in inspect(Contract).column_attrs if column.key not in {"id", "created_at"}}
    existing, _ = idempotency.prepare(session, request, principal, Contract, content)
    if existing:
        return {"id": existing.id, "validation_status": existing.validation_status}
    # Bloqueio por pessoa serializa contratos concorrentes em PostgreSQL.
    session.execute(select(Employee.id).where(Employee.id == id, Employee.organization_id == principal.user.organization_id).with_for_update())
    query = select(Contract.id).where(Contract.organization_id == principal.user.organization_id, Contract.employee_id == id,
        (Contract.valid_until.is_(None) | (Contract.valid_until > payload.valid_from)))
    if payload.valid_until:
        query = query.where(Contract.valid_from < payload.valid_until)
    if session.scalar(query):
        fail(409, "OVERLAPPING_CONTRACT", "Existe contrato sobreposto no período informado.")
    row = commit_created(session, row, principal, request)
    return {"id": row.id, "validation_status": row.validation_status}


@router.get("/employees/{id}/qualifications")
def employee_qualifications(id: str, principal=Depends(require("people:read")), session=Depends(get_db)):
    get_scoped(session, Employee, id, principal, "people:read", Employee.unit_id)
    rows = session.scalars(select(EmployeeQualification).where(EmployeeQualification.organization_id == principal.user.organization_id, EmployeeQualification.employee_id == id))
    return {"items": [as_dict(r, ["id", "qualification_id", "valid_from", "valid_until", "verification_status", "evidence"]) for r in rows]}


@router.post("/employees/{id}/qualifications", status_code=201)
def add_qualification(id: str, payload: QualificationInput, request: Request, principal=Depends(require("people:write")), session=Depends(get_db)):
    get_scoped(session, Employee, id, principal, "people:write", Employee.unit_id)
    related(session, Qualification, payload.qualification_id, principal)
    row = commit_created(session, EmployeeQualification(organization_id=principal.user.organization_id, employee_id=id, **payload.model_dump()), principal, request)
    return {"id": row.id, "verification_status": row.verification_status}


@router.get("/employees/{id}/skills")
def employee_skills(id: str, principal=Depends(require("people:read")), session=Depends(get_db)):
    get_scoped(session, Employee, id, principal, "people:read", Employee.unit_id)
    rows = session.scalars(select(EmployeeSkill).where(EmployeeSkill.organization_id == principal.user.organization_id, EmployeeSkill.employee_id == id))
    return {"items": [as_dict(r, ["id", "skill_id"]) for r in rows]}


@router.post("/employees/{id}/skills", status_code=201)
def add_skill(id: str, payload: SkillInput, request: Request, principal=Depends(require("people:write")), session=Depends(get_db)):
    get_scoped(session, Employee, id, principal, "people:write", Employee.unit_id)
    related(session, Skill, payload.skill_id, principal)
    row = commit_created(session, EmployeeSkill(organization_id=principal.user.organization_id, employee_id=id, skill_id=payload.skill_id), principal, request)
    return {"id": row.id, "skill_id": row.skill_id}


@router.get("/employees/{id}/availability")
def availability(id: str, principal=Depends(require("people:read")), session=Depends(get_db)):
    get_scoped(session, Employee, id, principal, "people:read", Employee.unit_id)
    rows = session.scalars(select(AvailabilityRule).where(AvailabilityRule.organization_id == principal.user.organization_id, AvailabilityRule.employee_id == id))
    from app.api.dependencies import aware
    return {"items": [{"id": r.id, "start_at": aware(r.start_at), "end_at": aware(r.end_at), "type": r.type, "reason": r.reason} for r in rows]}


@router.post("/employees/{id}/availability", status_code=201)
def add_availability(id: str, payload: AvailabilityInput, request: Request, principal=Depends(require("people:write")), session=Depends(get_db)):
    get_scoped(session, Employee, id, principal, "people:write", Employee.unit_id)
    row = commit_created(session, AvailabilityRule(organization_id=principal.user.organization_id, employee_id=id, **payload.model_dump()), principal, request)
    return {"id": row.id, "type": row.type}


@router.get("/users")
def users(page_number: int = Page, page_size: int = Size, principal=Depends(require("users:write")), session=Depends(get_db)):
    require_global(principal, "users:write")
    return page(session, scoped(User, principal, "users:write").order_by(User.username), page_number, page_size,
                lambda r: as_dict(r, ["id", "username", "active"]))


@router.post("/users", status_code=201)
def add_user(payload: UserInput, request: Request, principal=Depends(require("users:write")), session=Depends(get_db)):
    require_global(principal, "users:write")
    if payload.unit_id:
        related(session, Unit, payload.unit_id, principal)
    org = session.get(Organization, principal.user.organization_id)
    content = {**payload.model_dump(exclude={"password"}), "password": payload.password.get_secret_value()}
    existing, pending = idempotency.prepare(session, request, principal, User, content)
    if existing:
        return {"id": existing.id, "username": existing.username, "role": payload.role, "unit_id": payload.unit_id}
    try:
        user = create_user(session, org, payload.username, payload.password.get_secret_value(), payload.role, payload.unit_id)
    except ValueError:
        fail(409, "USER_CONFLICT", "Usuário existente ou configuração inválida.")
    audit(session, org.id, principal.user.id, "create", "users", user.id, request.state.correlation_id)
    idempotency.record(session, pending, user.id)
    session.commit()
    return {"id": user.id, "username": user.username, "role": payload.role, "unit_id": payload.unit_id}


@router.get("/roles")
def roles(principal=Depends(require("users:write"))):
    require_global(principal, "users:write")
    return {"items": [{"name": name, "permissions": sorted(codes)} for name, codes in ROLE_PERMISSIONS.items()]}


@router.get("/audit")
def audit_records(page_number: int = Page, page_size: int = Size, principal=Depends(require("audit:read")), session=Depends(get_db)):
    require_global(principal, "audit:read")
    return page(session, scoped(AuditLog, principal, "audit:read").order_by(AuditLog.created_at.desc(), AuditLog.id), page_number, page_size,
                lambda r: as_dict(r, ["id", "actor_id", "action", "entity_type", "entity_id", "correlation_id", "created_at", "details"]))


@router.get("/analytics/workforce")
def workforce(principal=Depends(require("org:read")), session=Depends(get_db)):
    query = scoped(Employee, principal, "org:read", Employee.unit_id)
    return {"employee_count": session.scalar(select(func.count()).select_from(query.subquery())),
            "source": "database", "synthetic": True}


@router.get("/analytics/overview")
def overview(unit_id: str | None = None, principal=Depends(require("org:read")), session=Depends(get_db)):
    from app.models.entities import now
    org = session.get(Organization, principal.user.organization_id)
    units_query = scoped(Unit, principal, "org:read", Unit.id)
    departments_query = scoped(Department, principal, "org:read", Department.unit_id)
    employees_query = scoped(Employee, principal, "org:read", Employee.unit_id)
    if unit_id:
        get_scoped(session, Unit, unit_id, principal, "org:read", Unit.id)
        units_query = units_query.where(Unit.id == unit_id)
        departments_query = departments_query.where(Department.unit_id == unit_id)
        employees_query = employees_query.where(Employee.unit_id == unit_id)
    units = session.scalars(units_query.order_by(Unit.name, Unit.id)).all()
    departments = session.scalars(departments_query.order_by(Department.name, Department.id)).all()
    people = employees_query.subquery()
    counts = dict(session.execute(select(people.c.status, func.count()).group_by(people.c.status)).all())
    per_department = dict(session.execute(select(people.c.department_id, func.count()).group_by(people.c.department_id)).all())
    instant = now()
    local_date = instant.astimezone(ZoneInfo(org.timezone)).date()
    current = select(Contract).join(people, people.c.id == Contract.employee_id).where(Contract.organization_id == org.id,
        Contract.valid_from <= local_date, (Contract.valid_until.is_(None) | (Contract.valid_until > local_date)), people.c.status == "active").subquery()
    average = session.scalar(select(func.avg(current.c.weekly_minutes)))
    regimes = session.execute(select(WorkPattern.name, func.count()).join(current, current.c.work_pattern_id == WorkPattern.id)
        .where(WorkPattern.organization_id == org.id).group_by(WorkPattern.name).order_by(WorkPattern.name)).all()
    return {"organization": as_dict(org, ["id", "name", "segment", "operation", "timezone", "is_demo"]),
        "source": "database", "as_of": instant, "unit_id": unit_id,
        "employee_count": sum(counts.values()), "active_count": counts.get("active", 0), "inactive_count": counts.get("inactive", 0),
        "unit_count": len(units), "department_count": len(departments),
        "weekly_average_hours": round(float(average) / 60, 2) if average is not None else None,
        "departments": [{"id": row.id, "name": row.name, "group": row.group, "unit_id": row.unit_id,
                         "employee_count": per_department.get(row.id, 0)} for row in departments],
        "regimes": [{"name": name, "employee_count": count} for name, count in regimes],
        "notices": ["Quantitativos sintéticos, sem comprovação de dimensionamento ou cobertura.",
                    "Jornadas contratuais pendentes de revisão; consulte as avaliações e as versões calculadas nos módulos específicos."]}
