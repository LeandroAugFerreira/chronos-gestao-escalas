from copy import deepcopy
from datetime import timedelta
from pathlib import Path
from sqlalchemy import select, update
from app.models.entities import (CalendarShift, Contract, Employee, OptimizationRun, ScheduleVersion, WorkPattern, now)
from app.services.optimization_snapshot import capture, signed
from app.services.optimization_worker import claim, finish, heartbeat, work_once
from app.services.seed import demo_id
from test_phase2 import context, headers, user_for
from test_phase5 import create_scenario, scenario_body
from test_optimizer import snapshot


def enqueue(ctx, **changes):
    base = scenario_body(ctx)
    scenario = create_scenario(ctx, demands=[{"name": "Cobertura sintética", "department_id": base["department_id"], "start_time": "08:00", "duration_minutes": 480,
        "weekdays": list(range(7)), "required_staff": 1, "source": "Demanda escolhida exclusivamente para teste"}])
    options = snapshot()["options"] | {"scenario_id": scenario["id"], "eligibility": "hypothesis", "mode": "diagnostic", "cycle_anchors": {}, "activity_job_role_ids": {}, **changes}
    response = ctx["client"].post("/api/v1/optimization", headers=headers(ctx) | {"Idempotency-Key": "optimization-test-1042"}, json=options)
    assert response.status_code == 202, response.text
    return response.json(), options


def test_queue_snapshot_and_real_worker(context, tmp_path):
    row, options = enqueue(context)
    assert row["state"] == "queued" and row["result"] == {}
    again = context["client"].post("/api/v1/optimization", headers=headers(context) | {"Idempotency-Key": "optimization-test-1042"}, json=options)
    assert again.status_code == 202 and again.json()["id"] == row["id"]
    assert "snapshot" not in row and "salary" not in str(row)
    assert work_once(context["factory"], context["settings"], tmp_path)
    finished = context["client"].get("/api/v1/optimization/" + row["id"], headers=headers(context)).json()
    assert finished["state"] == "succeeded", finished
    assert finished["result"]["solver_status"] == "OPTIMAL"
    assert finished["result"]["verification"]["valid"]
    assert finished["schedule_id"]
    with context["factory"]() as session:
        assert session.scalar(select(CalendarShift.id)) is None
        proposal = session.get(ScheduleVersion, finished["schedule_id"])
        assert proposal.state == "draft" and proposal.version == 1
    blocked = context["client"].post("/api/v1/schedules/" + finished["schedule_id"] + "/decision", headers=headers(context),
        json={"revision": 1, "schedule_digest": proposal.digest, "action": "submit", "reason": "Teste com premissas ainda pendentes"})
    assert blocked.status_code == 409 and blocked.json()["code"] == "APPROVAL_BLOCKED"


def test_cancellation_lease_recovery_and_fencing(context):
    row, _ = enqueue(context)
    task = claim(context["factory"])
    assert task and heartbeat(context["factory"], task)
    with context["factory"].begin() as session:
        session.execute(update(OptimizationRun).where(OptimizationRun.id == row["id"]).values(lease_until=now() - timedelta(seconds=1)))
    replacement = claim(context["factory"])
    assert replacement["token"] != task["token"]
    assert not finish(context["factory"], task, "irrelevant", error="STALE")
    current = context["client"].get("/api/v1/optimization/" + row["id"], headers=headers(context)).json()
    cancelled = context["client"].post("/api/v1/optimization/" + row["id"] + "/cancel", headers=headers(context), json={"revision": current["revision"]})
    assert cancelled.status_code == 200 and cancelled.json()["cancel_requested"]
    assert not heartbeat(context["factory"], replacement)
    assert finish(context["factory"], replacement, "irrelevant", error="CANCEL")
    assert context["client"].get("/api/v1/optimization/" + row["id"], headers=headers(context)).json()["state"] == "cancelled"


