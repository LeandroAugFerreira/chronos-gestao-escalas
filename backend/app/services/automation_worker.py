"""Local consumer and optional scheduler. No network while holding business locks."""
from datetime import timedelta
from uuid import uuid4
import httpx
from sqlalchemy import and_, or_, select
from app.api.dependencies import aware
from app.models import entities as m
from app.services.audit import audit
from app.services.automation_events import N8N_CODES, enqueue_definition
from app.services.automations import AutomationError, apply, owner_principal
from app.services.organization_lock import lock_organization

LEASE_SECONDS = 60


def claim(factory, model=m.OutboxEvent):
    with factory() as session:
        stamp = m.now()
        eligible = or_(and_(model.state == "queued", model.next_attempt_at <= stamp), and_(model.state == "running", model.lease_until < stamp))
        row = session.scalar(select(model).where(eligible).order_by(model.created_at, model.id).limit(1))
        if row is None:
            return None
        lock_organization(session, row.organization_id); session.refresh(row)
        if row.state not in {"queued", "running"} or row.state == "running" and row.lease_until and aware(row.lease_until) >= stamp or row.state == "queued" and aware(row.next_attempt_at) > stamp:
            return None
        if row.attempts >= row.attempt_limit:
            row.state = "failed"; row.error_code = "LEASE_RETRIES_EXHAUSTED"; row.finished_at = stamp
            row.lease_token = None; row.lease_until = None; row.revision += 1
            session.commit()
            return {"skipped": True, "id": row.id}
        row.state = "running"; row.attempts += 1; row.revision += 1
        row.started_at = stamp; row.finished_at = None; row.error_code = None
        row.lease_token = str(uuid4()); row.lease_until = stamp + timedelta(seconds=LEASE_SECONDS)
        task = {"id": row.id, "organization_id": row.organization_id, "token": row.lease_token, "model": model}
        session.commit()
        return task


def owned(session, task):
    lock_organization(session, task["organization_id"])
    row = session.get(task["model"], task["id"])
    if not row or row.state != "running" or row.lease_token != task["token"] or not row.lease_until or aware(row.lease_until) <= m.now():
        return None
    return row


def fail_task(factory, task, error, touched=()):
    with factory() as session:
        row = owned(session, task)
        if row is None:
            return False
        retry = error.transient and row.attempts < row.attempt_limit
        row.state = "queued" if retry else "failed"; row.error_code = error.code
        row.next_attempt_at = m.now() + timedelta(seconds=min(300, 5 * 2 ** (row.attempts - 1)))
        row.finished_at = m.now(); row.lease_token = None; row.lease_until = None; row.revision += 1
        if task["model"] is m.OutboxEvent:
            for definition_id, code, actor_id in touched:
                session.add(m.AutomationExecution(organization_id=row.organization_id, unit_id=row.unit_id, definition_id=definition_id,
                    event_id=row.id, actor_id=actor_id, code=code, source=row.source, attempt=row.attempts, state="failed", error_code=error.code, finished_at=m.now()))
        audit(session, row.organization_id, None, "automation." + row.state, row.__tablename__, row.id, details={"error_code": error.code, "attempt": row.attempts})
        session.commit()
        return True


def process_event(factory, task, settings):
    touched = []
    try:
        with factory() as session:
            event = owned(session, task)
            if event is None:
                return False
            query = select(m.AutomationDefinition).where(m.AutomationDefinition.organization_id == event.organization_id,
                m.AutomationDefinition.unit_id == event.unit_id, m.AutomationDefinition.code.in_(event.payload.get("codes", [])))
            if event.payload.get("definition_id"):
                query = query.where(m.AutomationDefinition.id == event.payload["definition_id"])
            definitions = session.scalars(query.order_by(m.AutomationDefinition.code)).all()
            results = []
            for definition in definitions:
                touched.append((definition.id, definition.code, definition.owner_id))
                result = apply(session, definition, event, settings) if definition.enabled else {"reason": "DISABLED"}
                state = "succeeded" if definition.enabled else "skipped"
                session.add(m.AutomationExecution(organization_id=event.organization_id, unit_id=event.unit_id, definition_id=definition.id,
                    event_id=event.id, actor_id=definition.owner_id, code=definition.code, source=event.source, attempt=event.attempts,
                    state=state, result=result, finished_at=m.now()))
                if definition.enabled:
                    definition.last_run_at = m.now()
                    if definition.code in N8N_CODES and definition.parameters.get("deliver_n8n"):
                        session.add(m.WebhookDelivery(organization_id=event.organization_id, unit_id=event.unit_id, definition_id=definition.id, event_id=event.id, code=definition.code))
                results.append({"definition_id": definition.id, "code": definition.code, "state": state, "result": result})
            if aware(event.lease_until) <= m.now():
                raise AutomationError("PROCESSING_LIMIT", transient=True)
            event.result = {"executions": results}; event.state = "succeeded"; event.finished_at = m.now()
            event.lease_token = None; event.lease_until = None; event.revision += 1
            audit(session, event.organization_id, None, "automation.event_complete", event.__tablename__, event.id, details={"definitions": len(results)})
            session.commit()
            return True
    except AutomationError as error:
        return fail_task(factory, task, error, touched)
    except (httpx.HTTPError, OSError):
        return fail_task(factory, task, AutomationError("PROCESSING_UNAVAILABLE", True), touched)
    except Exception:
        return fail_task(factory, task, AutomationError("PROCESSING_FAILED"), touched)


