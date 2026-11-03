import hashlib
import secrets
from datetime import timedelta
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import or_, select
from app.api.dependencies import aware, bearer, fail, get_db, principal_for_user, require
from app.api.resources import as_dict, related
from app.api.simulation import check_permission
from app.models import entities as m
from app.repositories.scoped import get_scoped, page, scoped
from app.schemas.automation import CallbackInput, CredentialInput, DefinitionPatch, IntegratedAvailability, QueueAction
from app.services import idempotency
from app.services.audit import audit
from app.services.automation_events import CODE_PERMISSIONS, N8N_CODES, enqueue_definition
from app.services.automations import AutomationError, apply, owner_principal
from app.services.optimization_snapshot import signed
from app.services.organization_lock import lock_organization

router = APIRouter(prefix="/api/v1", tags=["Automações e integração local"])
DEFINITION_FIELDS = ["id", "unit_id", "code", "name", "enabled", "owner_id", "interval_minutes", "next_run_at", "last_run_at", "parameters", "revision"]
QUEUE_FIELDS = ["id", "unit_id", "state", "revision", "attempts", "attempt_limit", "next_attempt_at", "started_at", "finished_at", "error_code", "created_at"]


def reference_view(row, fields, principal):
    result = as_dict(row, fields)
    permission = "audit:read" if row.entity_type in {"users", "user_roles"} else "people:read" if row.entity_type in {"employees", "contracts", "employee_qualifications", "availability_rules"} else None
    if permission and not principal.permits(permission, row.unit_id):
        result["entity_id"] = None
    return result


def execution_view(row, principal):
    result = as_dict(row, ["id", "unit_id", "definition_id", "event_id", "code", "source", "attempt", "state", "started_at", "finished_at", "result", "error_code"])
    if not principal.permits(CODE_PERMISSIONS[row.code], row.unit_id):
        result["result"] = {"restricted": True}
    return result


@router.get("/automations")
def definitions(request: Request, unit_id: str | None = None, page_number: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), principal=Depends(require("automation:read")), session=Depends(get_db)):
    query = scoped(m.AutomationDefinition, principal, "automation:read", m.AutomationDefinition.unit_id)
    if unit_id:
        query = query.where(m.AutomationDefinition.unit_id == unit_id)
    result = page(session, query.order_by(m.AutomationDefinition.unit_id, m.AutomationDefinition.code), page_number, page_size, lambda r: as_dict(r, DEFINITION_FIELDS))
    result["integration_configured"] = bool(request.app.state.settings.n8n_webhook_base_url)
    return result


@router.patch("/automations/{id}")
def configure(id: str, payload: DefinitionPatch, request: Request, principal=Depends(require("automation:manage")), session=Depends(get_db)):
    row = get_scoped(session, m.AutomationDefinition, id, principal, "automation:manage", m.AutomationDefinition.unit_id)
    if row.revision != payload.revision:
        fail(409, "REVISION_CONFLICT", "A automação mudou. Atualize a configuração.")
    check_permission(principal, CODE_PERMISSIONS[row.code], row.unit_id)
    owner_id = payload.owner_id or principal.user.id
    related(session, m.User, owner_id, principal)
    row.owner_id = owner_id
    if payload.enabled:
        try:
            owner_principal(session, row)
        except AutomationError:
            fail(422, "OWNER_PERMISSION_REQUIRED", "O responsável precisa estar ativo e autorizado para a rotina nesta unidade.")
    if payload.parameters.deliver_n8n and (row.code not in N8N_CODES or not request.app.state.settings.n8n_webhook_base_url):
        fail(422, "N8N_NOT_CONFIGURED", "Configure a integração local antes de habilitar o envio desta rotina.")
    row.enabled = payload.enabled; row.parameters = payload.parameters.model_dump(); row.interval_minutes = payload.interval_minutes
    row.next_run_at = m.now() + timedelta(minutes=row.interval_minutes) if row.enabled and row.interval_minutes else None
    row.revision += 1
    audit(session, row.organization_id, principal.user.id, "automation.configure", row.__tablename__, row.id, request.state.correlation_id, {"code": row.code, "enabled": row.enabled})
    session.commit()
    return as_dict(row, DEFINITION_FIELDS)


