"""Entidades da Fase 2. FKs compostas bloqueiam relações entre organizações."""

from datetime import UTC, date, datetime
from uuid import uuid4

from sqlalchemy import (Boolean, CheckConstraint, Date, DateTime, ForeignKey, ForeignKeyConstraint,
                        Index, Integer, JSON, MetaData, String, Text, UniqueConstraint)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def now():
    return datetime.now(UTC)


def uid():
    return str(uuid4())


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention={"ix": "ix_%(table_name)s_%(column_0_name)s", "uq": "uq_%(table_name)s_%(column_0_N_name)s", "ck": "ck_%(table_name)s_%(constraint_name)s", "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s", "pk": "pk_%(table_name)s"})


class Identified:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Tenant(Identified):
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)


def tenant_args(*constraints):
    return (UniqueConstraint("organization_id", "id"), *constraints)


def tenant_fk(column, table):
    return ForeignKeyConstraint(["organization_id", column], [f"{table}.organization_id", f"{table}.id"])


class Organization(Identified, Base):
    __tablename__ = "organizations"
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(160))
    segment: Mapped[str] = mapped_column(String(80))
    timezone: Mapped[str] = mapped_column(String(80), default="America/Sao_Paulo")
    operation: Mapped[str] = mapped_column(String(32), default="business")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    fixture_hash: Mapped[str | None] = mapped_column(String(64))


class Role(Identified, Base):
    __tablename__ = "roles"
    name: Mapped[str] = mapped_column(String(32), unique=True)


class Permission(Identified, Base):
    __tablename__ = "permissions"
    code: Mapped[str] = mapped_column(String(64), unique=True)


class RolePermission(Base):
    __tablename__ = "role_permissions"
    role_id: Mapped[str] = mapped_column(ForeignKey("roles.id"), primary_key=True)
    permission_id: Mapped[str] = mapped_column(ForeignKey("permissions.id"), primary_key=True)


class Unit(Tenant, Base):
    __tablename__ = "units"
    name: Mapped[str] = mapped_column(String(160))
    operation: Mapped[str] = mapped_column(String(32), default="business")
    timezone: Mapped[str] = mapped_column(String(80), default="America/Sao_Paulo")
    revision: Mapped[int] = mapped_column(Integer, default=1)
    __table_args__ = tenant_args()


class Department(Tenant, Base):
    __tablename__ = "departments"
    unit_id: Mapped[str] = mapped_column(String(36))
    name: Mapped[str] = mapped_column(String(160))
    group: Mapped[str] = mapped_column(String(80))
    operation: Mapped[str] = mapped_column(String(32), default="business")
    cost_center: Mapped[str] = mapped_column(String(80), default="")
    revision: Mapped[int] = mapped_column(Integer, default=1)
    __table_args__ = tenant_args(tenant_fk("unit_id", "units"), UniqueConstraint("organization_id", "unit_id", "id"))


class JobRole(Tenant, Base):
    __tablename__ = "job_roles"
    name: Mapped[str] = mapped_column(String(160))
    revision: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    __table_args__ = tenant_args()


class Skill(Tenant, Base):
    __tablename__ = "skills"
    name: Mapped[str] = mapped_column(String(160))
    revision: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    __table_args__ = tenant_args()


class Qualification(Tenant, Base):
    __tablename__ = "qualifications"
    name: Mapped[str] = mapped_column(String(200))
    revision: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    synthetic: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = tenant_args()


class RoleSkill(Tenant, Base):
    __tablename__ = "role_skills"
    job_role_id: Mapped[str] = mapped_column(String(36))
    skill_id: Mapped[str] = mapped_column(String(36))
    __table_args__ = tenant_args(tenant_fk("job_role_id", "job_roles"), tenant_fk("skill_id", "skills"), UniqueConstraint("organization_id", "job_role_id", "skill_id"))


class RoleQualification(Tenant, Base):
    __tablename__ = "role_qualifications"
    job_role_id: Mapped[str] = mapped_column(String(36))
    qualification_id: Mapped[str] = mapped_column(String(36))
    __table_args__ = tenant_args(tenant_fk("job_role_id", "job_roles"), tenant_fk("qualification_id", "qualifications"), UniqueConstraint("organization_id", "job_role_id", "qualification_id"))


