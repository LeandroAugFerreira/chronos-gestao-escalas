"""Outbox written in the same transaction as the business audit; no network here."""
from uuid import NAMESPACE_URL, uuid4, uuid5
from sqlalchemy import select
from app.models import entities as m

CATALOG = {
    "A01": "Conferência de cenários e propostas", "A02": "Alertas de cobertura", "A03": "Pendências de aprovação",
    "A04": "Relatório de indicadores", "A05": "Revisão de vigências", "A06": "Sugestões de reotimização", "A07": "Rastreabilidade de alterações",
}
CODE_PERMISSIONS = {"A01": "optimization:read", "A02": "optimization:read", "A03": "schedule:approve", "A04": "org:read", "A05": "people:read", "A06": "optimization:write", "A07": "audit:read"}
BUSINESS_TABLES = {"scenario_versions", "calendar_shifts", "availability_rules", "labor_rules", "work_patterns", "employees", "contracts",
    "employee_qualifications", "schedule_versions", "optimization_runs", "users", "user_roles", "departments", "units"}
N8N_CODES = {"A02", "A03", "A04", "A06"}


def ensure_definitions(session, org, unit_id=None):
    units = session.scalars(select(m.Unit).where(m.Unit.organization_id == org, *([m.Unit.id == unit_id] if unit_id else []))).all()
    for unit in units:
        existing = set(session.scalars(select(m.AutomationDefinition.code).where(m.AutomationDefinition.organization_id == org, m.AutomationDefinition.unit_id == unit.id)))
        for code, name in CATALOG.items():
            if code not in existing:
                session.add(m.AutomationDefinition(id=str(uuid5(NAMESPACE_URL, f"chronos/automation/{org}/{unit.id}/{code}")),
                    organization_id=org, unit_id=unit.id, code=code, name=name, enabled=False,
                    parameters={"lookahead_days": 30, "monitor_limit": 100, "deliver_n8n": False}))


def codes_for(kind, entity_type):
    codes = {"A07"}
    if entity_type in {"scenario_versions", "calendar_shifts", "labor_rules", "contracts", "work_patterns", "schedule_versions", "optimization_runs"}:
        codes.add("A01")
    if entity_type in {"scenario_versions", "calendar_shifts", "schedule_versions"} or kind == "optimization.succeeded":
        codes.add("A02")
    if kind == "schedule.submit":
        codes.add("A03")
    if entity_type in {"labor_rules", "contracts", "employee_qualifications", "work_patterns"}:
        codes.add("A05")
    if entity_type == "availability_rules":
        codes.add("A06")
    return sorted(codes)


def publish_audit(session, audit_row):
    entity = audit_row.entity_type
    if entity not in BUSINESS_TABLES or audit_row.action.startswith(("automation.", "integration.", "auth.", "demo.")):
        return
    # Capture references only. Reasons, names, salaries and credentials never enter this envelope.
    model = next((mapper.class_ for mapper in m.Base.registry.mappers if mapper.local_table.name == entity), None)
    row = session.get(model, audit_row.entity_id) if model else None
    if row is not None and row.organization_id != audit_row.organization_id:
        return
    unit_id = getattr(row, "unit_id", None)
    if entity == "units":
        unit_id = audit_row.entity_id
    if row is not None and getattr(row, "employee_id", None):
        person = session.get(m.Employee, row.employee_id)
        unit_id = person.unit_id if person else unit_id
    units = [unit_id] if unit_id else list(session.scalars(select(m.Unit.id).where(m.Unit.organization_id == audit_row.organization_id)))
    kind = audit_row.action if "." in audit_row.action else entity + "." + audit_row.action
    for ident in units:
        ensure_definitions(session, audit_row.organization_id, ident)
        session.add(m.OutboxEvent(organization_id=audit_row.organization_id, unit_id=ident, actor_id=audit_row.actor_id,
            kind=kind, entity_type=entity, entity_id=audit_row.entity_id, correlation_id=audit_row.correlation_id,
            dedupe_key=f"audit:{audit_row.id}:{ident}", source="event", payload={"codes": codes_for(kind, entity)}))


def enqueue_definition(session, definition, actor, source="manual", dedupe_key=None):
    if dedupe_key:
        existing = session.scalar(select(m.OutboxEvent).where(m.OutboxEvent.organization_id == definition.organization_id, m.OutboxEvent.dedupe_key == dedupe_key))
        if existing:
            return existing
    event = m.OutboxEvent(organization_id=definition.organization_id, unit_id=definition.unit_id, actor_id=actor,
        kind="automation." + source, entity_type="automation_definitions", entity_id=definition.id,
        correlation_id=str(uuid4()), dedupe_key=dedupe_key or "manual:" + str(uuid4()), source=source,
        payload={"codes": [definition.code], "definition_id": definition.id})
    session.add(event); session.flush()
    return event
