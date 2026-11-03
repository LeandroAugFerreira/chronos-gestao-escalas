from copy import deepcopy
import pytest
from app.schemas.optimization import OptimizationInput
from app.services.optimizer import approval_blockers, check_solution, prepare, solve


def snapshot(people=3, **changes):
    options = OptimizationInput.model_validate({"scenario_id": "s", "name": "Teste sintético", "start_date": "2026-11-02", "end_date": "2026-11-03",
        "templates": [{"name": str(h), "start_time": f"{h:02}:00", "duration_minutes": 480} for h in [0, 8, 16]],
        "limits": {"max_daily_minutes": 480, "max_weekly_minutes": 2400, "min_rest_minutes": 600,
            "min_break_minutes": 0, "break_threshold_minutes": 480, "min_weekly_rest_minutes": 1440, "max_consecutive_days": 5,
            "source": "Parâmetros sintéticos, sem caráter normativo", "validation_status": "validated", "review_evidence": "Revisão exclusivamente para este teste sintético"},
        "activity_job_role_ids": {"0": ["role"]}, "history_review_evidence": "Histórico sintético completo conferido para teste", "cycle_anchors": {"pattern": "2026-11-02"},
        **changes}).model_dump(mode="json")
    demand = {"department_id": "dept", "skill_ids": [], "qualification_ids": [], "weekdays": list(range(7)), "start_time": "00:00", "duration_minutes": 1440, "required_staff": 1, "validation_status": "validated"}
    return {"algorithm_version": "chronos-cpsat-1.0", "scenario": {"id": "s", "unit_id": "unit", "department_id": "dept", "digest": "d" * 64,
        "inputs": {"demands": [demand], "validation_status": "validated"}}, "options": options,
        "facts": {"units": [{"id": "unit", "timezone": "America/Sao_Paulo"}],
        "employees": [{"id": f"p{i}", "status": "active", "unit_id": "unit", "department_id": "dept", "job_role_id": "role", "preferences": {}} for i in range(people)],
        "contracts": [{"id": f"c{i}", "employee_id": f"p{i}", "work_pattern_id": "pattern", "valid_from": "2020-01-01", "valid_until": None, "weekly_minutes": 2400, "validation_status": "validated"} for i in range(people)],
        "work_patterns": [{"id": "pattern", "configuration": {"cycle": ["work"], "shift_minutes": 480}, "legal_status": "validated"}],
        "employee_skills": [], "employee_qualifications": [], "role_skills": [], "role_qualifications": [], "availability_rules": [], "calendar_shifts": [],
        "approved_schedules": [], "scenario_reviews": [],
        "labor_rules": [{"id": kind, "kind": kind, "supersedes_id": None, "contract_id": None, "unit_id": None, "job_role_id": None,
            "valid_from": "2026-01-01T00:00:00+00:00", "valid_until": "2027-01-01T00:00:00+00:00", "minutes": value, "threshold_minutes": 480, "status": "validated"}
            for kind, value in [("max_daily", 480), ("max_weekly", 2400), ("min_rest", 600), ("min_break", 0), ("min_weekly_rest", 1440)]]}}


def test_full_day_optimal_and_deterministic():
    first, second = solve(snapshot()), solve(snapshot())
    assert first["solver_status"] == "OPTIMAL"
    assert first["verification"]["valid"] and first["verification"]["covered_staff_minutes"] == 1440
    assert len(first["assignments"]) == 3 and first["approval_blockers"] == []
    assert first["assignments"] == second["assignments"]


@pytest.mark.parametrize("mode,status,gap", [("strict", "INFEASIBLE", None), ("diagnostic", "OPTIMAL", 480)])
def test_insufficient_staff_has_explicit_gap(mode, status, gap):
    result = solve(snapshot(2, mode=mode))
    assert result["solver_status"] == status
    if gap:
        assert result["verification"]["uncovered_staff_minutes"] == gap
        assert "UNCOVERED_DEMAND" in result["approval_blockers"]


def test_pauses_do_not_cover_patient_demand():
    data = snapshot(mode="diagnostic")
    for template in data["options"]["templates"]:
        template.update(break_after_minutes=240, break_minutes=60)
    result = solve(data)
    assert result["verification"]["uncovered_staff_minutes"] == 180


@pytest.mark.parametrize("constraint", ["skill", "qualification", "absence", "history", "cycle", "contract"])
def test_hard_eligibility_and_history(constraint):
    data = snapshot(1, mode="diagnostic")
    demand = data["scenario"]["inputs"]["demands"][0]
    if constraint == "skill":
        demand["skill_ids"] = ["required"]
    elif constraint == "qualification":
        demand["qualification_ids"] = ["required"]
    elif constraint == "absence":
        data["facts"]["availability_rules"] = [{"employee_id": "p0", "type": "unavailable", "start_at": "2026-11-02T00:00:00-03:00", "end_at": "2026-11-03T00:00:00-03:00"}]
    elif constraint == "history":
        data["facts"]["calendar_shifts"] = [{"employee_id": "p0", "unit_id": "unit", "state": "draft", "start_at": "2026-11-02T00:00:00-03:00", "end_at": "2026-11-03T00:00:00-03:00", "breaks": []}]
    elif constraint == "cycle":
        data["facts"]["work_patterns"][0]["configuration"]["cycle"] = ["rest"]
    else:
        data["facts"]["contracts"] = []
    result = solve(data)
    assert not result["assignments"] and result["verification"]["uncovered_staff_minutes"] == 1440


