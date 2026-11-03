from datetime import timedelta
from uuid import uuid4
from sqlalchemy import func, select, update
from app.models import entities as m
from app.services import automation_worker as worker
from app.services.automation_events import enqueue_definition
from app.services.automations import AutomationError
from app.services.seed import demo_id
from test_phase2 import context, headers, user_for


def configure(ctx, code, **changes):
    auth = headers(ctx)
    found = ctx["client"].get("/api/v1/automations", headers=auth).json()["items"]
    definition = next(d for d in found if d["code"] == code)
    response = ctx["client"].patch("/api/v1/automations/" + definition["id"], headers=auth,
        json={"revision": definition["revision"], "enabled": True, "parameters": {"monitor_limit": 5}, **changes})
    assert response.status_code == 200, response.text
    return response.json()


def queue(ctx, definition):
    response = ctx["client"].post("/api/v1/automations/" + definition["id"] + "/run", headers=headers(ctx) | {"Idempotency-Key": "manual-run-1042"}, json={"revision": definition["revision"]})
    assert response.status_code == 202, response.text
    return response.json()


def drain(ctx, limit=60):
    for _ in range(limit):
        if not worker.work_once(ctx["factory"], ctx["settings"]):
            return
    raise AssertionError("Fila não esvaziou no limite do teste")


def integration_key(ctx, actions=("workflow_callback", "availability")):
    response = ctx["client"].post("/api/v1/integration-credentials", headers=headers(ctx),
        json={"name": "Credencial sintética", "unit_id": demo_id("horizonte-main"), "actions": list(actions)})
    assert response.status_code == 201, response.text
    return response.json()


def test_definitions_disabled_and_manual_report_csv(context):
    result = context["client"].get("/api/v1/automations", headers=headers(context)).json()
    assert result["total"] == 7 and all(not d["enabled"] for d in result["items"])
    definition = configure(context, "A04")
    event = queue(context, definition)
    repeated = queue(context, definition)
    assert repeated["id"] == event["id"]
    drain(context)
    artifacts = context["client"].get("/api/v1/automation-artifacts", headers=headers(context)).json()
    assert artifacts["total"] == 1
    content = context["client"].get("/api/v1/automation-artifacts/" + artifacts["items"][0]["id"], headers=headers(context)).json()
    assert "Chronos 1.0" in content["content"] and "colaboradores;350" in content["content"]
    assert "salary" not in content["content"]
    with context["factory"]() as session:
        assert session.get(m.OutboxEvent, event["id"]).state == "succeeded"


def test_outbox_is_atomic_and_no_personal_payload(context):
    with context["factory"]() as session:
        before = session.scalar(select(func.count()).select_from(m.OutboxEvent))
        from app.services.audit import audit
        audit(session, context["org"], context["user"], "update", "employees", demo_id("hh-0001"), details={"secret": "NEVER-FORWARD-PRIVATE"})
        session.flush()
        assert session.scalar(select(func.count()).select_from(m.OutboxEvent)) == before + 1
        row = session.scalar(select(m.OutboxEvent).order_by(m.OutboxEvent.created_at.desc()))
        assert "NEVER-FORWARD" not in str(row.payload)
        session.rollback()
    with context["factory"]() as session:
        assert session.scalar(select(func.count()).select_from(m.OutboxEvent)) == before


def test_integration_availability_replay_conflict_scope_and_revocation(context):
    key = integration_key(context)
    auth = {"Authorization": "Bearer " + key["token_once"]}
    data = {"request_id": str(uuid4()), "sent_at": m.now().isoformat(), "employee_id": demo_id("hh-0001"),
        "start_at": "2026-11-02T08:00:00-03:00", "end_at": "2026-11-02T12:00:00-03:00", "type": "unavailable", "reason": "Hipótese sintética"}
    first = context["client"].post("/api/v1/integration/availability", headers=auth, json=data)
    assert first.status_code == 201, first.text
    second = context["client"].post("/api/v1/integration/availability", headers=auth, json=data)
    assert second.status_code == 201 and second.json()["id"] == first.json()["id"] and second.json()["replayed"]
    assert context["client"].post("/api/v1/integration/availability", headers=auth, json=data | {"reason": "Mudança indevida"}).status_code == 409
    assert context["client"].post("/api/v1/integration/availability", headers=auth, json=data | {"request_id": str(uuid4()), "employee_id": str(uuid4())}).status_code == 404
    listing = context["client"].get("/api/v1/integration-credentials", headers=headers(context))
    assert "token_once" not in listing.text and "token_hash" not in listing.text
    assert context["client"].post("/api/v1/integration-credentials/" + key["id"] + "/revoke", headers=headers(context), json={"revision": 1}).status_code == 200
    assert context["client"].post("/api/v1/integration/availability", headers=auth, json=data).status_code == 401