@router.post("/automations/{id}/run", status_code=202)
def manual_run(id: str, payload: QueueAction, request: Request, principal=Depends(require("automation:run")), session=Depends(get_db)):
    row = get_scoped(session, m.AutomationDefinition, id, principal, "automation:run", m.AutomationDefinition.unit_id)
    check_permission(principal, CODE_PERMISSIONS[row.code], row.unit_id)
    if row.revision != payload.revision or not row.enabled:
        fail(409, "AUTOMATION_UNAVAILABLE", "A rotina está desativada ou sua revisão mudou.")
    existing, pending = idempotency.prepare(session, request, principal, m.OutboxEvent, payload.model_dump())
    if existing:
        return as_dict(existing, QUEUE_FIELDS)
    event = enqueue_definition(session, row, principal.user.id)
    idempotency.record(session, pending, event.id)
    audit(session, row.organization_id, principal.user.id, "automation.enqueue", event.__tablename__, event.id, request.state.correlation_id, {"code": row.code})
    session.commit()
    return as_dict(event, QUEUE_FIELDS)


@router.get("/automation-events")
def events(unit_id: str | None = None, page_number: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), principal=Depends(require("automation:read")), session=Depends(get_db)):
    query = scoped(m.OutboxEvent, principal, "automation:read", m.OutboxEvent.unit_id)
    if unit_id:
        query = query.where(m.OutboxEvent.unit_id == unit_id)
    return page(session, query.order_by(m.OutboxEvent.created_at.desc(), m.OutboxEvent.id), page_number, page_size,
        lambda r: reference_view(r, QUEUE_FIELDS + ["kind", "entity_type", "entity_id", "source", "correlation_id"], principal))


@router.get("/automation-executions")
def executions(unit_id: str | None = None, code: str | None = None, page_number: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), principal=Depends(require("automation:read")), session=Depends(get_db)):
    query = scoped(m.AutomationExecution, principal, "automation:read", m.AutomationExecution.unit_id)
    if unit_id:
        query = query.where(m.AutomationExecution.unit_id == unit_id)
    if code:
        query = query.where(m.AutomationExecution.code == code)
    return page(session, query.order_by(m.AutomationExecution.created_at.desc(), m.AutomationExecution.id), page_number, page_size,
        lambda r: execution_view(r, principal))


@router.get("/automation-deliveries")
def deliveries(page_number: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), principal=Depends(require("automation:read")), session=Depends(get_db)):
    return page(session, scoped(m.WebhookDelivery, principal, "automation:read", m.WebhookDelivery.unit_id).order_by(m.WebhookDelivery.created_at.desc(), m.WebhookDelivery.id),
        page_number, page_size, lambda r: as_dict(r, QUEUE_FIELDS + ["code", "event_id", "definition_id", "last_http_status"]))


@router.post("/automation-queue/{kind}/{id}/{action}")
def queue_action(kind: str, id: str, action: str, payload: QueueAction, request: Request, principal=Depends(require("automation:run")), session=Depends(get_db)):
    if kind not in {"events", "deliveries"} or action not in {"retry", "cancel"}:
        fail(404, "NOT_FOUND", "Operação inexistente.")
    model = m.OutboxEvent if kind == "events" else m.WebhookDelivery
    row = get_scoped(session, model, id, principal, "automation:run", model.unit_id)
    if row.revision != payload.revision or action == "retry" and row.state != "failed" or action == "cancel" and row.state not in {"queued", "running"}:
        fail(409, "REVISION_CONFLICT", "Estado ou revisão mudou. Atualize a fila.")
    row.lease_token = None; row.lease_until = None; row.revision += 1
    if action == "retry":
        row.state = "queued"; row.next_attempt_at = m.now(); row.attempt_limit = row.attempts + 3; row.error_code = None; row.finished_at = None
    else:
        row.state = "cancelled"; row.finished_at = m.now()
    audit(session, row.organization_id, principal.user.id, "automation." + action, row.__tablename__, row.id, request.state.correlation_id)
    session.commit()
    return as_dict(row, QUEUE_FIELDS)


