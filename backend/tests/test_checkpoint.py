import copy

import pytest

from fastapi.testclient import TestClient

from app.main import app
from app.services.demo import load_demo, summarize_demo
from scripts.generate_demo import build_dataset, validate_dataset

client = TestClient(app)


def test_fixture_has_350_unique_people_and_all_sectors():
    data = load_demo()
    validate_dataset(data)
    assert len(data["employees"]) == 350
    assert len({e["id"] for e in data["employees"]}) == 350
    assert len(data["departments"]) == 19
    assert all(e["synthetic"] for e in data["employees"])


def test_generator_is_reproducible_and_committed_fixture_is_current():
    assert build_dataset() == build_dataset()
    assert build_dataset() == load_demo()


def test_summary_changes_with_source_data_instead_of_fixed_frontend_counts():
    data = copy.deepcopy(load_demo())
    data["employees"].pop()
    summary = summarize_demo(data)
    assert summary.employee_count == 349
    assert sum(d.employee_count for d in summary.departments) == 349


def test_fixture_role_and_skill_links_are_consistent():
    data = load_demo()
    roles = {r["id"]: r for r in data["job_roles"]}
    for employee in data["employees"]:
        role = roles[employee["job_role_id"]]
        assert set(role["required_skill_ids"]) <= set(employee["skill_ids"])
        assert employee["department_id"] in role["department_ids"]
        assert employee["legal_status"] == "pending_review"


def test_health_and_summary_api_contract():
    assert client.get("/api/v1/health").json()["version"] == "1.0"
    response = client.get("/api/v1/demo/summary")
    assert response.status_code == 200
    payload = response.json()
    assert payload["employee_count"] == 350
    assert payload["synthetic"] is True
    assert {r["id"] for r in payload["regimes"]} >= {"5x2", "4x3", "12x36", "custom"}


def test_missing_fixture_returns_safe_actionable_error(monkeypatch):
    def fail():
        raise FileNotFoundError("private/server/path")
    monkeypatch.setattr("app.api.routes.load_demo", fail)
    response = client.get("/api/v1/demo/summary")
    assert response.status_code == 503
    assert response.json()["code"] == "DEMO_UNAVAILABLE"
    assert "private" not in response.text


def test_cors_does_not_allow_arbitrary_origins():
    response = client.get("/api/v1/demo/summary", headers={"Origin": "https://untrusted.example"})
    assert "access-control-allow-origin" not in response.headers
    response = client.get("/api/v1/health", headers={"Origin": "http://127.0.0.1:5187"})
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5187"


def test_openapi_identifies_chronos_1_0():
    schema = client.get("/openapi.json").json()
    assert schema["info"]["version"] == "1.0"
    assert "Chronos 1.0" in schema["info"]["title"]


def test_people_not_exposed_without_database_or_authentication():
    assert client.get("/api/v1/employees").status_code in {401, 503}
    assert "employees" not in client.get("/api/v1/demo/summary").json()


def test_fixture_validation_rejects_cross_organization_records():
    data = copy.deepcopy(load_demo())
    data["employees"][0]["organization_id"] = "other-company"
    with pytest.raises(AssertionError, match="Organização inconsistente"):
        validate_dataset(data)


def test_fixture_validation_rejects_missing_qualification():
    data = copy.deepcopy(load_demo())
    data["employee_qualifications"].pop(0)
    with pytest.raises(AssertionError):
        validate_dataset(data)


def test_fixture_validation_rejects_someone_elses_contract():
    data = copy.deepcopy(load_demo())
    data["employees"][0]["contract_id"] = data["employees"][1]["contract_id"]
    with pytest.raises(AssertionError):
        validate_dataset(data)