def test_scheduler_coalesces_and_lease_fences(context):
    definition = configure(context, "A07", interval_minutes=1)
    with context["factory"].begin() as session:
        session.execute(update(m.AutomationDefinition).where(m.AutomationDefinition.id == definition["id"]).values(next_run_at=m.now() - timedelta(days=2)))
    assert worker.schedule_due(context["factory"]) == 1
    assert worker.schedule_due(context["factory"]) == 0
    task = worker.claim(context["factory"])
    with context["factory"].begin() as session:
        session.execute(update(m.OutboxEvent).where(m.OutboxEvent.id == task["id"]).values(lease_until=m.now() - timedelta(seconds=1)))
    replacement = worker.claim(context["factory"])
    assert replacement["token"] != task["token"]
    assert not worker.process_event(context["factory"], task, context["settings"])
    assert worker.process_event(context["factory"], replacement, context["settings"])


def test_transient_retry_and_manual_retry_keep_attempt_history(context, monkeypatch):
    definition = configure(context, "A04")
    event = queue(context, definition)
    original = worker.apply
    def temporary(*_):
        raise AutomationError("TEMPORARY_TEST_FAILURE", True)
    monkeypatch.setattr(worker, "apply", temporary)
    task = worker.claim(context["factory"])
    assert worker.process_event(context["factory"], task, context["settings"])
    with context["factory"].begin() as session:
        row = session.get(m.OutboxEvent, event["id"])
        assert row.state == "queued" and row.attempts == 1 and row.error_code == "TEMPORARY_TEST_FAILURE"
        row.next_attempt_at = m.now() - timedelta(seconds=1)
    monkeypatch.setattr(worker, "apply", original)
    drain(context)
    with context["factory"]() as session:
        history = session.scalars(select(m.AutomationExecution).where(m.AutomationExecution.event_id == event["id"]).order_by(m.AutomationExecution.attempt)).all()
        assert [e.state for e in history] == ["failed", "succeeded"]
        assert session.scalar(select(func.count()).select_from(m.AutomationArtifact)) == 1


def test_vigency_notices_deduplicate_and_never_validate_rules(context):
    definition = configure(context, "A05")
    queue(context, definition); drain(context)
    with context["factory"]() as session:
        count = session.scalar(select(func.count()).select_from(m.AutomationNotice))
        assert count > 0
    with context["factory"].begin() as session:
        enqueue_definition(session, session.get(m.AutomationDefinition, definition["id"]), context["user"], "timer")
    drain(context)
    with context["factory"]() as session:
        assert session.scalar(select(func.count()).select_from(m.AutomationNotice)) == count
        assert session.scalar(select(func.count()).select_from(m.Contract).where(m.Contract.validation_status == "validated")) == 0
        assert session.scalar(select(func.count()).select_from(m.LaborRule)) == 0


def test_submission_notifies_only_other_current_approvers(context):
    from test_phase6 import validated_proposal
    reviewer_id = user_for(context, "reviewer", "manager")
    configure(context, "A03")
    run = validated_proposal(context)
    proposal = context["client"].get("/api/v1/schedules/" + run["schedule_id"], headers=headers(context)).json()
    response = context["client"].post("/api/v1/schedules/" + proposal["id"] + "/decision", headers=headers(context),
        json={"revision": 1, "schedule_digest": proposal["digest"], "action": "submit", "reason": "Proposta sintética submetida para teste de avisos"})
    assert response.status_code == 200, response.text
    drain(context)
    with context["factory"]() as session:
        recipients = session.scalars(select(m.AutomationNotice.recipient_id).where(m.AutomationNotice.code == "A03")).all()
        assert recipients == [reviewer_id]
    assert context["client"].get("/api/v1/automation-notices", headers=headers(context)).json()["total"] == 0
    assert context["client"].get("/api/v1/automation-notices", headers=headers(context, "reviewer")).json()["total"] == 1