class Employee(Tenant, Base):
    __tablename__ = "employees"
    unit_id: Mapped[str] = mapped_column(String(36))
    department_id: Mapped[str] = mapped_column(String(36))
    job_role_id: Mapped[str] = mapped_column(String(36))
    name: Mapped[str] = mapped_column(String(160))
    registration: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(16), default="active")
    synthetic: Mapped[bool] = mapped_column(Boolean, default=True)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    preferences: Mapped[dict] = mapped_column(JSON, default=dict)
    __table_args__ = tenant_args(tenant_fk("unit_id", "units"), tenant_fk("job_role_id", "job_roles"),
        ForeignKeyConstraint(["organization_id", "unit_id", "department_id"], ["departments.organization_id", "departments.unit_id", "departments.id"]),
        UniqueConstraint("organization_id", "registration"), CheckConstraint("status IN ('active','inactive')", name="valid_status"),
        Index("ix_employees_scope", "organization_id", "unit_id", "department_id", "status"))


class EmployeeSkill(Tenant, Base):
    __tablename__ = "employee_skills"
    employee_id: Mapped[str] = mapped_column(String(36))
    skill_id: Mapped[str] = mapped_column(String(36))
    __table_args__ = tenant_args(tenant_fk("employee_id", "employees"), tenant_fk("skill_id", "skills"), UniqueConstraint("organization_id", "employee_id", "skill_id"))


class EmployeeQualification(Tenant, Base):
    __tablename__ = "employee_qualifications"
    employee_id: Mapped[str] = mapped_column(String(36))
    qualification_id: Mapped[str] = mapped_column(String(36))
    valid_from: Mapped[date] = mapped_column(Date)
    valid_until: Mapped[date] = mapped_column(Date)
    verification_status: Mapped[str] = mapped_column(String(32), default="pending_review")
    evidence: Mapped[str] = mapped_column(Text, default="")
    __table_args__ = tenant_args(tenant_fk("employee_id", "employees"), tenant_fk("qualification_id", "qualifications"), CheckConstraint("valid_until > valid_from", name="valid_dates"))


class WorkPattern(Tenant, Base):
    __tablename__ = "work_patterns"
    revision: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    name: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text, default="")
    legal_status: Mapped[str] = mapped_column(String(32), default="pending_review")
    configuration: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}")
    __table_args__ = tenant_args()


class Contract(Tenant, Base):
    __tablename__ = "contracts"
    employee_id: Mapped[str] = mapped_column(String(36))
    work_pattern_id: Mapped[str] = mapped_column(String(36))
    weekly_minutes: Mapped[int] = mapped_column(Integer)
    base_salary_cents: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="BRL")
    employment_type: Mapped[str] = mapped_column(String(40))
    valid_from: Mapped[date] = mapped_column(Date)
    valid_until: Mapped[date | None] = mapped_column(Date)
    validation_status: Mapped[str] = mapped_column(String(32), default="pending_review")
    assumption_source: Mapped[str] = mapped_column(Text, default="")
    __table_args__ = tenant_args(tenant_fk("employee_id", "employees"), tenant_fk("work_pattern_id", "work_patterns"),
        CheckConstraint("weekly_minutes > 0 AND base_salary_cents >= 0", name="positive_amounts"),
        CheckConstraint("valid_until IS NULL OR valid_until > valid_from", name="valid_dates"))


class AvailabilityRule(Tenant, Base):
    __tablename__ = "availability_rules"
    employee_id: Mapped[str] = mapped_column(String(36))
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    type: Mapped[str] = mapped_column(String(24), default="unavailable")
    reason: Mapped[str] = mapped_column(String(200), default="")
    __table_args__ = tenant_args(tenant_fk("employee_id", "employees"), CheckConstraint("end_at > start_at", name="positive_interval"), CheckConstraint("type IN ('available','unavailable')", name="valid_type"))


class User(Tenant, Base):
    __tablename__ = "users"
    username: Mapped[str] = mapped_column(String(80))
    password_hash: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = tenant_args(UniqueConstraint("organization_id", "username"))


class UserRole(Tenant, Base):
    __tablename__ = "user_roles"
    user_id: Mapped[str] = mapped_column(String(36))
    role_id: Mapped[str] = mapped_column(String(36), ForeignKey("roles.id"))
    unit_id: Mapped[str | None] = mapped_column(String(36))
    __table_args__ = tenant_args(tenant_fk("user_id", "users"), tenant_fk("unit_id", "units"))