def test_scope_redaction_and_queued_cancel(context):
    row, _ = enqueue(context)
    unit = row["unit_id"]
    user_for(context, "readonly", "analyst", unit)
    detail = context["client"].get("/api/v1/optimization/" + row["id"], headers=headers(context, "readonly"))
    assert detail.status_code == 200 and "cost_cents" not in str(detail.json())
    assert context["client"].post("/api/v1/optimization/" + row["id"] + "/cancel", headers=headers(context, "readonly"), json={"revision": 1}).status_code == 403
    assert context["client"].post("/api/v1/optimization/" + row["id"] + "/cancel", headers=headers(context), json={"revision": 9}).status_code == 409
    cancelled = context["client"].post("/api/v1/optimization/" + row["id"] + "/cancel", headers=headers(context), json={"revision": 1})
    assert cancelled.status_code == 200 and cancelled.json()["state"] == "cancelled"
    assert claim(context["factory"]) is None


def test_review_requires_current_digest_and_explicit_evidence(context):
    auth = headers(context); client = context["client"]
    targets = client.get("/api/v1/optimization-review-targets?kind=contract&page_size=1", headers=auth)
    assert targets.status_code == 200
    target = targets.json()["items"][0]
    data = {"kind": "contract", "entity_id": target["id"], "entity_digest": target["entity_digest"], "source": "Documento sintético de teste", "evidence": "Revisão de contrato registrada pelo responsável sintético"}
    assert client.post("/api/v1/optimization-reviews", headers=auth, json=data | {"entity_digest": "0" * 64}).status_code == 409
    assert client.post("/api/v1/optimization-reviews", headers=auth, json=data).status_code == 201
    with context["factory"]() as session:
        assert session.get(Contract, target["id"]).validation_status == "validated"


def validated_proposal(ctx):
    """Use real captured facts; explicitly review synthetic inputs in this isolated test only."""
    row, _ = enqueue(ctx, eligibility="verified")
    # Use the employee's actual role rather than guessing a fixture role identifier.
    with ctx["factory"].begin() as session:
        run = session.get(OptimizationRun, row["id"])
        person = next(p for p in run.snapshot["facts"]["employees"] if p["id"] == demo_id("hh-0001"))
        pattern = session.get(WorkPattern, next(c for c in run.snapshot["facts"]["contracts"] if c["employee_id"] == person["id"])["work_pattern_id"])
        pattern.configuration = {"cycle": ["work"], "shift_minutes": 480}; pattern.legal_status = "validated"
        session.execute(update(Contract).where(Contract.employee_id.in_([p["id"] for p in run.snapshot["facts"]["employees"]])).values(validation_status="validated"))
        from app.models.entities import EmployeeQualification
        session.execute(update(EmployeeQualification).where(EmployeeQualification.employee_id == person["id"]).values(verification_status="validated"))
        from app.models.entities import LaborRule, ScenarioVersion
        for kind, value in [("max_daily", 480), ("max_weekly", 2400), ("min_rest", 600), ("min_break", 0), ("min_weekly_rest", 1440)]:
            from datetime import datetime
            session.add(LaborRule(organization_id=ctx["org"], key="solver-" + kind, version=1, kind=kind, minutes=value, threshold_minutes=480,
                valid_from=datetime.fromisoformat("2026-01-01T00:00:00+00:00"), valid_until=datetime.fromisoformat("2027-01-01T00:00:00+00:00"),
                source="Hipótese sintética para teste de fluxo", status="validated", review_evidence="Revisão sintética de teste, sem valor normativo", reviewer_id=ctx["user"]))
        scenario = session.get(ScenarioVersion, run.scenario_id)
        from app.models.entities import EntityReview
        session.add(EntityReview(organization_id=ctx["org"], unit_id=run.unit_id, actor_id=ctx["user"], entity_kind="scenario", entity_id=scenario.id,
            entity_digest=scenario.digest, source="Hipótese sintética para teste", evidence="Demanda e histórico sintéticos conferidos"))
        run.inputs = run.inputs | {"activity_job_role_ids": {"0": [person["job_role_id"]]}, "cycle_anchors": {pattern.id: "2026-11-02"}}
        session.flush()
        run.snapshot = capture(session, scenario, run.inputs)
        run.input_digest = signed(run.snapshot, ctx["settings"].jwt_secret.get_secret_value())
    task = claim(ctx["factory"])
    from app.services.optimizer import solve
    result = solve(deepcopy(task["snapshot"]))
    assert result["assignments"], result["candidate_rejections"]
    assert result["approval_blockers"] == [], result["approval_blockers"]
    assert finish(ctx["factory"], task, ctx["settings"].jwt_secret.get_secret_value(), result)
    return ctx["client"].get("/api/v1/optimization/" + row["id"], headers=headers(ctx)).json()


