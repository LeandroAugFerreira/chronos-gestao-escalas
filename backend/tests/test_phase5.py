from datetime import date
from decimal import Decimal
from sqlalchemy import select, update
from app.models.entities import Contract, Employee, FinancialRun, ScenarioVersion
from app.schemas.simulation import FinancialInput
from app.services.capacity import merge, subtract
from app.services.financial import difference, project
from app.services.seed import demo_id
from test_phase2 import context, headers, user_for


def scenario_body(ctx, **changes):
    with ctx["factory"]() as session:
        person = session.get(Employee, demo_id("hh-0001"))
        return {"unit_id": person.unit_id, "department_id": person.department_id, "key": "base-1042", "name": "Cenário de teste", "reference_month": "2026-11-01", "source": "Hipótese sintética de teste", **changes}


def create_scenario(ctx, **changes):
    response = ctx["client"].post("/api/v1/scenarios", headers=headers(ctx), json=scenario_body(ctx, **changes))
    assert response.status_code == 201, response.text
    return response.json()


def financial_body(id, **changes):
    return {"scenario_id": id, "name": "Projeção sintética", "source": "Hipótese de cálculo documentada", **changes}


def run_financial(ctx, id, **changes):
    response = ctx["client"].post("/api/v1/financial", headers=headers(ctx), json=financial_body(id, **changes))
    assert response.status_code == 201, response.text
    return response.json()


def payroll(salary=10000, start="2020-01-01", until=None):
    return {"employees": [{"employee_id": "p1", "contracts": [{"id": "c1", "salary_cents": salary, "currency": "BRL", "valid_from": start, "valid_until": until, "validation_status": "pending_review", "source": "Teste"}]}]}


def test_decimal_rounding_proration_and_zero_baseline():
    assumptions = FinancialInput.model_validate(financial_body("s"))
    result = project(date(2026, 11, 1), payroll(101, until="2026-11-16"), assumptions)
    assert result["months"][0]["base_payroll_cents"] == 51  # 101 × 15/30 = 50,5 → 51
    assert result["annual_total_cents"] == 51
    assert difference(0, 123)["percent"] is None
    assert difference(100, 90)["percent"] == "-10.000000"


def test_recurrence_seasonality_new_hires_and_reconciliation():
    assumptions = FinancialInput.model_validate(financial_body("s", new_hires=[{"headcount": 2, "monthly_salary_cents": 5000, "start_month": 2, "end_month": 3, "source": "Hipótese de contratação"}], components=[
        {"name": "Treinamento", "category": "training", "kind": "fixed", "amount_cents": 10001, "recurrence": "once", "start_month": 2, "source": "Orçamento único hipotético"},
        {"name": "Encargo", "category": "charge", "kind": "percent", "rate_bps": 1000, "month_indexes": [3, 6], "source": "Taxa hipotética sazonal"}]))
    result = project(date(2026, 11, 1), payroll(20000), assumptions)
    assert result["annual_base_payroll_cents"] == 260000
    assert result["annual_components_cents"]["training"] == 10001
    assert result["annual_components_cents"]["charge"] == 5000
    assert result["annual_total_cents"] == 275001 == sum(m["total_cents"] for m in result["months"])


def test_hour_conversion_basis_and_component_order_independence():
    components = [
        {"name": "Noturno hipotético", "category": "night", "kind": "hours", "hourly_base_salary_cents": 120000, "monthly_divisor_minutes": 12000,
         "rate_bps": 2000, "conversion_numerator": 8, "conversion_denominator": 7, "real_minutes_by_month": [600] + [0] * 11, "source": "Conversão e adicional hipotéticos"},
        {"name": "Extra hipotética", "category": "overtime", "kind": "hours", "hourly_base_salary_cents": 120000, "monthly_divisor_minutes": 12000,
         "rate_bps": 5000, "include_base_hour": True, "real_minutes_by_month": [60] + [0] * 11, "source": "Premissa de hora extra"},
        {"name": "Encargo hipotético", "category": "charge", "kind": "percent", "rate_bps": 1000, "percent_basis": "payroll_and_additions", "source": "Base de incidência hipotética"}]
    a = project(date(2026, 11, 1), payroll(), FinancialInput.model_validate(financial_body("s", components=components)))
    b = project(date(2026, 11, 1), payroll(), FinancialInput.model_validate(financial_body("s", components=list(reversed(components)))))
    first = a["months"][0]
    assert first["components"][0]["amount_cents"] == 1371
    assert first["components"][0]["payable_minutes"] == "685.714286"
    assert first["components"][1]["amount_cents"] == 900
    assert first["components"][2]["amount_cents"] == 1227
    assert a["annual_total_cents"] == b["annual_total_cents"]