class RefreshSession(Tenant, Base):
    __tablename__ = "refresh_sessions"
    user_id: Mapped[str] = mapped_column(String(36))
    family_id: Mapped[str] = mapped_column(String(36), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = tenant_args(tenant_fk("user_id", "users"))


class AuditLog(Tenant, Base):
    __tablename__ = "audit_logs"
    actor_id: Mapped[str | None] = mapped_column(String(36))
    action: Mapped[str] = mapped_column(String(80))
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[str] = mapped_column(String(36))
    correlation_id: Mapped[str] = mapped_column(String(36))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    __table_args__ = tenant_args(tenant_fk("actor_id", "users"))


class LoginThrottle(Identified, Base):
    __tablename__ = "login_throttles"
    bucket_hash: Mapped[str] = mapped_column(String(64), unique=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class IdempotencyRecord(Tenant, Base):
    __tablename__ = "idempotency_records"
    actor_id: Mapped[str] = mapped_column(String(36))
    route: Mapped[str] = mapped_column(String(200))
    key_hash: Mapped[str] = mapped_column(String(64))
    payload_hash: Mapped[str] = mapped_column(String(64))
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[str] = mapped_column(String(36))
    __table_args__ = tenant_args(tenant_fk("actor_id", "users"), UniqueConstraint("organization_id", "actor_id", "route", "key_hash"))


class LaborRule(Tenant, Base):
    """Versão imutável; substituições são novos registros com outra vigência."""
    __tablename__ = "labor_rules"
    key: Mapped[str] = mapped_column(String(80))
    version: Mapped[int] = mapped_column(Integer)
    supersedes_id: Mapped[str | None] = mapped_column(String(36))
    kind: Mapped[str] = mapped_column(String(40))
    minutes: Mapped[int] = mapped_column(Integer)
    threshold_minutes: Mapped[int] = mapped_column(Integer, default=0)
    unit_id: Mapped[str | None] = mapped_column(String(36))
    job_role_id: Mapped[str | None] = mapped_column(String(36))
    contract_id: Mapped[str | None] = mapped_column(String(36))
    agreement: Mapped[str] = mapped_column(String(200), default="")
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="pending_review")
    review_evidence: Mapped[str] = mapped_column(Text, default="")
    reviewer_id: Mapped[str | None] = mapped_column(String(36))
    __table_args__ = tenant_args(tenant_fk("supersedes_id", "labor_rules"), tenant_fk("unit_id", "units"), tenant_fk("job_role_id", "job_roles"), tenant_fk("contract_id", "contracts"), tenant_fk("reviewer_id", "users"), UniqueConstraint("organization_id", "supersedes_id"),
        UniqueConstraint("organization_id", "key", "version"), CheckConstraint("version > 0 AND minutes >= 0 AND threshold_minutes >= 0", name="positive_parameters"),
        CheckConstraint("valid_until > valid_from", name="valid_interval"), CheckConstraint("status IN ('pending_review','validated')", name="valid_status"))


class CalendarShift(Tenant, Base):
    __tablename__ = "calendar_shifts"
    employee_id: Mapped[str] = mapped_column(String(36))
    unit_id: Mapped[str] = mapped_column(String(36))
    department_id: Mapped[str] = mapped_column(String(36))
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    breaks: Mapped[list] = mapped_column(JSON, default=list)
    label: Mapped[str] = mapped_column(String(80), default="Plantão")
    state: Mapped[str] = mapped_column(String(16), default="draft")
    revision: Mapped[int] = mapped_column(Integer, default=1)
    evaluation: Mapped[dict] = mapped_column(JSON, default=dict)
    __table_args__ = tenant_args(tenant_fk("employee_id", "employees"), tenant_fk("unit_id", "units"),
        ForeignKeyConstraint(["organization_id", "unit_id", "department_id"], ["departments.organization_id", "departments.unit_id", "departments.id"]),
        CheckConstraint("end_at > start_at", name="positive_interval"), CheckConstraint("state IN ('draft','cancelled')", name="valid_state"),
        Index("ix_calendar_shifts_scope", "organization_id", "unit_id", "start_at"))


class ScheduleEvaluation(Tenant, Base):
    __tablename__ = "schedule_evaluations"
    shift_id: Mapped[str] = mapped_column(String(36))
    actor_id: Mapped[str] = mapped_column(String(36))
    shift_revision: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[dict] = mapped_column(JSON)
    __table_args__ = tenant_args(tenant_fk("shift_id", "calendar_shifts"), tenant_fk("actor_id", "users"))


class ScenarioVersion(Tenant, Base):
    __tablename__ = "scenario_versions"
    unit_id: Mapped[str] = mapped_column(String(36))
    department_id: Mapped[str | None] = mapped_column(String(36))
    actor_id: Mapped[str] = mapped_column(String(36))
    key: Mapped[str] = mapped_column(String(80))
    version: Mapped[int] = mapped_column(Integer)
    parent_id: Mapped[str | None] = mapped_column(String(36))
    name: Mapped[str] = mapped_column(String(160))
    reference_month: Mapped[date] = mapped_column(Date)
    inputs: Mapped[dict] = mapped_column(JSON)
    capacity: Mapped[dict] = mapped_column(JSON)
    evidence: Mapped[dict] = mapped_column(JSON)
    payroll_snapshot: Mapped[dict] = mapped_column(JSON)
    digest: Mapped[str] = mapped_column(String(64))
    __table_args__ = tenant_args(tenant_fk("unit_id", "units"), tenant_fk("actor_id", "users"), tenant_fk("parent_id", "scenario_versions"),
        ForeignKeyConstraint(["organization_id", "unit_id", "department_id"], ["departments.organization_id", "departments.unit_id", "departments.id"]),
        UniqueConstraint("organization_id", "key", "version"), UniqueConstraint("organization_id", "unit_id", "id"),
        CheckConstraint("version > 0", name="positive_version"))


class FinancialRun(Tenant, Base):
    __tablename__ = "financial_runs"
    unit_id: Mapped[str] = mapped_column(String(36))
    scenario_id: Mapped[str] = mapped_column(String(36))
    actor_id: Mapped[str] = mapped_column(String(36))
    name: Mapped[str] = mapped_column(String(160))
    assumptions: Mapped[dict] = mapped_column(JSON)
    result: Mapped[dict] = mapped_column(JSON)
    digest: Mapped[str] = mapped_column(String(64))
    __table_args__ = tenant_args(tenant_fk("unit_id", "units"), tenant_fk("actor_id", "users"),
        ForeignKeyConstraint(["organization_id", "unit_id", "scenario_id"], ["scenario_versions.organization_id", "scenario_versions.unit_id", "scenario_versions.id"]))


class OptimizationRun(Tenant, Base):
    __tablename__ = "optimization_runs"
    unit_id: Mapped[str] = mapped_column(String(36))
    scenario_id: Mapped[str] = mapped_column(String(36))
    actor_id: Mapped[str] = mapped_column(String(36))
    name: Mapped[str] = mapped_column(String(160))
    inputs: Mapped[dict] = mapped_column(JSON)
    snapshot: Mapped[dict] = mapped_column(JSON)
    input_digest: Mapped[str] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(24), default="queued")
    revision: Mapped[int] = mapped_column(Integer, default=1)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    lease_token: Mapped[str | None] = mapped_column(String(36))
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    error_code: Mapped[str | None] = mapped_column(String(64))
    __table_args__ = tenant_args(tenant_fk("unit_id", "units"), tenant_fk("actor_id", "users"),
        ForeignKeyConstraint(["organization_id", "unit_id", "scenario_id"], ["scenario_versions.organization_id", "scenario_versions.unit_id", "scenario_versions.id"]),
        UniqueConstraint("organization_id", "unit_id", "id"), CheckConstraint("state IN ('queued','running','succeeded','failed','cancelled')", name="valid_state"),
        Index("ix_optimization_runs_queue", "state", "lease_until", "created_at"))


