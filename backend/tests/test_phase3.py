from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.models.entities import AuditLog, Contract, Department, Employee, RefreshSession, Unit
from app.services.seed import demo_id
from test_phase2 import context, headers, user_for

ORIGIN = "http://127.0.0.1:5187"
PASSWORD = "test-only-password-1042"


def csrf(client):
    response = client.get("/api/v1/session/csrf", headers={"Origin": ORIGIN})
    assert response.status_code == 200, response.text
    return {"Origin": ORIGIN, "X-CSRF-Token": response.json()["csrf_token"]}


def browser_login(client):
    return client.post("/api/v1/session/login", headers=csrf(client),
        json={"organization": "horizonte", "username": "admin", "password": PASSWORD})


def test_browser_session_cookie_flags_csrf_refresh_and_logout(context):
    client = context["client"]
    response = browser_login(client)
    assert response.status_code == 200, response.text
    assert "refresh_token" not in response.json()
    assert response.json()["user"]["username"] == "admin"
    cookies = response.headers.get_list("set-cookie")
    assert len(cookies) == 2
    assert all("HttpOnly" in cookie and "SameSite=strict" in cookie and "Path=/" in cookie for cookie in cookies)
    old_cookie = client.cookies.get("chronos-refresh")
    token = response.json()["access_token"]
    renewed = client.post("/api/v1/session/refresh", headers={"Origin": ORIGIN, "X-CSRF-Token": response.json()["csrf_token"]})
    assert renewed.status_code == 200, renewed.text
    assert client.cookies.get("chronos-refresh") != old_cookie
    assert "refresh_token" not in renewed.json()
    result = client.post("/api/v1/session/logout", headers=csrf(client))
    assert result.status_code == 204
    assert client.cookies.get("chronos-refresh") is None
    assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer " + token}).status_code == 401


def test_browser_rejects_missing_origin_csrf_and_cross_site_requests(context):
    client = context["client"]
    body = {"organization": "horizonte", "username": "admin", "password": PASSWORD}
    valid = csrf(client)
    for values in [{}, {"Origin": ORIGIN}, {**valid, "Origin": "https://untrusted.example"}, {**valid, "Sec-Fetch-Site": "cross-site"}, {**valid, "X-CSRF-Token": "invalid"}]:
        assert client.post("/api/v1/session/login", headers=values, json=body).status_code == 403
    assert client.get("/api/v1/session/csrf", headers={"Origin": "https://untrusted.example"}).status_code == 403


def test_csrf_is_bound_to_authenticated_family_and_login_replaces_old_session(context):
    client = context["client"]
    anonymous = csrf(client)
    first = browser_login(client)
    assert first.status_code == 200
    assert client.post("/api/v1/session/refresh", headers=anonymous).status_code == 403
    second = browser_login(client)
    assert second.status_code == 200
    assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer " + first.json()["access_token"]}).status_code == 401
    assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer " + second.json()["access_token"]}).status_code == 200


def test_secure_session_uses_host_cookie_prefix_and_invalid_refresh_clears_cookie(context):
    context["app"].state.settings.cookie_secure = True
    with TestClient(context["app"], base_url="https://testserver") as client:
        response = browser_login(client)
        assert response.status_code == 200
        assert all("Secure" in value and "__Host-chronos" in value for value in response.headers.get_list("set-cookie"))
        with context["factory"].begin() as session:
            from sqlalchemy import update
            session.execute(update(RefreshSession).values(expires_at=datetime.now(UTC) - timedelta(days=1)))
        response = client.post("/api/v1/session/refresh", headers=csrf(client))
        assert response.status_code == 401
        assert client.cookies.get("__Host-chronos-refresh") is None