def test_approval_two_people_and_freshness(context):
    # Prepare the second reviewer before calculation so the snapshot is stable.
    user_for(context, "approver", "manager")
    run = validated_proposal(context)
    client = context["client"]; auth = headers(context)
    proposal = client.get("/api/v1/schedules/" + run["schedule_id"], headers=auth).json()
    data = {"revision": proposal["revision"], "schedule_digest": proposal["digest"], "action": "submit", "reason": "Proposta sintética revisada para submissão"}
    submitted = client.post("/api/v1/schedules/" + proposal["id"] + "/decision", headers=auth, json=data)
    assert submitted.status_code == 200, submitted.text
    data.update(revision=2, action="approve")
    assert client.post("/api/v1/schedules/" + proposal["id"] + "/decision", headers=auth, json=data).status_code == 403
    approved = client.post("/api/v1/schedules/" + proposal["id"] + "/decision", headers=headers(context, "approver"), json=data)
    assert approved.status_code == 200 and approved.json()["state"] == "approved", approved.text
    frozen = client.get("/api/v1/schedules/" + proposal["id"], headers=auth).json()
    assert len(frozen["decisions"]) == 2 and frozen["digest"] == proposal["digest"]


def test_changed_data_blocks_submission(context):
    run = validated_proposal(context)
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from time import sleep
    from app.services.organization_lock import lock_organization
    auth = headers(context)
    proposal = context["client"].get("/api/v1/schedules/" + run["schedule_id"], headers=auth).json()
    started = Event()
    def submit():
        started.set()
        return context["client"].post("/api/v1/schedules/" + proposal["id"] + "/decision", headers=auth,
            json={"revision": 1, "schedule_digest": proposal["digest"], "action": "submit", "reason": "Teste de bloqueio após mudança concorrente"})
    with context["factory"]() as writer, ThreadPoolExecutor(max_workers=1) as executor:
        lock_organization(writer, context["org"])
        writer.execute(update(Employee).where(Employee.id == demo_id("hh-0001")).values(preferences={"preferred_shift": "night"}))
        future = executor.submit(submit)
        assert started.wait(timeout=10)
        sleep(0.2)
        assert not future.done()  # decision cannot pass the transaction still holding the organization
        writer.commit()
        response = future.result(timeout=20)
    assert response.status_code == 409 and response.json()["code"] == "STALE_INPUTS"