class ScheduleVersion(Tenant, Base):
    __tablename__ = "schedule_versions"
    unit_id: Mapped[str] = mapped_column(String(36))
    run_id: Mapped[str] = mapped_column(String(36))
    parent_id: Mapped[str | None] = mapped_column(String(36))
    series_id: Mapped[str] = mapped_column(String(36))
    version: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(160))
    state: Mapped[str] = mapped_column(String(24), default="draft")
    revision: Mapped[int] = mapped_column(Integer, default=1)
    payload: Mapped[dict] = mapped_column(JSON)
    verification: Mapped[dict] = mapped_column(JSON)
    digest: Mapped[str] = mapped_column(String(64))
    __table_args__ = tenant_args(tenant_fk("unit_id", "units"), tenant_fk("parent_id", "schedule_versions"),
        ForeignKeyConstraint(["organization_id", "unit_id", "run_id"], ["optimization_runs.organization_id", "optimization_runs.unit_id", "optimization_runs.id"]),
        UniqueConstraint("organization_id", "run_id"), UniqueConstraint("organization_id", "series_id", "version"),
        CheckConstraint("state IN ('draft','submitted','approved','rejected','superseded')", name="valid_state"))


class ScheduleDecision(Tenant, Base):
    __tablename__ = "schedule_decisions"
    schedule_id: Mapped[str] = mapped_column(String(36))
    actor_id: Mapped[str] = mapped_column(String(36))
    action: Mapped[str] = mapped_column(String(24))
    reason: Mapped[str] = mapped_column(Text)
    schedule_digest: Mapped[str] = mapped_column(String(64))
    input_digest: Mapped[str] = mapped_column(String(64))
    __table_args__ = tenant_args(tenant_fk("schedule_id", "schedule_versions"), tenant_fk("actor_id", "users"))