def test_availability_suggests_new_version_without_replacing_existing(context):
    from test_phase6 import validated_proposal
    configure(context, "A06")
    run = validated_proposal(context)
    original = context["client"].get("/api/v1/schedules/" + run["schedule_id"], headers=headers(context)).json()
    assignment = original["payload"]["assignments"][0]
    response = context["client"].post("/api/v1/employees/" + assignment["employee_id"] + "/availability", headers=headers(context),
        json={"start_at": assignment["start_at"], "end_at": assignment["end_at"], "type": "unavailable", "reason": "Ausência sintética para verificar impacto"})
    assert response.status_code == 201
    drain(context)
    with context["factory"]() as session:
        assert session.scalar(select(func.count()).select_from(m.AutomationSuggestion)) == 1
        assert session.scalar(select(func.count()).select_from(m.OptimizationRun)) == 1
        schedule = session.get(m.ScheduleVersion, original["id"])
        assert schedule.state == "draft" and schedule.payload == original["payload"]


def test_coverage_notification_uses_stored_gap_and_deduplicates(context):
    from test_phase6 import enqueue
    from app.services.audit import audit
    configure(context, "A02")
    run, _ = enqueue(context)
    with context["factory"].begin() as session:
        row = session.get(m.OptimizationRun, run["id"])
        row.state = "succeeded"
        row.result = {"solver_status": "OPTIMAL", "verification": {"valid": True, "required_staff_minutes": 480, "uncovered_staff_minutes": 240, "gaps": [{}]}}
        audit(session, context["org"], context["user"], "optimization.succeeded", row.__tablename__, row.id)
    drain(context)
    with context["factory"]() as session:
        notices = session.scalars(select(m.AutomationNotice).where(m.AutomationNotice.code == "A02")).all()
        assert len(notices) == 1 and "240" in notices[0].body


def test_revoked_owner_fails_safely_and_manual_retry_does_not_reset_attempts(context):
    owner = user_for(context, "delegated", "manager")
    definition = configure(context, "A04", owner_id=owner)
    event = queue(context, definition)
    with context["factory"].begin() as session:
        session.get(m.User, owner).active = False
    drain(context)
    with context["factory"]() as session:
        row = session.get(m.OutboxEvent, event["id"])
        assert row.state == "failed" and row.error_code == "OWNER_UNAVAILABLE"
        revision = row.revision
    with context["factory"].begin() as session:
        session.get(m.User, owner).active = True
    retried = context["client"].post("/api/v1/automation-queue/events/" + event["id"] + "/retry", headers=headers(context), json={"revision": revision})
    assert retried.status_code == 200 and retried.json()["attempt_limit"] == 4
    drain(context)
    with context["factory"]() as session:
        row = session.get(m.OutboxEvent, event["id"])
        assert row.state == "succeeded" and row.attempts == 2


def test_financial_report_is_not_exposed_to_aggregate_reader(context):
    from test_phase5 import create_scenario, run_financial
    scenario = create_scenario(context)
    run_financial(context, scenario["id"])
    definition = configure(context, "A04")
    queue(context, definition); drain(context)
    user_for(context, "aggregate", "analyst")
    own = context["client"].get("/api/v1/automation-artifacts", headers=headers(context)).json()["items"][0]
    assert own["finance_required"]
    assert context["client"].get("/api/v1/automation-artifacts", headers=headers(context, "aggregate")).json()["total"] == 0
    assert context["client"].get("/api/v1/automation-artifacts/" + own["id"], headers=headers(context, "aggregate")).status_code == 403