def test_independent_verifier_rejects_overlap_and_forged_ids():
    data = prepare(snapshot())
    own = [c["id"] for c in data["candidates"] if c["employee_id"] == "p0"]
    assert not check_solution(data, own)["valid"]  # more than one shift exceeds daily cap/rest
    assert not check_solution(data, [999999])["valid"]


def test_pending_evidence_blocks_approval_without_legal_defaults():
    data = snapshot()
    data["options"]["limits"]["validation_status"] = "pending_review"
    data["options"]["history_review_evidence"] = ""
    result = solve(data)
    assert result["verification"]["valid"] and result["approval_blockers"]


def test_continuity_limit_is_hard_even_in_diagnostic():
    result = solve(snapshot(mode="diagnostic", continuity_max_people_per_activity_day=1))
    assert result["verification"]["uncovered_staff_minutes"] == 960


def test_two_activities_cannot_double_count_one_person():
    data = snapshot(1, mode="diagnostic")
    data["scenario"]["inputs"]["demands"].append(deepcopy(data["scenario"]["inputs"]["demands"][0]))
    data["options"]["activity_job_role_ids"]["1"] = ["role"]
    result = solve(data)
    assert len(result["assignments"]) == 1
    assert result["verification"]["uncovered_staff_minutes"] == 2400


def test_rest_from_other_unit_and_travel_are_preserved():
    data = snapshot(1, mode="diagnostic")
    data["scenario"]["inputs"]["demands"][0].update(start_time="08:00", duration_minutes=480)
    data["facts"]["calendar_shifts"] = [{"employee_id": "p0", "unit_id": "other", "state": "draft", "start_at": "2026-11-01T12:00:00-03:00", "end_at": "2026-11-01T20:00:00-03:00", "breaks": []}]
    baseline = solve(deepcopy(data))
    assert len(baseline["assignments"]) == 1  # twelve hours between shifts
    rule = deepcopy(next(r for r in data["facts"]["labor_rules"] if r["kind"] == "min_rest"))
    rule.update(id="other-unit-rest", unit_id="other", minutes=900)
    data["facts"]["labor_rules"].append(rule)
    assert not solve(deepcopy(data))["assignments"]
    data["facts"]["labor_rules"].pop()
    data["options"]["cross_unit_travel_minutes"] = 180
    assert not solve(data)["assignments"]


def test_weekly_contract_budget_and_rest_cannot_be_relaxed():
    data = snapshot(1, mode="diagnostic", end_date="2026-11-04")
    data["facts"]["contracts"][0]["weekly_minutes"] = 480
    result = solve(data)
    assert len(result["assignments"]) == 1 and result["verification"]["uncovered_staff_minutes"] == 2400
    data = snapshot(1, mode="diagnostic")
    data["options"]["limits"]["min_weekly_rest_minutes"] = 10080
    assert not solve(data)["assignments"]


def test_expired_qualification_and_rule_successor():
    data = snapshot(1, mode="diagnostic")
    data["scenario"]["inputs"]["demands"][0]["qualification_ids"] = ["q"]
    data["facts"]["employee_qualifications"] = [{"employee_id": "p0", "qualification_id": "q", "valid_from": "2020-01-01", "valid_until": "2026-11-02", "verification_status": "validated"}]
    assert not solve(deepcopy(data))["assignments"]
    data["facts"]["employee_qualifications"][0]["valid_until"] = "2027-01-01"
    assert solve(deepcopy(data))["assignments"]
    parent = next(r for r in data["facts"]["labor_rules"] if r["kind"] == "max_daily")
    successor = deepcopy(parent)
    successor.update(id="new-cap", supersedes_id=parent["id"], valid_from="2026-11-02T00:00:00+00:00", minutes=240)
    data["facts"]["labor_rules"].append(successor)
    assert not solve(data)["assignments"]


def test_expired_computation_budget_reports_unknown(monkeypatch):
    import app.services.optimizer as optimizer
    clock = iter([0.0, 1000.0, 1000.0])
    monkeypatch.setattr(optimizer, "monotonic", lambda: next(clock))
    result = optimizer.solve(snapshot())
    assert result["solver_status"] == "UNKNOWN" and not result["verification"]["valid"]


def test_solver_child_inherits_runtime_without_service_credentials(monkeypatch):
    from app.services.optimization_worker import solver_environment
    secrets = ["CHRONOS_TEST_POSTGRES_URL", "CHRONOS_DATABASE_URL", "CHRONOS_JWT_SECRET", "PGPASSWORD", "CHRONOS_BOOTSTRAP_PASSWORD", "OPENAI_API_KEY"]
    for name in secrets:
        monkeypatch.setenv(name, "canary-not-a-real-credential")
    environment = solver_environment()
    assert all(name not in environment for name in secrets)
    assert "PATH" in {name.upper() for name in environment}