class EntityReview(Tenant, Base):
    __tablename__ = "entity_reviews"
    unit_id: Mapped[str | None] = mapped_column(String(36))
    actor_id: Mapped[str] = mapped_column(String(36))
    entity_kind: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[str] = mapped_column(String(36))
    entity_digest: Mapped[str] = mapped_column(String(64))
    source: Mapped[str] = mapped_column(Text)
    evidence: Mapped[str] = mapped_column(Text)
    __table_args__ = tenant_args(tenant_fk("unit_id", "units"), tenant_fk("actor_id", "users"))


class QueueState:
    state: Mapped[str] = mapped_column(String(24), default="queued")
    revision: Mapped[int] = mapped_column(Integer, default=1)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    attempt_limit: Mapped[int] = mapped_column(Integer, default=3)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    lease_token: Mapped[str | None] = mapped_column(String(36))
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(64))


class AutomationDefinition(Tenant, Base):
    __tablename__ = "automation_definitions"
    unit_id: Mapped[str] = mapped_column(String(36))
    code: Mapped[str] = mapped_column(String(3))
    name: Mapped[str] = mapped_column(String(160))
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    owner_id: Mapped[str | None] = mapped_column(String(36))
    interval_minutes: Mapped[int | None] = mapped_column(Integer)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    parameters: Mapped[dict] = mapped_column(JSON, default=dict)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    __table_args__ = tenant_args(tenant_fk("unit_id", "units"), tenant_fk("owner_id", "users"),
        UniqueConstraint("organization_id", "unit_id", "code"), CheckConstraint("code IN ('A01','A02','A03','A04','A05','A06','A07')", name="valid_code"))


class OutboxEvent(QueueState, Tenant, Base):
    __tablename__ = "outbox_events"
    unit_id: Mapped[str] = mapped_column(String(36))
    actor_id: Mapped[str | None] = mapped_column(String(36))
    kind: Mapped[str] = mapped_column(String(80))
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[str] = mapped_column(String(36))
    correlation_id: Mapped[str] = mapped_column(String(36))
    dedupe_key: Mapped[str] = mapped_column(String(180))
    source: Mapped[str] = mapped_column(String(24), default="event")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    __table_args__ = tenant_args(tenant_fk("unit_id", "units"), tenant_fk("actor_id", "users"),
        UniqueConstraint("organization_id", "dedupe_key"), CheckConstraint("state IN ('queued','running','succeeded','failed','cancelled')", name="valid_state"),
        Index("ix_outbox_events_queue", "state", "next_attempt_at", "lease_until"))


class AutomationExecution(Tenant, Base):
    __tablename__ = "automation_executions"
    unit_id: Mapped[str] = mapped_column(String(36))
    definition_id: Mapped[str] = mapped_column(String(36))
    event_id: Mapped[str] = mapped_column(String(36))
    actor_id: Mapped[str | None] = mapped_column(String(36))
    code: Mapped[str] = mapped_column(String(3))
    source: Mapped[str] = mapped_column(String(24))
    attempt: Mapped[int] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String(24))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    error_code: Mapped[str | None] = mapped_column(String(64))
    __table_args__ = tenant_args(tenant_fk("unit_id", "units"), tenant_fk("definition_id", "automation_definitions"),
        tenant_fk("event_id", "outbox_events"), tenant_fk("actor_id", "users"), UniqueConstraint("organization_id", "definition_id", "event_id", "attempt"))