def test_capacity_calendar_empty_no_salary_leak_and_saved_version(context):
    row = create_scenario(context)
    assert row["capacity"]["population_count"] > 0
    assert row["capacity"]["effective_budget_minutes"] == 0
    assert "payroll_snapshot" not in row and "evidence" not in row and "salary_cents" not in str(row)
    assert context["client"].patch("/api/v1/scenarios/" + row["id"], headers=headers(context), json={"name": "Mutação"}).status_code in {404, 405}
    second = create_scenario(context, version=2, parent_id=row["id"], target_weekly_minutes=2400)
    result = context["client"].post("/api/v1/scenarios/compare", headers=headers(context), json={"left_id": row["id"], "right_id": second["id"]})
    assert result.status_code == 200 and result.json()["metrics"]["effective_budget_minutes"]["percent"] is None
    assert context["client"].get("/api/v1/scenarios/" + row["id"], headers=headers(context)).json()["digest"] == row["digest"]


def test_cycle_capacity_demands_limits_and_no_calendar_writes(context):
    client = context["client"]; auth = headers(context)
    pattern = client.post("/api/v1/work-patterns", headers=auth, json={"name": "5x2 hipótese", "description": "Ciclo sintético configurado", "configuration": {"cycle": ["work"] * 5 + ["rest"] * 2, "shift_minutes": 540}}).json()
    base = scenario_body(context)
    demand = {"name": "Atividade fictícia", "department_id": base["department_id"], "start_time": "08:00", "duration_minutes": 480, "weekdays": [0, 1, 2, 3, 4], "required_staff": 100, "source": "Demanda hipotética escolhida para teste"}
    row = create_scenario(context, mode="cycle", work_pattern_id=pattern["id"], cycle_anchor="2026-11-02", break_minutes=60, eligibility="hypothesis", demands=[demand], target_weekly_minutes=2400)
    assert row["capacity"]["raw_available_minutes"] > 0
    assert row["capacity"]["effective_budget_minutes"] <= row["capacity"]["raw_available_minutes"]
    assert row["capacity"]["demands"][0]["gap_lower_bound_minutes"] > 0
    assert row["capacity"]["labor_summary"]["evaluations"] == row["capacity"]["population_count"]
    reduced = create_scenario(context, version=2, parent_id=row["id"], mode="cycle", work_pattern_id=pattern["id"], cycle_anchor="2026-11-02", break_minutes=60, eligibility="hypothesis", target_weekly_minutes=1200)
    assert reduced["capacity"]["effective_budget_minutes"] < row["capacity"]["effective_budget_minutes"]
    with context["factory"]() as session:
        from app.models.entities import CalendarShift
        assert session.scalar(select(CalendarShift.id)) is None


def test_scenario_idempotency_and_invalid_period_or_reference(context):
    data = scenario_body(context)
    auth = headers(context) | {"Idempotency-Key": "scenario-1042"}
    first = context["client"].post("/api/v1/scenarios", headers=auth, json=data)
    assert first.status_code == 201
    second = context["client"].post("/api/v1/scenarios", headers=auth, json=data)
    assert second.json()["id"] == first.json()["id"]
    assert context["client"].post("/api/v1/scenarios", headers=headers(context), json=data | {"reference_month": "2026-11-02"}).status_code == 422
    assert context["client"].post("/api/v1/scenarios", headers=headers(context), json=data | {"work_pattern_id": "other-company"}).status_code == 422