@router.get("/automation-notices")
def notices(page_number: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), principal=Depends(require("automation:read")), session=Depends(get_db)):
    query = scoped(m.AutomationNotice, principal, "automation:read", m.AutomationNotice.unit_id).where(or_(m.AutomationNotice.recipient_id.is_(None), m.AutomationNotice.recipient_id == principal.user.id))
    return page(session, query.order_by(m.AutomationNotice.created_at.desc(), m.AutomationNotice.id), page_number, page_size,
        lambda r: reference_view(r, ["id", "unit_id", "code", "severity", "title", "body", "entity_type", "entity_id", "acknowledged_at", "revision", "created_at"], principal))


@router.post("/automation-notices/{id}/acknowledge")
def acknowledge(id: str, payload: QueueAction, request: Request, principal=Depends(require("automation:read")), session=Depends(get_db)):
    row = get_scoped(session, m.AutomationNotice, id, principal, "automation:read", m.AutomationNotice.unit_id)
    if row.recipient_id not in {None, principal.user.id}:
        fail(404, "NOT_FOUND", "Aviso não encontrado.")
    if row.recipient_id is None:
        check_permission(principal, "automation:run", row.unit_id)
    if row.revision != payload.revision or row.acknowledged_at:
        fail(409, "REVISION_CONFLICT", "O aviso já mudou.")
    row.acknowledged_at = m.now(); row.acknowledged_by = principal.user.id; row.revision += 1
    audit(session, row.organization_id, principal.user.id, "automation.acknowledge", row.__tablename__, row.id, request.state.correlation_id)
    session.commit()
    return {"id": row.id, "revision": row.revision, "acknowledged_at": aware(row.acknowledged_at)}


@router.get("/automation-artifacts")
def artifacts(page_number: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), principal=Depends(require("automation:read")), session=Depends(get_db)):
    query = scoped(m.AutomationArtifact, principal, "automation:read", m.AutomationArtifact.unit_id)
    if not principal.permits("finance:read"):
        financial_units = principal.scopes.get("finance:read") or set()
        query = query.where(or_(m.AutomationArtifact.finance_required.is_(False), m.AutomationArtifact.unit_id.in_(financial_units)))
    return page(session, query.order_by(m.AutomationArtifact.created_at.desc(), m.AutomationArtifact.id), page_number, page_size,
        lambda r: as_dict(r, ["id", "unit_id", "filename", "content_type", "digest", "finance_required", "created_at"]))


@router.get("/automation-artifacts/{id}")
def artifact(id: str, principal=Depends(require("automation:read")), session=Depends(get_db)):
    row = get_scoped(session, m.AutomationArtifact, id, principal, "automation:read", m.AutomationArtifact.unit_id)
    if row.finance_required:
        check_permission(principal, "finance:read", row.unit_id)
    return as_dict(row, ["id", "filename", "content_type", "digest", "content"])


@router.get("/automation-suggestions")
def suggestions(page_number: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), principal=Depends(require("optimization:read")), session=Depends(get_db)):
    return page(session, scoped(m.AutomationSuggestion, principal, "optimization:read", m.AutomationSuggestion.unit_id)
        .order_by(m.AutomationSuggestion.created_at.desc(), m.AutomationSuggestion.id), page_number, page_size,
        lambda r: as_dict(r, ["id", "unit_id", "event_id", "schedule_id", "source_run_id", "reason", "details", "state", "revision", "created_at"]))