def bridge_setup(ctx):
    from pydantic import SecretStr
    ctx["settings"] = ctx["settings"].model_copy(update={"n8n_webhook_base_url": "http://127.0.0.1:5687/webhook/chronos", "n8n_outbound_token": SecretStr("test-only-outbound-1042-very-long-token")})
    ctx["app"].state.settings = ctx["settings"]
    definition = configure(ctx, "A04", parameters={"monitor_limit": 5, "deliver_n8n": True})
    event = queue(ctx, definition)
    task = worker.claim(ctx["factory"])
    assert worker.process_event(ctx["factory"], task, ctx["settings"])
    with ctx["factory"]() as session:
        delivery = session.scalar(select(m.WebhookDelivery).where(m.WebhookDelivery.event_id == event["id"]))
        delivery_id = delivery.id
    return definition, event, delivery_id


def test_callback_authentication_replay_and_delivery_binding(context):
    definition, event, delivery_id = bridge_setup(context)
    task = worker.claim(context["factory"], m.WebhookDelivery)
    key = integration_key(context, ["workflow_callback"])
    data = {"request_id": delivery_id, "event_id": event["id"], "definition_id": definition["id"], "code": "A04", "sent_at": m.now().isoformat()}
    assert context["client"].post("/api/v1/integration/automation-events", json=data).status_code == 401
    auth = {"Authorization": "Bearer " + key["token_once"], "X-Chronos-Workflow-Execution": "synthetic-42"}
    assert context["client"].post("/api/v1/integration/automation-events", headers=auth, json=data | {"sent_at": (m.now() - timedelta(hours=1)).isoformat()}).status_code == 422
    assert context["client"].post("/api/v1/integration/automation-events", headers=auth, json=data | {"event_id": str(uuid4())}).status_code == 404
    first = context["client"].post("/api/v1/integration/automation-events", headers=auth, json=data)
    assert first.status_code == 200 and first.json()["workflow_execution_id"] == "synthetic-42", first.text
    assert context["client"].post("/api/v1/integration/automation-events", headers=auth, json=data).json()["replayed"]
    assert context["client"].post("/api/v1/integration/automation-events", headers=auth, json=data | {"code": "A02"}).status_code == 409
    with context["factory"]() as session:
        assert session.scalar(select(func.count()).select_from(m.IntegrationReceipt)) == 1
        assert session.scalar(select(func.count()).select_from(m.AutomationArtifact)) == 1
    assert task["id"] == delivery_id


def test_delivery_temporary_failure_retries_and_requires_actual_callback(context, monkeypatch):
    import httpx
    import json
    _, event, delivery_id = bridge_setup(context)
    key = integration_key(context, ["workflow_callback"])
    original_client = httpx.Client
    calls = []
    def transport(request):
        calls.append(str(request.url))
        if len(calls) == 1:
            return httpx.Response(503, json={"status": "synthetic-unavailable"})
        response = context["client"].post("/api/v1/integration/automation-events", headers={"Authorization": "Bearer " + key["token_once"]}, json=json.loads(request.content))
        return httpx.Response(response.status_code, json=response.json())
    monkeypatch.setattr(worker.httpx, "Client", lambda **kwargs: original_client(transport=httpx.MockTransport(transport), **kwargs))
    first = worker.claim(context["factory"], m.WebhookDelivery)
    assert worker.process_delivery(context["factory"], first, context["settings"])
    with context["factory"].begin() as session:
        delivery = session.get(m.WebhookDelivery, delivery_id)
        assert delivery.state == "queued" and delivery.error_code == "HTTP_503"
        delivery.next_attempt_at = m.now() - timedelta(seconds=1)
    second = worker.claim(context["factory"], m.WebhookDelivery)
    assert worker.process_delivery(context["factory"], second, context["settings"])
    with context["factory"]() as session:
        delivery = session.get(m.WebhookDelivery, delivery_id)
        assert delivery.state == "succeeded" and delivery.attempts == 2 and delivery.last_http_status == 200
        assert session.scalar(select(func.count()).select_from(m.AutomationArtifact).where(m.AutomationArtifact.event_id == event["id"])) == 1


