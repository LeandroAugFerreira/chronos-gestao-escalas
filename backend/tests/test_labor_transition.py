from datetime import date
from decimal import Decimal
import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient
from app.main import create_app
from app.core.config import Settings
from app.api.dependencies import get_db
from app.schemas.labor_transition import TransitionInput
from app.services.labor_transition import compare, metadata
from app.api.labor_transition import references, comparison


def result(**values):
    return compare(TransitionInput(reference_date=values.pop("reference_date", "2026-12-16"), **values))


@pytest.mark.parametrize("day,minutes,rests,divisor", [
    ("2026-11-25", 2640, 1, "220"), ("2026-12-15", 2640, 1, "220"),
    ("2026-12-16", 2520, 2, "210"), ("2027-12-15", 2520, 2, "210"),
    ("2027-12-16", 2400, 2, "200"), ("2028-01-01", 2400, 2, "200"),
])
def test_actual_effect_boundaries(day, minutes, rests, divisor):
    data = result(reference_date=day)
    assert data["effective_weekly_minutes"] == minutes
    assert data["phase"]["rest_days"] == rests
    assert data["monthly_divisor_hours"] == divisor
    assert data["monthly_salary_cents"] == 330000


@pytest.mark.parametrize("contract,divisor", [(1200, "100"), (1800, "150"), (2400, "200")])
def test_shorter_contract_never_reduced_proportionately(contract, divisor):
    for day in ("2026-12-16", "2027-12-16"):
        data = result(reference_date=day, contract_weekly_minutes=contract, planned_weekly_minutes=contract)
        assert data["effective_weekly_minutes"] == contract
        assert data["monthly_divisor_hours"] == divisor


def test_more_favorable_divisor_and_salary_preservation():
    data = result(more_favorable_divisor_hours=Decimal("180"), proposed_salary_cents=300000)
    assert data["monthly_divisor_hours"] == "180"
    assert data["monthly_salary_cents"] == 330000
    assert data["hourly_cents"] == 1833
    assert data["status"] == "adjustment_required"
    assert any(f["code"] == "SALARY_PRESERVATION" and f["status"] == "exceeds" for f in data["findings"])
    assert result(more_favorable_divisor_hours=Decimal("250"))["monthly_divisor_hours"] == "210"


def test_hour_value_changes_without_claiming_salary_raise_or_savings():
    first, last = result(), result(reference_date="2027-12-16")
    assert first["baseline_hourly_cents"] == 1500
    assert first["hourly_cents"] == 1571
    assert last["hourly_cents"] == 1650
    assert last["monthly_salary_cents"] == first["monthly_salary_cents"]
    assert last["hourly_change_percent"] == "10.00"


@pytest.mark.parametrize("day,collective,expected", [
    ("2026-12-16", "absent_at_cutoff", "within"),
    ("2027-12-15", "absent_at_cutoff", "within"),
    ("2027-12-16", "absent_at_cutoff", "exceeds"),
    ("2026-12-15", "absent_at_cutoff", "exceeds"),
    ("2026-12-16", "not_reviewed", "exceeds"),
    ("2026-12-16", "present", "exceeds"),
])
def test_interim_daily_exception_requires_date_and_explicit_assumption(day, collective, expected):
    data = result(reference_date=day, collective_status=collective, planned_daily_minutes=504, use_interim_daily_exception=True)
    assert next(f for f in data["findings"] if f["code"] == "DAILY_LIMIT")["status"] == expected
    assert any(f["code"] == "INTERIM_DAILY_EXCEPTION" and f["status"] == "review" for f in data["findings"])


def test_8h24_is_not_automatically_assumed():
    data = result(planned_daily_minutes=504)
    assert any(f["code"] == "DAILY_LIMIT" and f["status"] == "exceeds" for f in data["findings"])


def test_weekly_assumptions_must_fit_declared_daily_capacity_and_rest_days():
    data = result(planned_weekly_minutes=2520, planned_daily_minutes=480, rest_days_24h=2)
    assert data["status"] == "adjustment_required"
    assert any(f["code"] == "DECLARED_CAPACITY" for f in data["findings"])


@pytest.mark.parametrize("regime", ["12x36", "rotating", "custom"])
def test_special_regime_never_certified_by_ordinary_week_or_daily_limit(regime):
    data = result(regime=regime, planned_daily_minutes=720, planned_weekly_minutes=2880, rest_days_24h=1)
    assert data["status"] == "review_required"
    assert not any(f["code"] in {"DAILY_LIMIT", "WEEKLY_LIMIT", "WEEKLY_RESTS"} for f in data["findings"])
    assert any(f["code"] == "SPECIAL_REGIME" for f in data["findings"])


def test_two_distinct_24h_rests_and_collective_compensation_need_context():
    assert result(rest_days_24h=1)["status"] == "adjustment_required"
    data = result(rest_days_24h=1, collective_rest_compensation=True)
    assert data["status"] == "review_required"
    assert any(f["code"] == "REST_REVIEW" for f in data["findings"])


def test_snapshot_and_digest_include_source_profile_and_assumptions():
    a, b = result(), result()
    assert a == b
    assert len(a["digest"]) == 64
    assert result(monthly_salary_cents=330001)["digest"] != a["digest"]
    assert {s["id"] for s in a["sources"]} == {"ec141", "decree13173", "portaria2041", "stf8041"}
    assert any(f["code"] == "FUTURE_REFERENCE" for f in a["findings"])
    copy = metadata(); copy["phases"][0]["weekly_minutes"] = 1
    assert metadata()["phases"][0]["weekly_minutes"] == 2640


@pytest.mark.parametrize("values", [
    {"reference_date": "1999-12-31"}, {"reference_date": "2099-01-01"},
    {"monthly_salary_cents": -1}, {"rest_days_24h": 8},
    {"more_favorable_divisor_hours": "NaN"}, {"more_favorable_divisor_hours": 0},
    {"regime": "any_job_automatically_legal"}, {"extra": "forbidden"},
])
def test_invalid_or_unbounded_assumptions_rejected(values):
    with pytest.raises(ValidationError):
        TransitionInput(**({"reference_date": "2026-12-16"} | values))


def test_api_requires_authentication_and_validates_comparison():
    application = create_app(Settings(_env_file=None, jwt_secret="transition-test-secret-32-characters-or-more", environment="test"))
    application.dependency_overrides[get_db] = lambda: None
    with TestClient(application) as client:
        assert client.get("/api/v1/labor-transition").status_code == 401
        assert client.post("/api/v1/labor-transition/compare", json={"reference_date": "2026-12-16"}).status_code == 401
        application.dependency_overrides[references.__defaults__[0].dependency] = lambda: object()
        application.dependency_overrides[comparison.__defaults__[0].dependency] = lambda: object()
        assert client.get("/api/v1/labor-transition").json()["product_version"] == "2.0"
        response = client.post("/api/v1/labor-transition/compare", json={"reference_date": "2027-12-16"})
        assert response.status_code == 200
        assert response.json()["effective_weekly_minutes"] == 2400
        assert client.post("/api/v1/labor-transition/compare", json={"reference_date": "bad"}).status_code == 422
