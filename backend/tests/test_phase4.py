from datetime import date
from sqlalchemy import select, update
from app.models.entities import Contract, EmployeeQualification, LaborRule, WorkPattern
from app.services.seed import demo_id
from test_phase2 import context, headers, user_for


def shift(**changes):
    return {"employee_id": demo_id("hh-0001"), "department_id": demo_id("direction"), "start_at": "2026-11-02T08:00:00-03:00", "end_at": "2026-11-02T17:00:00-03:00", "breaks": [{"start_at": "2026-11-02T12:00:00-03:00", "end_at": "2026-11-02T13:00:00-03:00", "paid": False}], **changes}


def body(ctx, **changes):
    with ctx["factory"]() as session:
        from app.models.entities import Employee
        person = session.get(Employee, demo_id("hh-0001"))
        return shift(department_id=person.department_id, **changes)


def preview(ctx, data, id=None):
    response = ctx["client"].post("/api/v1/calendar/preview" + ("?shift_id=" + id if id else ""), headers=headers(ctx), json=data)
    assert response.status_code == 200, response.text
    return response.json()


def save(ctx, data, key=None):
    auth = headers(ctx) | ({"Idempotency-Key": key} if key else {})
    response = ctx["client"].post("/api/v1/calendar", headers=auth, json=data | {"preview_digest": preview(ctx, data)["digest"]})
    assert response.status_code == 201, response.text
    return response.json()