@router.post("/integration-credentials", status_code=201)
def credential(payload: CredentialInput, request: Request, principal=Depends(require("integration:manage")), session=Depends(get_db)):
    for permission in ["integration:manage", "automation:run"] + (["people:write"] if "availability" in payload.actions else []):
        check_permission(principal, permission, payload.unit_id)
    related(session, m.Unit, payload.unit_id, principal)
    token = "chr_" + secrets.token_urlsafe(36)
    row = m.IntegrationCredential(organization_id=principal.user.organization_id, unit_id=payload.unit_id, actor_id=principal.user.id,
        name=payload.name, actions=payload.actions, token_hash=hashlib.sha256(token.encode()).hexdigest())
    session.add(row); session.flush()
    audit(session, row.organization_id, principal.user.id, "integration.create_credential", row.__tablename__, row.id, request.state.correlation_id)
    session.commit()
    return {**as_dict(row, ["id", "unit_id", "name", "actions", "enabled", "revision"]), "token_once": token}


@router.get("/integration-credentials")
def credentials(page_number: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), principal=Depends(require("integration:manage")), session=Depends(get_db)):
    return page(session, scoped(m.IntegrationCredential, principal, "integration:manage", m.IntegrationCredential.unit_id).order_by(m.IntegrationCredential.created_at.desc()),
        page_number, page_size, lambda r: as_dict(r, ["id", "unit_id", "name", "actions", "enabled", "revision", "created_at"]))


@router.post("/integration-credentials/{id}/revoke")
def revoke(id: str, payload: QueueAction, request: Request, principal=Depends(require("integration:manage")), session=Depends(get_db)):
    row = get_scoped(session, m.IntegrationCredential, id, principal, "integration:manage", m.IntegrationCredential.unit_id)
    if row.revision != payload.revision:
        fail(409, "REVISION_CONFLICT", "A credencial mudou.")
    row.enabled = False; row.revision += 1
    audit(session, row.organization_id, principal.user.id, "integration.revoke_credential", row.__tablename__, row.id, request.state.correlation_id)
    session.commit()
    return {"id": row.id, "enabled": False, "revision": row.revision}


def integration_actor(credentials=Depends(bearer), session=Depends(get_db)):
    if credentials is None:
        fail(401, "UNAUTHORIZED", "Credencial de integração necessária.")
    token_hash = hashlib.sha256(credentials.credentials.encode()).hexdigest()
    row = session.scalar(select(m.IntegrationCredential).where(m.IntegrationCredential.token_hash == token_hash, m.IntegrationCredential.enabled.is_(True)))
    if not row:
        fail(401, "INVALID_INTEGRATION_TOKEN", "Credencial de integração inválida ou revogada.")
    lock_organization(session, row.organization_id)
    session.refresh(row)
    user = session.get(m.User, row.actor_id)
    if not row.enabled or not user or not user.active:
        fail(401, "INVALID_INTEGRATION_TOKEN", "Credencial de integração inválida ou revogada.")
    principal = principal_for_user(session, user)
    for permission in ["integration:manage", "automation:run"]:
        check_permission(principal, permission, row.unit_id)
    return row, principal


def receipt_context(session, credential, action, payload, settings):
    if action not in credential.actions:
        fail(403, "FORBIDDEN", "A credencial não autoriza esta ação.")
    content = payload.model_dump(mode="json", exclude={"sent_at"})
    fingerprint = signed({"action": action, "content": content}, settings.jwt_secret.get_secret_value())
    previous = session.scalar(select(m.IntegrationReceipt).where(m.IntegrationReceipt.organization_id == credential.organization_id,
        m.IntegrationReceipt.credential_id == credential.id, m.IntegrationReceipt.request_id == str(payload.request_id)))
    if previous:
        if previous.body_digest != fingerprint or previous.action != action:
            fail(409, "REPLAY_CONFLICT", "Identificador já utilizado com outro conteúdo.")
        return previous.result, fingerprint
    if abs((m.now() - payload.sent_at).total_seconds()) > 300:
        fail(422, "STALE_INTEGRATION_REQUEST", "Uma nova requisição deve ter timestamp atual.")
    return None, fingerprint