def test_financial_salary_snapshot_immutable_and_hours_reduction_no_pay_cut(context):
    first = create_scenario(context)
    a = run_financial(context, first["id"])
    second = create_scenario(context, parent_id=first["id"], version=2, target_weekly_minutes=1200)
    b = run_financial(context, second["id"])
    assert a["result"]["annual_base_payroll_cents"] == b["result"]["annual_base_payroll_cents"] > 0
    with context["factory"].begin() as session:
        session.execute(update(Contract).where(Contract.employee_id == demo_id("hh-0001")).values(base_salary_cents=1))
    frozen = context["client"].post("/api/v1/financial/preview", headers=headers(context), json=financial_body(first["id"]))
    assert frozen.json()["annual_total_cents"] == a["result"]["annual_total_cents"]
    third = create_scenario(context, parent_id=second["id"], version=3)
    c = run_financial(context, third["id"])
    comparison = context["client"].post("/api/v1/financial/compare", headers=headers(context), json={"left_id": a["id"], "right_id": c["id"]})
    assert comparison.status_code == 200 and comparison.json()["salary_check"]["decreases_detected"] == 1


def test_financial_access_scopes_and_capacity_evidence_privacy(context):
    row = create_scenario(context)
    user_for(context, "analyst5", "analyst")
    analyst = headers(context, "analyst5")
    assert context["client"].get("/api/v1/scenarios/" + row["id"], headers=analyst).status_code == 200
    assert context["client"].get("/api/v1/scenarios/" + row["id"] + "/evidence", headers=analyst).status_code == 403
    assert context["client"].post("/api/v1/financial/preview", headers=analyst, json=financial_body(row["id"])).status_code == 403
    user_for(context, "finance5", "finance")
    assert context["client"].post("/api/v1/financial/preview", headers=headers(context, "finance5"), json=financial_body(row["id"])).status_code == 200
    unit = context["client"].post("/api/v1/units", headers=headers(context), json={"name": "Fora do escopo"}).json()
    user_for(context, "scoped5", "hr", unit["id"])
    assert context["client"].get("/api/v1/scenarios/" + row["id"], headers=headers(context, "scoped5")).status_code == 404


def test_financial_idempotency_sensitivity_and_no_mutation(context):
    row = create_scenario(context)
    data = financial_body(row["id"], components=[{"name": "Transição", "kind": "fixed", "category": "training", "amount_cents": 10000, "recurrence": "once", "source": "Orçamento hipotético"}])
    auth = headers(context) | {"Idempotency-Key": "financial-1042"}
    first = context["client"].post("/api/v1/financial", headers=auth, json=data)
    assert first.status_code == 201, first.text
    second = context["client"].post("/api/v1/financial", headers=auth, json=data)
    assert second.json()["id"] == first.json()["id"]
    sensitivity = context["client"].post("/api/v1/financial/" + first.json()["id"] + "/sensitivity", headers=headers(context), json={"driver": "fixed_costs", "delta_bps": 1000})
    assert sensitivity.status_code == 200 and sensitivity.json()["annual_total_cents"]["delta"] == 1000
    assert sensitivity.json()["saved"] is False
    assert context["client"].get("/api/v1/financial/" + first.json()["id"], headers=headers(context)).json()["digest"] == first.json()["digest"]


def test_financial_comparison_rejects_other_period_and_invalid_parameters(context):
    first = create_scenario(context)
    second = create_scenario(context, key="outro-mes", reference_month="2026-12-01")
    a, b = run_financial(context, first["id"]), run_financial(context, second["id"])
    assert context["client"].post("/api/v1/financial/compare", headers=headers(context), json={"left_id": a["id"], "right_id": b["id"]}).status_code == 422
    bad = financial_body(first["id"], components=[{"name": "Inválida", "category": "night", "kind": "hours", "monthly_divisor_minutes": 0, "source": "Divisor inválido"}])
    assert context["client"].post("/api/v1/financial/preview", headers=headers(context), json=bad).status_code == 422
    omitted = financial_body(first["id"], components=[{"name": "Sem divisor", "category": "night", "kind": "hours", "hourly_base_salary_cents": 10000, "source": "Divisor não informado"}])
    assert context["client"].post("/api/v1/financial/preview", headers=headers(context), json=omitted).status_code == 422
    duplicated = financial_body(first["id"], components=[{"name": "Taxa", "kind": "percent", "category": "charge", "source": "Taxa hipotética"}], exclusions=[{"category": "charge", "source": "Teste duplicação", "justification": "Exclusão contraditória"}])
    assert context["client"].post("/api/v1/financial/preview", headers=headers(context), json=duplicated).status_code == 422