class AutomationNotice(Tenant, Base):
    __tablename__ = "automation_notices"
    unit_id: Mapped[str] = mapped_column(String(36))
    definition_id: Mapped[str] = mapped_column(String(36))
    recipient_id: Mapped[str | None] = mapped_column(String(36))
    code: Mapped[str] = mapped_column(String(3))
    dedupe_key: Mapped[str] = mapped_column(String(180))
    severity: Mapped[str] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(String(160))
    body: Mapped[str] = mapped_column(Text)
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[str] = mapped_column(String(36))
    acknowledged_by: Mapped[str | None] = mapped_column(String(36))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revision: Mapped[int] = mapped_column(Integer, default=1)
    __table_args__ = tenant_args(tenant_fk("unit_id", "units"), tenant_fk("definition_id", "automation_definitions"),
        ForeignKeyConstraint(["organization_id", "recipient_id"], ["users.organization_id", "users.id"], name="fk_automation_notices_recipient"),
        ForeignKeyConstraint(["organization_id", "acknowledged_by"], ["users.organization_id", "users.id"], name="fk_automation_notices_acknowledger"), UniqueConstraint("organization_id", "dedupe_key"))


class AutomationArtifact(Tenant, Base):
    __tablename__ = "automation_artifacts"
    unit_id: Mapped[str] = mapped_column(String(36))
    definition_id: Mapped[str] = mapped_column(String(36))
    event_id: Mapped[str] = mapped_column(String(36))
    filename: Mapped[str] = mapped_column(String(160))
    content_type: Mapped[str] = mapped_column(String(80), default="text/csv")
    content: Mapped[str] = mapped_column(Text)
    digest: Mapped[str] = mapped_column(String(64))
    finance_required: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = tenant_args(tenant_fk("unit_id", "units"), tenant_fk("definition_id", "automation_definitions"),
        tenant_fk("event_id", "outbox_events"), UniqueConstraint("organization_id", "definition_id", "event_id"))


class AutomationSuggestion(Tenant, Base):
    __tablename__ = "automation_suggestions"
    unit_id: Mapped[str] = mapped_column(String(36))
    event_id: Mapped[str] = mapped_column(String(36))
    schedule_id: Mapped[str] = mapped_column(String(36))
    source_run_id: Mapped[str] = mapped_column(String(36))
    state: Mapped[str] = mapped_column(String(24), default="pending")
    reason: Mapped[str] = mapped_column(Text)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    __table_args__ = tenant_args(tenant_fk("unit_id", "units"), tenant_fk("event_id", "outbox_events"),
        tenant_fk("schedule_id", "schedule_versions"), tenant_fk("source_run_id", "optimization_runs"),
        UniqueConstraint("organization_id", "event_id", "schedule_id"))


class IntegrationCredential(Tenant, Base):
    __tablename__ = "integration_credentials"
    unit_id: Mapped[str] = mapped_column(String(36))
    actor_id: Mapped[str] = mapped_column(String(36))
    name: Mapped[str] = mapped_column(String(160))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    actions: Mapped[list] = mapped_column(JSON)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    __table_args__ = tenant_args(tenant_fk("unit_id", "units"), tenant_fk("actor_id", "users"))


class IntegrationReceipt(Tenant, Base):
    __tablename__ = "integration_receipts"
    unit_id: Mapped[str] = mapped_column(String(36))
    credential_id: Mapped[str] = mapped_column(String(36))
    request_id: Mapped[str] = mapped_column(String(36))
    body_digest: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(32))
    result: Mapped[dict] = mapped_column(JSON)
    __table_args__ = tenant_args(tenant_fk("unit_id", "units"), tenant_fk("credential_id", "integration_credentials"),
        UniqueConstraint("organization_id", "credential_id", "request_id"))


class WebhookDelivery(QueueState, Tenant, Base):
    __tablename__ = "webhook_deliveries"
    unit_id: Mapped[str] = mapped_column(String(36))
    definition_id: Mapped[str] = mapped_column(String(36))
    event_id: Mapped[str] = mapped_column(String(36))
    code: Mapped[str] = mapped_column(String(3))
    last_http_status: Mapped[int | None] = mapped_column(Integer)
    __table_args__ = tenant_args(tenant_fk("unit_id", "units"), tenant_fk("definition_id", "automation_definitions"),
        tenant_fk("event_id", "outbox_events"), UniqueConstraint("organization_id", "definition_id", "event_id"),
        CheckConstraint("state IN ('queued','running','succeeded','failed','cancelled')", name="valid_state"),
        Index("ix_webhook_deliveries_queue", "state", "next_attempt_at", "lease_until"))