def test_actual_worker_cancel_keeps_proposal_absent(context, tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from time import monotonic, sleep
    row, _ = enqueue(context)
    auth = headers(context)
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(work_once, context["factory"], context["settings"], tmp_path)
        deadline = monotonic() + 15
        while monotonic() < deadline:
            with context["factory"]() as session:
                current = session.get(OptimizationRun, row["id"])
                state, revision = current.state, current.revision
            if state == "running":
                break
            sleep(0.02)
        assert state == "running"
        response = context["client"].post("/api/v1/optimization/" + row["id"] + "/cancel", headers=auth, json={"revision": revision})
        assert response.status_code == 200, response.text
        assert future.result(timeout=40)
    with context["factory"]() as session:
        assert session.get(OptimizationRun, row["id"]).state == "cancelled"
        assert session.scalar(select(ScheduleVersion.id).where(ScheduleVersion.run_id == row["id"])) is None


def test_version_derivation_preserves_approved_parent_until_decision(context):
    user_for(context, "approver", "manager")
    initial = validated_proposal(context)
    client = context["client"]; auth = headers(context); reviewer = headers(context, "approver")
    original = client.get("/api/v1/schedules/" + initial["schedule_id"], headers=auth).json()
    decision = {"revision": 1, "schedule_digest": original["digest"], "action": "submit", "reason": "Conteúdo sintético revisado para teste"}
    assert client.post("/api/v1/schedules/" + original["id"] + "/decision", headers=auth, json=decision).status_code == 200
    assert client.post("/api/v1/schedules/" + original["id"] + "/decision", headers=reviewer, json=decision | {"revision": 2, "action": "approve"}).status_code == 200
    options = initial["inputs"] | {"name": "Versão filha", "parent_schedule_id": original["id"]}
    queued = client.post("/api/v1/optimization", headers=auth, json=options)
    assert queued.status_code == 202, queued.text
    task = claim(context["factory"])
    from app.services.optimizer import solve
    result = solve(deepcopy(task["snapshot"]))
    assert result["assignments"] and result["approval_blockers"] == []
    assert finish(context["factory"], task, context["settings"].jwt_secret.get_secret_value(), result)
    detail = client.get("/api/v1/optimization/" + queued.json()["id"], headers=auth).json()
    child = client.get("/api/v1/schedules/" + detail["schedule_id"], headers=auth).json()
    assert child["version"] == 2 and child["parent_id"] == original["id"]
    assert client.get("/api/v1/schedules/" + original["id"], headers=auth).json()["state"] == "approved"
    decision.update(schedule_digest=child["digest"])
    assert client.post("/api/v1/schedules/" + child["id"] + "/decision", headers=auth, json=decision).status_code == 200
    assert client.post("/api/v1/schedules/" + child["id"] + "/decision", headers=reviewer, json=decision | {"revision": 2, "action": "approve"}).status_code == 200
    preserved = client.get("/api/v1/schedules/" + original["id"], headers=auth).json()
    assert preserved["state"] == "superseded" and preserved["payload"] == original["payload"]


def test_other_unit_cannot_observe_or_enqueue(context):
    row, options = enqueue(context)
    from app.models.entities import Unit
    with context["factory"].begin() as session:
        other = Unit(organization_id=context["org"], name="Unidade distinta de teste", operation="administrative")
        session.add(other); session.flush(); unit = other.id
    user_for(context, "other-manager", "manager", unit)
    auth = headers(context, "other-manager")
    assert context["client"].get("/api/v1/optimization/" + row["id"], headers=auth).status_code == 404
    assert context["client"].get("/api/v1/optimization", headers=auth).json()["total"] == 0
    assert context["client"].post("/api/v1/optimization", headers=auth, json=options).status_code == 404


def test_cost_and_assignments_are_redacted_from_aggregate_reader(context, tmp_path):
    templates = deepcopy(snapshot()["options"]["templates"])
    for item in templates:
        item["cost_cents"] = 12345
    row, options = enqueue(context, templates=templates, cost_weight=1, cost_source="Custo hipotético confidencial para teste")
    user_for(context, "aggregate", "analyst", row["unit_id"])
    user_for(context, "local-manager", "manager", row["unit_id"])
    assert work_once(context["factory"], context["settings"], tmp_path)
    own = context["client"].get("/api/v1/optimization/" + row["id"], headers=headers(context)).json()
    assert own["result"]["estimated_cost_cents"] > 0
    redacted = context["client"].get("/api/v1/optimization/" + row["id"], headers=headers(context, "aggregate")).json()
    assert "assignments" not in redacted["result"] and "estimated_cost_cents" not in redacted["result"]
    assert "cost_cents" not in str(redacted["inputs"]) and "cost_source" not in redacted["inputs"]
    stage = next(s for s in redacted["result"]["stages"] if s["stage"] == "cost_balance_preferences")
    assert "objective" not in stage and "best_bound" not in stage
    response = context["client"].post("/api/v1/optimization", headers=headers(context, "local-manager"), json=options)
    assert response.status_code == 403