def test_restore_demo_removes_simulations(context):
    from app.models.entities import Organization
    from app.services.demo import load_demo
    from app.services.seed import restore_demo, seed_demo
    row = create_scenario(context)
    run_financial(context, row["id"])
    with context["factory"].begin() as session:
        org = session.get(Organization, context["org"])
        restore_demo(session, org, "Hospital Horizonte", "test")
        seed_demo(session, load_demo())
        assert session.scalar(select(FinancialRun.id)) is None
        assert session.scalar(select(ScenarioVersion.id)) is None


def test_calendar_cross_month_absence_and_destination_department(context):
    from datetime import UTC, datetime
    from app.models.entities import CalendarShift
    base = scenario_body(context)
    dept = context["client"].post("/api/v1/departments", headers=headers(context), json={"name": "Destino temporário", "unit_id": base["unit_id"], "group": "Operações"}).json()
    with context["factory"].begin() as session:
        session.add(CalendarShift(organization_id=context["org"], employee_id=demo_id("hh-0001"), unit_id=base["unit_id"], department_id=dept["id"],
            start_at=datetime.fromisoformat("2026-11-30T22:00:00-03:00").astimezone(UTC), end_at=datetime.fromisoformat("2026-12-01T06:00:00-03:00").astimezone(UTC), breaks=[], evaluation={}))
    absence = context["client"].post("/api/v1/employees/" + demo_id("hh-0001") + "/availability", headers=headers(context), json={"start_at": "2026-11-30T23:00:00-03:00", "end_at": "2026-12-01T00:00:00-03:00", "type": "unavailable"})
    assert absence.status_code == 201
    result = create_scenario(context, department_id=None, eligibility="hypothesis", demands=[{"name": "Plantão no destino", "department_id": dept["id"], "start_time": "22:00", "duration_minutes": 480, "weekdays": [0], "required_staff": 1, "source": "Demanda sintética no destino"}])
    assert result["capacity"]["raw_available_minutes"] == 60
    assert result["capacity"]["demands"][0]["eligible_upper_bound_minutes"] == 60


def test_weekly_budget_is_exact_over_four_weeks(context):
    pattern = context["client"].post("/api/v1/work-patterns", headers=headers(context), json={"name": "Todos os dias hipótese", "description": "Teste de orçamento, sem escala válida", "configuration": {"cycle": ["work"], "shift_minutes": 480}}).json()
    row = create_scenario(context, reference_month="2027-02-01", mode="cycle", work_pattern_id=pattern["id"], cycle_anchor="2027-02-01", target_weekly_minutes=2400, eligibility="hypothesis")
    evidence = context["client"].get("/api/v1/scenarios/" + row["id"] + "/evidence", headers=headers(context)).json()
    person = next(p for p in evidence["population"] if p["employee_id"] == demo_id("hh-0001"))
    assert "eligible_segments" in person and "salary_cents" not in str(evidence)
    with context["factory"]() as session:
        contract = session.scalar(select(Contract).where(Contract.employee_id == demo_id("hh-0001")))
        assert person["contract_budget_floor_minutes"] == min(contract.weekly_minutes, 2400) * 4


def test_demo_availability_seed_utc_and_repair_is_conservative(context):
    from datetime import UTC, datetime
    import pytest
    from app.api.dependencies import aware
    from app.models.entities import AvailabilityRule, Organization
    from app.services.demo import load_demo
    from app.services.demo_time_repair import repair_demo_times
    data = load_demo()
    source = data["availability_rules"][0]
    with context["factory"].begin() as session:
        org = session.get(Organization, context["org"])
        row = session.get(AvailabilityRule, demo_id(source["id"]))
        assert aware(row.start_at) == datetime.fromisoformat(source["start"]).astimezone(UTC)
        if context["backend"] == "sqlite":
            row.start_at = datetime.fromisoformat(source["start"]).replace(tzinfo=UTC)
            row.end_at = datetime.fromisoformat(source["end"]).replace(tzinfo=UTC)
            session.flush()
        result = repair_demo_times(session, org, data, "test")
        assert result["repaired"] == (1 if context["backend"] == "sqlite" else 0)
        assert repair_demo_times(session, org, data, "test")["repaired"] == 0
        row.reason = "Alteração manual que não deve ser reescrita"
        result = repair_demo_times(session, org, data, "test")
        assert result["not_matched"] == (1 if context["backend"] == "sqlite" else 0)
        assert row.reason.startswith("Alteração manual")
        with pytest.raises(ValueError):
            repair_demo_times(session, org, data, "production")