def process_delivery(factory, task, settings):
    try:
        with factory() as session:
            delivery = owned(session, task)
            if delivery is None:
                return False
            definition = session.get(m.AutomationDefinition, delivery.definition_id)
            if not definition.enabled or not definition.parameters.get("deliver_n8n"):
                delivery.state = "cancelled"; delivery.finished_at = m.now(); delivery.lease_token = None; delivery.lease_until = None; delivery.revision += 1
                session.commit()
                return True
            owner_principal(session, definition)
            if not settings.n8n_webhook_base_url:
                raise AutomationError("N8N_NOT_CONFIGURED")
            endpoint = settings.n8n_webhook_base_url.rstrip("/") + "/" + delivery.code.lower()
            envelope = {"request_id": delivery.id, "event_id": delivery.event_id, "definition_id": delivery.definition_id, "code": delivery.code, "sent_at": m.now().isoformat()}
            session.commit()  # release locks before HTTP; the lease fences the eventual commit
        with httpx.Client(timeout=5, trust_env=False, follow_redirects=False) as client:
            with client.stream("POST", endpoint, json=envelope, headers={"X-Chronos-Token": settings.n8n_outbound_token.get_secret_value()}) as response:
                status = response.status_code
                size = 0
                for part in response.iter_bytes():
                    size += len(part)
                    if size > 65536:
                        raise AutomationError("RESPONSE_LIMIT")
                if not 200 <= status < 300:
                    raise AutomationError(f"HTTP_{status}", status in {408, 425, 429} or status >= 500)
        with factory() as session:
            delivery = owned(session, task)
            if delivery is None:
                return False
            receipt = session.scalar(select(m.IntegrationReceipt.id).where(m.IntegrationReceipt.organization_id == delivery.organization_id,
                m.IntegrationReceipt.unit_id == delivery.unit_id, m.IntegrationReceipt.request_id == delivery.id, m.IntegrationReceipt.action == "workflow_callback"))
            if receipt is None:
                raise AutomationError("CALLBACK_NOT_CONFIRMED", True)
            delivery.state = "succeeded"; delivery.last_http_status = status; delivery.finished_at = m.now()
            delivery.lease_token = None; delivery.lease_until = None; delivery.revision += 1
            audit(session, delivery.organization_id, None, "automation.delivery_complete", delivery.__tablename__, delivery.id, details={"http_status": status})
            session.commit()
            return True
    except AutomationError as error:
        return fail_task(factory, task, error)
    except httpx.HTTPError:
        return fail_task(factory, task, AutomationError("NETWORK_UNAVAILABLE", True))
    except Exception:
        return fail_task(factory, task, AutomationError("DELIVERY_FAILED"))


def schedule_due(factory, limit=50):
    scheduled = 0
    with factory() as session:
        ids = session.execute(select(m.AutomationDefinition.id, m.AutomationDefinition.organization_id).where(
            m.AutomationDefinition.enabled.is_(True), m.AutomationDefinition.next_run_at <= m.now(),
            m.AutomationDefinition.interval_minutes.is_not(None)).order_by(m.AutomationDefinition.next_run_at, m.AutomationDefinition.id).limit(limit)).all()
    for ident, org in ids:
        with factory() as session:
            lock_organization(session, org)
            definition = session.get(m.AutomationDefinition, ident)
            stamp = m.now()
            if not definition.enabled or not definition.next_run_at or aware(definition.next_run_at) > stamp or not definition.interval_minutes:
                continue
            enqueue_definition(session, definition, definition.owner_id, "timer", f"timer:{ident}:{aware(definition.next_run_at).isoformat()}")
            # Missed ticks coalesce into one run; no catch-up storm after restart.
            definition.next_run_at = stamp + timedelta(minutes=definition.interval_minutes)
            session.commit(); scheduled += 1
    return scheduled


def work_once(factory, settings, scheduler=False):
    if scheduler:
        schedule_due(factory)
    task = claim(factory)
    if task:
        return True if task.get("skipped") else process_event(factory, task, settings)
    task = claim(factory, m.WebhookDelivery)
    if task:
        return True if task.get("skipped") else process_delivery(factory, task, settings)
    return False