def test_cancelled_queue_and_other_unit_are_isolated(context):
    definition = configure(context, "A04")
    event = queue(context, definition)
    with context["factory"].begin() as session:
        other = m.Unit(organization_id=context["org"], name="Unidade isolada", operation="administrative")
        session.add(other); session.flush(); other_id = other.id
    user_for(context, "other-manager", "manager", other_id)
    foreign = headers(context, "other-manager")
    assert context["client"].get("/api/v1/automations", headers=foreign).json()["total"] == 0
    assert context["client"].post("/api/v1/automation-queue/events/" + event["id"] + "/cancel", headers=foreign, json={"revision": event["revision"]}).status_code == 404
    cancelled = context["client"].post("/api/v1/automation-queue/events/" + event["id"] + "/cancel", headers=headers(context), json={"revision": event["revision"]})
    assert cancelled.status_code == 200 and cancelled.json()["state"] == "cancelled"
    assert worker.claim(context["factory"]) is None


def test_integration_rejects_remote_endpoint_and_unsafe_environment():
    import pytest
    from pydantic import ValidationError
    from app.core.config import Settings
    with pytest.raises(ValidationError):
        Settings(_env_file=None, n8n_webhook_base_url="http://example.invalid/webhook/chronos", n8n_outbound_token="test-only-outbound-1042-very-long-token")


def test_current_input_monitor_flags_changes_without_mutating_proposal(context):
    from test_phase6 import validated_proposal
    definition = configure(context, "A01")
    run = validated_proposal(context)
    drain(context)
    with context["factory"]() as session:
        initial = session.get(m.ScheduleVersion, run["schedule_id"])
        original_payload = initial.payload
        assert session.scalar(select(func.count()).select_from(m.AutomationNotice).where(m.AutomationNotice.code == "A01")) == 0
    with context["factory"].begin() as session:
        session.get(m.Employee, demo_id("hh-0001")).preferences = {"preferred_shift": "night"}
    queue(context, definition); drain(context)
    with context["factory"]() as session:
        execution = session.scalar(select(m.AutomationExecution).where(m.AutomationExecution.code == "A01").order_by(m.AutomationExecution.created_at.desc(), m.AutomationExecution.id))
        assert execution.result["checks"][0]["inputs_changed"]
        assert session.get(m.ScheduleVersion, run["schedule_id"]).payload == original_payload


def test_audit_and_personal_references_are_hidden_from_aggregate_reader(context):
    configure(context, "A07")
    from app.services.audit import audit
    with context["factory"].begin() as session:
        audit(session, context["org"], context["user"], "update", "users", context["user"])
        audit(session, context["org"], context["user"], "update", "employees", demo_id("hh-0001"))
    drain(context)
    user_for(context, "aggregate", "analyst")
    auth = headers(context, "aggregate")
    events = context["client"].get("/api/v1/automation-events", headers=auth).json()["items"]
    assert events and all(event["entity_id"] is None for event in events)
    executions = context["client"].get("/api/v1/automation-executions?code=A07", headers=auth).json()["items"]
    assert executions and all(row["result"] == {"restricted": True} for row in executions)


def test_date_only_vigency_uses_unit_timezone(context, monkeypatch):
    from datetime import UTC, date, datetime
    from app.services.automations import apply
    definition = configure(context, "A05", parameters={"monitor_limit": 1, "lookahead_days": 1})
    with context["factory"].begin() as session:
        row = session.scalar(select(m.Contract).order_by(m.Contract.id).limit(1))
        row.validation_status = "validated"; row.valid_until = date(2026, 10, 26); contract_id = row.id
        event = enqueue_definition(session, session.get(m.AutomationDefinition, definition["id"]), context["user"])
        event_id = event.id
    monkeypatch.setattr(m, "now", lambda: datetime(2026, 10, 25, 1, 0, tzinfo=UTC))  # Oct 24 in São Paulo
    with context["factory"].begin() as session:
        apply(session, session.get(m.AutomationDefinition, definition["id"]), session.get(m.OutboxEvent, event_id), context["settings"])
        assert session.scalar(select(m.AutomationNotice.id).where(m.AutomationNotice.entity_id == contract_id)) is None
    monkeypatch.setattr(m, "now", lambda: datetime(2026, 10, 25, 4, 0, tzinfo=UTC))  # Oct 25 in São Paulo
    with context["factory"].begin() as session:
        apply(session, session.get(m.AutomationDefinition, definition["id"]), session.get(m.OutboxEvent, event_id), context["settings"])
        assert session.scalar(select(m.AutomationNotice.id).where(m.AutomationNotice.entity_id == contract_id)) is not None