def test_dashboard_uses_database_and_reconciles_changes(context):
    client = context["client"]
    auth = headers(context)
    first = client.get("/api/v1/analytics/overview", headers=auth)
    assert first.status_code == 200
    data = first.json()
    assert data["source"] == "database" and data["employee_count"] == 350
    assert data["active_count"] == 350 and data["department_count"] == 19
    assert sum(row["employee_count"] for row in data["departments"]) == 350
    assert sum(row["employee_count"] for row in data["regimes"]) == 350
    assert data["weekly_average_hours"] > 0
    body = {"revision": 1, "status": "inactive"}
    assert client.patch("/api/v1/employees/" + demo_id("hh-0001"), headers=auth, json=body).status_code == 200
    changed = client.get("/api/v1/analytics/overview", headers=auth).json()
    assert changed["employee_count"] == 350 and changed["active_count"] == 349 and changed["inactive_count"] == 1
    assert sum(row["employee_count"] for row in changed["regimes"]) == 349


def test_dashboard_and_transfer_respect_unit_scopes(context):
    client = context["client"]
    auth = headers(context)
    unit = client.post("/api/v1/units", headers=auth, json={"name": "Segunda unidade"}).json()
    department = client.post("/api/v1/departments", headers=auth, json={"unit_id": unit["id"], "name": "Novo setor", "group": "Serviços"}).json()
    user_for(context, "scopedhr", "hr", demo_id("horizonte-main"))
    scoped = headers(context, "scopedhr")
    assert client.get("/api/v1/analytics/overview?unit_id=" + unit["id"], headers=scoped).status_code == 404
    transfer = {"revision": 1, "unit_id": unit["id"], "department_id": department["id"], "job_role_id": demo_id("director")}
    person = demo_id("hh-0001")
    assert client.patch("/api/v1/employees/" + person, headers=scoped, json=transfer).status_code == 403
    assert client.patch("/api/v1/employees/" + person, headers=auth, json=transfer).status_code == 200
    assert client.get("/api/v1/analytics/overview", headers=scoped).json()["employee_count"] == 349
    assert client.get("/api/v1/analytics/overview?unit_id=" + unit["id"], headers=auth).json()["employee_count"] == 1
    assert client.patch("/api/v1/employees/" + person, headers=auth, json=transfer).status_code == 409


def test_unit_department_catalog_edits_require_current_revision(context):
    client = context["client"]
    auth = headers(context)
    unit = client.get("/api/v1/units", headers=auth).json()["items"][0]
    update = {"revision": unit["revision"], "name": "Unidade atualizada", "operation": "24x7", "timezone": unit["timezone"]}
    assert client.patch("/api/v1/units/" + unit["id"], headers=auth, json=update).status_code == 200
    assert client.patch("/api/v1/units/" + unit["id"], headers=auth, json=update).status_code == 409
    department = client.get("/api/v1/departments", headers=auth).json()["items"][0]
    assert client.patch("/api/v1/departments/" + department["id"], headers=auth, json={key: value for key, value in department.items() if key != "id"}).status_code == 200
    role = client.get("/api/v1/catalogs/job-roles", headers=auth).json()["items"][0]
    change = {"name": "Função atualizada", "revision": role["revision"]}
    assert client.patch("/api/v1/catalogs/job-roles/" + role["id"], headers=auth, json=change).status_code == 200
    assert client.patch("/api/v1/catalogs/job-roles/" + role["id"], headers=auth, json=change).status_code == 409
    user_for(context, "readonly", "manager")
    assert client.patch("/api/v1/units/" + unit["id"], headers=headers(context, "readonly"), json=update).status_code == 403


def test_transfer_cannot_associate_other_company_or_mismatched_department(context):
    client = context["client"]
    auth = headers(context)
    person = demo_id("hh-0001")
    assert client.patch("/api/v1/employees/" + person, headers=auth, json={"revision": 1, "unit_id": "missing"}).status_code == 422
    assert client.patch("/api/v1/employees/" + person, headers=auth, json={"revision": 1, "unit_id": "missing", "department_id": demo_id("icu")}).status_code == 422
    with context["factory"]() as session:
        assert session.get(Employee, person).unit_id == demo_id("horizonte-main")