def rule(ctx, kind="max_daily", **changes):
    payload = {"key": kind, "version": 1, "kind": kind, "minutes": 480, "valid_from": "2026-01-01T00:00:00Z", "valid_until": "2027-01-01T00:00:00Z", "source": "Hipótese de teste, sem validade jurídica", **changes}
    response = ctx["client"].post("/api/v1/labor-rules", headers=headers(ctx), json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_preview_save_edit_cancel_and_immutable_history(context):
    data = body(context)
    result = preview(context, data)
    assert result["actual_minutes"] == result["payable_minutes"] == 480
    assert result["elapsed_minutes"] == 540
    assert result["status"] == "pending"
    assert any(f["status"] == "missing" for f in result["findings"])
    saved = save(context, data)
    assert saved["revision"] == 1
    changed = data | {"label": "Ajustado"}
    payload = changed | {"revision": 1, "preview_digest": preview(context, changed, saved["id"])["digest"]}
    url = "/api/v1/calendar/" + saved["id"]
    assert context["client"].patch(url, headers=headers(context), json=payload).status_code == 200
    assert context["client"].patch(url, headers=headers(context), json=payload).status_code == 409
    assert len(context["client"].get(url + "/evaluations", headers=headers(context)).json()["items"]) == 2
    assert context["client"].post(url + "/cancel", headers=headers(context), json={"revision": 2}).status_code == 200
    assert context["client"].post(url + "/cancel", headers=headers(context), json={"revision": 2}).status_code == 409
    response = context["client"].get("/api/v1/calendar", headers=headers(context), params={"start": data["start_at"], "end": "2026-11-09T08:00:00-03:00"})
    assert response.status_code == 200 and response.json()["total"] == 0


def test_midnight_paid_break_and_invalid_intervals(context):
    data = body(context, start_at="2026-11-02T22:00:00-03:00", end_at="2026-11-03T06:00:00-03:00", breaks=[{"start_at": "2026-11-03T01:00:00-03:00", "end_at": "2026-11-03T02:00:00-03:00", "paid": True}])
    result = preview(context, data)
    assert result["actual_minutes"] == 420 and result["payable_minutes"] == 480
    for bad in [data | {"start_at": "2026-11-02T22:00:00"}, data | {"end_at": data["start_at"]}, data | {"breaks": data["breaks"] * 2}]:
        assert context["client"].post("/api/v1/calendar/preview", headers=headers(context), json=bad).status_code == 422


def test_versions_effective_boundaries_conflicts_and_stale_preview(context):
    data = body(context)
    old = preview(context, data)
    rule(context, minutes=420)
    stale = context["client"].post("/api/v1/calendar", headers=headers(context), json=data | {"preview_digest": old["digest"]})
    assert stale.status_code == 409 and stale.json()["code"] == "PREVIEW_EXPIRED"
    result = preview(context, data)
    assert result["status"] == "nonconform" and any(f["code"] == "MAX_DAILY" for f in result["findings"])
    rule(context, version=2, minutes=600)
    assert any(f["code"] == "RULE_CONFLICT" for f in preview(context, data)["findings"])
    immutable = context["client"].patch("/api/v1/labor-rules/missing", headers=headers(context), json={"minutes": 900})
    assert immutable.status_code in {404, 405}
    # Vigência termina exatamente no início: não se aplica.
    rule(context, kind="min_break", valid_until=data["start_at"], minutes=900)
    assert not any(f["code"] == "MIN_BREAK" for f in preview(context, data)["findings"])


def test_adjacent_history_weekly_totals_and_unavailability(context):
    data = body(context)
    save(context, data)
    rule(context, kind="min_rest", minutes=660)
    rule(context, kind="max_weekly", minutes=600)
    following = body(context, start_at="2026-11-03T01:00:00-03:00", end_at="2026-11-03T09:00:00-03:00", breaks=[])
    result = preview(context, following)
    assert any(f["code"] == "MIN_REST" and f["evidence"]["actual_minutes"] == 480 for f in result["findings"])
    assert any(f["code"] == "MAX_WEEKLY" and f["status"] == "nonconform" for f in result["findings"])
    assert any(f["code"] == "SHIFT_OVERLAP" for f in preview(context, data)["findings"])
    response = context["client"].post("/api/v1/employees/" + data["employee_id"] + "/availability", headers=headers(context), json={"start_at": following["start_at"], "end_at": following["end_at"], "type": "unavailable", "reason": "Teste"})
    assert response.status_code == 201, response.text
    assert any(f["code"] == "UNAVAILABLE" for f in preview(context, following)["findings"])


def test_rule_scope_permissions_and_review_evidence(context):
    data = body(context)
    user_for(context, "manager4", "manager")
    assert context["client"].get("/api/v1/labor-rules", headers=headers(context, "manager4")).status_code == 200
    assert context["client"].post("/api/v1/labor-rules", headers=headers(context, "manager4"), json={}).status_code == 403
    unit = context["client"].post("/api/v1/units", headers=headers(context), json={"name": "Outra unidade"}).json()
    rule(context, unit_id=unit["id"], minutes=1)
    assert not any(f["code"] == "MAX_DAILY" for f in preview(context, data)["findings"])
    user_for(context, "outside4", "manager", unit["id"])
    assert context["client"].post("/api/v1/calendar/preview", headers=headers(context, "outside4"), json=data).status_code == 404
    assert context["client"].post("/api/v1/work-patterns", headers=headers(context), json={"name": "4x3", "description": "Hipótese condicionada ao contrato"}).json()["legal_status"] == "pending_review"
    invalid = {"key": "x", "version": 1, "kind": "max_daily", "minutes": 500, "source": "Teste", "valid_from": "2026-01-01T00:00:00Z", "valid_until": "2027-01-01T00:00:00Z", "status": "validated"}
    assert context["client"].post("/api/v1/labor-rules", headers=headers(context), json=invalid).status_code == 422


def test_idempotency_and_snapshots_survive_new_rule(context):
    data = body(context)
    digest = preview(context, data)["digest"]
    auth = headers(context) | {"Idempotency-Key": "calendar-test-1042"}
    payload = data | {"preview_digest": digest}
    first = context["client"].post("/api/v1/calendar", headers=auth, json=payload)
    assert first.status_code == 201, first.text
    rule(context, minutes=1)
    second = context["client"].post("/api/v1/calendar", headers=auth, json=payload)
    assert second.status_code == 201 and second.json()["id"] == first.json()["id"]
    assert second.json()["evaluation"]["digest"] == digest
    history = context["client"].get("/api/v1/calendar/" + first.json()["id"] + "/evaluations", headers=headers(context)).json()["items"]
    assert len(history) == 1 and history[0]["snapshot"]["digest"] == digest


def validated_facts(ctx):
    with ctx["factory"].begin() as session:
        session.execute(update(Contract).where(Contract.employee_id == demo_id("hh-0001")).values(validation_status="validated"))
        session.execute(update(WorkPattern).values(legal_status="validated"))
        session.execute(update(EmployeeQualification).where(EmployeeQualification.employee_id == demo_id("hh-0001")).values(verification_status="validated"))


def test_four_statuses_without_hiding_missing_rules(context):
    validated_facts(context)
    data = body(context)
    assert preview(context, data)["status"] == "missing"
    # Apenas teste: nenhuma aprovação jurídica é feita na demonstração real.
    for kind, limit in [("max_daily", 480), ("max_weekly", 2400), ("min_break", 60), ("min_rest", 660), ("min_weekly_rest", 1440)]:
        rule(context, kind=kind, minutes=limit, status="validated", review_evidence="Declaração sintética exclusiva de teste; escopo analisado.")
    assert preview(context, data)["status"] == "pending"  # Sem histórico adjacente.
    save(context, body(context, start_at="2026-10-30T08:00:00-03:00", end_at="2026-10-30T16:00:00-03:00", breaks=[]))
    assert preview(context, data)["status"] == "conform"
    broken = body(context, breaks=[])
    assert preview(context, broken)["status"] == "nonconform"


def test_daily_local_midnight_and_partial_effective_rule(context):
    data = body(context, start_at="2026-11-02T22:00:00-03:00", end_at="2026-11-03T06:00:00-03:00", breaks=[])
    rule(context, minutes=360)
    daily = [f for f in preview(context, data)["findings"] if f["code"] == "MAX_DAILY"]
    assert [f["evidence"]["actual_minutes"] for f in daily] == [120, 360]
    assert all(f["status"] == "conform" for f in daily)
    rule(context, kind="min_break", valid_from="2026-11-03T00:00:00-03:00", minutes=60)
    findings = preview(context, data)["findings"]
    assert any(f["code"] == "RULE_MISSING" and f["evidence"]["kind"] == "min_break" for f in findings)


def test_future_shift_rest_and_contiguous_breaks(context):
    data = body(context)
    rule(context, kind="min_rest", minutes=660)
    rule(context, kind="min_break", minutes=60)
    following = body(context, start_at="2026-11-03T01:00:00-03:00", end_at="2026-11-03T09:00:00-03:00", breaks=[])
    save(context, following)
    result = preview(context, data)
    assert any(f["code"] == "MIN_REST" and f["evidence"]["window"] == "posterior" and f["status"] == "nonconform" for f in result["findings"])
    data["breaks"] = [{"start_at": "2026-11-02T12:00:00-03:00", "end_at": "2026-11-02T12:30:00-03:00", "paid": False}, {"start_at": "2026-11-02T12:30:00-03:00", "end_at": "2026-11-02T13:00:00-03:00", "paid": True}]
    result = preview(context, data)
    assert result["actual_minutes"] == 480 and result["payable_minutes"] == 510
    assert any(f["code"] == "MIN_BREAK" and f["status"] == "conform" for f in result["findings"])


def test_contract_scope_clips_rule_and_pattern_configuration(context):
    data = body(context, start_at="2026-11-02T22:00:00-03:00", end_at="2026-11-03T06:00:00-03:00", breaks=[])
    with context["factory"].begin() as session:
        contract = session.scalar(select(Contract).where(Contract.employee_id == data["employee_id"]))
        contract.valid_until = date(2026, 11, 3)
        contract_id = contract.id
    rule(context, contract_id=contract_id, minutes=900)
    findings = preview(context, data)["findings"]
    assert any(f["code"] == "RULE_MISSING" and f["evidence"]["kind"] == "max_daily" and f["evidence"]["start"] == "2026-11-03T03:00:00+00:00" for f in findings)
    response = context["client"].post("/api/v1/work-patterns", headers=headers(context), json={"name": "5x2 custom", "description": "Hipótese cíclica", "configuration": {"cycle": ["work"] * 5 + ["rest"] * 2, "shift_minutes": 480}})
    assert response.status_code == 201 and response.json()["configuration"]["cycle"][-1] == "rest"


def test_explicit_successor_replaces_only_from_its_start_and_preserves_snapshot(context):
    data = body(context)
    first = rule(context, minutes=420)
    saved = save(context, data)
    second = rule(context, version=2, minutes=600, supersedes_id=first["id"], valid_from="2026-11-03T00:00:00-03:00")
    assert second["supersedes_id"] == first["id"]
    # Segunda-feira ainda aplica a v1; terça-feira aplica apenas a v2.
    assert any(f["code"] == "MAX_DAILY" and f["evidence"]["version"] == 1 for f in preview(context, data)["findings"])
    following = body(context, start_at="2026-11-03T08:00:00-03:00", end_at="2026-11-03T17:00:00-03:00", breaks=[{"start_at": "2026-11-03T12:00:00-03:00", "end_at": "2026-11-03T13:00:00-03:00", "paid": False}])
    result = preview(context, following)
    daily = [f for f in result["findings"] if f["code"] == "MAX_DAILY"]
    assert len(daily) == 1 and daily[0]["evidence"]["version"] == 2
    assert not any(f["code"] == "RULE_CONFLICT" for f in result["findings"])
    history = context["client"].get("/api/v1/calendar/" + saved["id"] + "/evaluations", headers=headers(context)).json()["items"]
    assert history[0]["snapshot"]["rules"][0]["version"] == 1
    bad = {"key": "max_daily", "version": 3, "kind": "max_daily", "minutes": 700, "supersedes_id": second["id"], "valid_from": "2026-01-01T00:00:00Z", "valid_until": "2027-01-01T00:00:00Z", "source": "Teste"}
    assert context["client"].post("/api/v1/labor-rules", headers=headers(context), json=bad).status_code == 422


def test_restore_demo_removes_calendar_rules_and_successor_chain(context):
    from app.models.entities import CalendarShift, Organization, ScheduleEvaluation
    from app.services.demo import load_demo
    from app.services.seed import restore_demo, seed_demo
    first = rule(context)
    rule(context, version=2, supersedes_id=first["id"], minutes=450)
    save(context, body(context))
    with context["factory"].begin() as session:
        org = session.get(Organization, context["org"])
        restore_demo(session, org, "Hospital Horizonte", "test")
        seed_demo(session, load_demo())
        for model in [CalendarShift, LaborRule, ScheduleEvaluation]:
            assert session.scalar(select(model.id).where(model.organization_id == org.id)) is None