def save_receipt(session, credential, request_id, fingerprint, action, result):
    session.add(m.IntegrationReceipt(organization_id=credential.organization_id, unit_id=credential.unit_id, credential_id=credential.id,
        request_id=str(request_id), body_digest=fingerprint, action=action, result=result))


@router.post("/integration/automation-events")
def callback(payload: CallbackInput, request: Request, identity=Depends(integration_actor), session=Depends(get_db)):
    credential, principal = identity
    existing, fingerprint = receipt_context(session, credential, "workflow_callback", payload, request.app.state.settings)
    if existing is not None:
        return {**existing, "replayed": True}
    delivery = session.scalar(select(m.WebhookDelivery).where(m.WebhookDelivery.id == str(payload.request_id), m.WebhookDelivery.organization_id == credential.organization_id,
        m.WebhookDelivery.unit_id == credential.unit_id, m.WebhookDelivery.definition_id == str(payload.definition_id), m.WebhookDelivery.event_id == str(payload.event_id), m.WebhookDelivery.code == payload.code))
    if not delivery or delivery.state not in {"running", "succeeded"}:
        fail(404, "NOT_FOUND", "Entrega autorizada não encontrada.")
    definition = session.get(m.AutomationDefinition, delivery.definition_id)
    check_permission(principal, CODE_PERMISSIONS[definition.code], delivery.unit_id)
    if not definition.enabled or not definition.parameters.get("deliver_n8n"):
        fail(409, "AUTOMATION_UNAVAILABLE", "A rotina está desativada para integração.")
    try:
        result = apply(session, definition, session.get(m.OutboxEvent, delivery.event_id), request.app.state.settings)
    except AutomationError:
        fail(409, "AUTOMATION_UNAVAILABLE", "O responsável não está autorizado a executar a rotina.")
    execution_id = request.headers.get("X-Chronos-Workflow-Execution", "")
    if execution_id and (len(execution_id) > 64 or not execution_id.replace("-", "").isalnum()):
        fail(422, "INVALID_EXECUTION_REFERENCE", "Identificador de execução inválido.")
    response = {"accepted": True, "delivery_id": delivery.id, "code": delivery.code, "result": result, "workflow_execution_id": execution_id or None}
    save_receipt(session, credential, payload.request_id, fingerprint, "workflow_callback", response)
    audit(session, credential.organization_id, credential.actor_id, "automation.n8n_callback", delivery.__tablename__, delivery.id, request.state.correlation_id)
    session.commit()
    return response


@router.post("/integration/availability", status_code=201)
def integrated_availability(payload: IntegratedAvailability, request: Request, identity=Depends(integration_actor), session=Depends(get_db)):
    credential, principal = identity
    check_permission(principal, "people:write", credential.unit_id)
    existing, fingerprint = receipt_context(session, credential, "availability", payload, request.app.state.settings)
    if existing is not None:
        return {**existing, "replayed": True}
    person = session.scalar(select(m.Employee).where(m.Employee.organization_id == credential.organization_id, m.Employee.unit_id == credential.unit_id, m.Employee.id == payload.employee_id))
    if person is None:
        fail(404, "NOT_FOUND", "Profissional não encontrado nesta unidade.")
    values = payload.model_dump(exclude={"request_id", "sent_at", "employee_id"})
    row = m.AvailabilityRule(organization_id=credential.organization_id, employee_id=person.id, **values)
    session.add(row); session.flush()
    response = {"id": row.id, "type": row.type, "accepted": True}
    save_receipt(session, credential, payload.request_id, fingerprint, "availability", response)
    audit(session, row.organization_id, credential.actor_id, "create", row.__tablename__, row.id, request.state.correlation_id)
    session.commit()
    return response
