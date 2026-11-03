import copy
from datetime import UTC, datetime, timedelta
import io
import json
import os
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.autogenerate import compare_metadata
from fastapi.testclient import TestClient
import jwt
import pytest
from sqlalchemy import delete, func, inspect, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.engine import make_url

from app.core.config import PROJECT_ROOT, Settings
from app.core.database import build_engine, session_factory
from app.core.security import hash_password
from app.main import create_app
from app.models.entities import (AuditLog, AvailabilityRule, Base, Contract, Department, Employee,
    EmployeeQualification, Organization, RefreshSession, Role, Unit, User, UserRole)
from app.services.demo import load_demo
from app.services.seed import create_user, demo_id, init_rbac, restore_demo, seed_demo

PASSWORD = "test-only-password-1042"
SECRET = "test-only-secret-chronos-1042-very-long"
PG_URL = os.getenv("CHRONOS_TEST_POSTGRES_URL")
BACKENDS = ["sqlite"] + (["postgresql"] if PG_URL else [])


def migrate(engine, target="head", down=False):
    config = Config(str(PROJECT_ROOT / "backend/alembic.ini"))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        (command.downgrade if down else command.upgrade)(config, target)


@pytest.fixture(params=BACKENDS)
def context(request, tmp_path):
    admin_engine = None
    schema = None
    if request.param == "postgresql":
        url = make_url(PG_URL)
        if not (url.database or "").endswith("_test"):
            pytest.fail("CHRONOS_TEST_POSTGRES_URL deve apontar para banco exclusivo terminado em _test")
        from sqlalchemy import create_engine
        admin_engine = create_engine(url)
        schema = "chronos_test_" + uuid4().hex
        with admin_engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        url = url.update_query_dict({"options": f"-csearch_path={schema}"}).render_as_string(hide_password=False)
    else:
        url = "sqlite+pysqlite:///" + (tmp_path / "chronos-test.sqlite3").as_posix()
    settings = Settings(_env_file=None, database_url=url, allow_sqlite=True, jwt_secret=SECRET,
                        environment="test", login_limit=100)
    app = create_app(settings)
    engine = app.state.engine
    migrate(engine)
    factory = app.state.session_factory
    with factory.begin() as session:
        init_rbac(session)
        org, _ = seed_demo(session, load_demo())
        user = create_user(session, org, "admin", PASSWORD)
        user_id = user.id
    client = TestClient(app)
    yield {"app": app, "engine": engine, "factory": factory, "client": client, "settings": settings,
           "org": demo_id("organization"), "user": user_id, "backend": request.param}
    client.close()
    engine.dispose()
    if admin_engine:
        with admin_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin_engine.dispose()


def login(ctx, username="admin"):
    result = ctx["client"].post("/api/v1/auth/login", json={"organization": "horizonte", "username": username, "password": PASSWORD})
    assert result.status_code == 200, result.text
    return result.json()


def headers(ctx, username="admin"):
    return {"Authorization": "Bearer " + login(ctx, username)["access_token"]}


def user_for(ctx, username, role, unit=None):
    with ctx["factory"].begin() as session:
        return create_user(session, session.get(Organization, ctx["org"]), username, PASSWORD, role, unit).id


def test_migrations_match_model_and_reverse(context):
    engine = context["engine"]
    with engine.connect() as connection:
        assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []
    migrate(engine, "base", down=True)
    assert set(inspect(engine).get_table_names()) <= {"alembic_version"}
    migrate(engine)
    assert set(Base.metadata.tables) <= set(inspect(engine).get_table_names())


def test_persisted_seed_and_restart(context):
    assert context["client"].get("/api/v1/health/ready").status_code == 200
    with context["factory"].begin() as session:
        assert session.scalar(select(func.count()).select_from(Employee)) == 350
        assert session.scalar(select(func.count()).select_from(Department)) == 19
        assert session.scalar(select(func.count()).select_from(EmployeeQualification)) == 350
        org, changed = seed_demo(session, load_demo())
        assert changed is False
    engine2 = build_engine(context["settings"])
    with session_factory(engine2)() as session:
        assert session.scalar(select(func.count()).select_from(Employee)) == 350
    engine2.dispose()


def test_password_hash_and_login_errors_are_safe(context):
    with context["factory"]() as session:
        encoded = session.get(User, context["user"]).password_hash
        assert encoded.startswith("$argon2id$") and PASSWORD not in encoded
    response = context["client"].post("/api/v1/auth/login", json={"organization": "horizonte", "username": "admin", "password": "wrong"})
    assert response.status_code == 401 and response.headers["www-authenticate"] == "Bearer"
    assert "wrong" not in response.text and encoded not in response.text
    tokens = login(context)
    response = context["client"].get("/api/v1/auth/me", headers={"Authorization": "Bearer " + tokens["access_token"]})
    assert response.status_code == 200 and response.json()["username"] == "admin"
    assert response.headers["cache-control"] == "no-store"


def test_jwt_rejects_tamper_expiration_wrong_audience_and_missing_claim(context):
    token = login(context)["access_token"]
    decoded = jwt.decode(token, SECRET, algorithms=["HS256"], audience="chronos-api", issuer="chronos")
    payloads = [dict(decoded, exp=1), dict(decoded, aud="other-service"), {k: v for k, v in decoded.items() if k != "exp"}, dict(decoded, type="refresh")]
    for payload in payloads:
        bad = jwt.encode(payload, SECRET, algorithm="HS256")
        assert context["client"].get("/api/v1/auth/me", headers={"Authorization": "Bearer " + bad}).status_code == 401
    tampered = jwt.encode(decoded, "different-secret-value-more-than-32-chars", algorithm="HS256")
    assert context["client"].get("/api/v1/auth/me", headers={"Authorization": "Bearer " + tampered}).status_code == 401


def test_refresh_rotation_replay_and_logout_invalidate_access(context):
    initial = login(context)
    renewed = context["client"].post("/api/v1/auth/refresh", json={"refresh_token": initial["refresh_token"]})
    assert renewed.status_code == 200
    token = renewed.json()
    assert token["refresh_token"] != initial["refresh_token"]
    with context["factory"]() as session:
        assert initial["refresh_token"] not in " ".join(session.scalars(select(RefreshSession.token_hash)))
    replay = context["client"].post("/api/v1/auth/refresh", json={"refresh_token": initial["refresh_token"]})
    assert replay.status_code == 401
    assert context["client"].get("/api/v1/auth/me", headers={"Authorization": "Bearer " + token["access_token"]}).status_code == 401
    fresh = login(context)
    assert context["client"].post("/api/v1/auth/logout", json={"refresh_token": fresh["refresh_token"]}).status_code == 204
    assert context["client"].get("/api/v1/auth/me", headers={"Authorization": "Bearer " + fresh["access_token"]}).status_code == 401


def test_rate_limit_survives_app_restart(context):
    context["app"].state.settings.login_limit = 2
    body = {"organization": "horizonte", "username": "absent", "password": "wrong"}
    for _ in range(2):
        assert context["client"].post("/api/v1/auth/login", json=body).status_code == 401
    app2 = create_app(context["settings"])
    with TestClient(app2) as client:
        assert client.post("/api/v1/auth/login", json=body).status_code == 429
    app2.state.engine.dispose()


def test_rbac_and_salary_minimization(context):
    user_for(context, "manager", "manager")
    user_for(context, "finance", "finance")
    user_for(context, "demo", "demo")
    manager = headers(context, "manager")
    response = context["client"].get("/api/v1/employees", headers=manager)
    assert response.status_code == 200 and response.json()["total"] == 350
    employee = response.json()["items"][0]
    assert "salary" not in response.text and "base_salary_cents" not in response.text
    assert context["client"].get(f"/api/v1/employees/{employee['id']}/contracts", headers=manager).status_code == 403
    finance = headers(context, "finance")
    assert context["client"].get("/api/v1/employees", headers=finance).status_code == 403
    assert context["client"].get(f"/api/v1/employees/{employee['id']}/contracts", headers=finance).status_code == 200
    assert context["client"].get("/api/v1/employees", headers=headers(context, "demo")).status_code == 403
    assert context["client"].post("/api/v1/employees", headers=manager, json={}).status_code == 403


def test_unit_scoping_does_not_widen_other_permissions(context):
    unit = demo_id("horizonte-main")
    user_id = user_for(context, "scoped", "manager", unit)
    with context["factory"].begin() as session:
        other = Unit(organization_id=context["org"], name="Other")
        session.add(other)
        session.flush()
        department = Department(organization_id=context["org"], unit_id=other.id, name="Office", group="Admin")
        session.add(department)
        session.flush()
        employee = Employee(organization_id=context["org"], unit_id=other.id, department_id=department.id,
            job_role_id=demo_id("director"), name="Hidden", registration="HIDDEN")
        session.add(employee)
        session.flush()
        hidden = employee.id
        role = session.scalar(select(Role).where(Role.name == "analyst"))
        session.add(UserRole(organization_id=context["org"], user_id=user_id, role_id=role.id))
    token = headers(context, "scoped")
    assert context["client"].get("/api/v1/units", headers=token).json()["total"] == 2  # analyst has org:read globally
    assert context["client"].get("/api/v1/employees", headers=token).json()["total"] == 350
    assert context["client"].get(f"/api/v1/employees/{hidden}", headers=token).status_code == 404


def test_cross_tenant_reads_writes_and_database_foreign_keys(context):
    admin = headers(context)
    with context["factory"].begin() as session:
        other = Organization(slug="other", name="Other company", segment="services")
        session.add(other)
        session.flush()
        unit = Unit(organization_id=other.id, name="Private unit")
        session.add(unit)
        session.flush()
        org_id, unit_id = other.id, unit.id
    assert context["client"].get(f"/api/v1/organizations/{org_id}", headers=admin).status_code == 404
    response = context["client"].post("/api/v1/departments", headers=admin, json={"unit_id": unit_id, "name": "Bad", "group": "Admin"})
    assert response.status_code == 422
    with context["factory"]() as session:
        session.add(Department(organization_id=context["org"], unit_id=unit_id, name="Invalid", group="Admin"))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


def test_create_update_conflict_and_audit_are_transactional(context):
    admin = headers(context)
    body = {"unit_id": demo_id("horizonte-main"), "department_id": demo_id("management"), "job_role_id": demo_id("director"),
            "name": "Pessoa de teste", "registration": "NEW001"}
    created = context["client"].post("/api/v1/employees", headers=admin, json=body)
    assert created.status_code == 201, created.text
    row = created.json()
    assert context["client"].post("/api/v1/employees", headers=admin, json=body).status_code == 409
    changed = context["client"].patch(f"/api/v1/employees/{row['id']}", headers=admin, json={"revision": 1, "name": "Pessoa alterada"})
    assert changed.status_code == 200 and changed.json()["revision"] == 2
    assert context["client"].patch(f"/api/v1/employees/{row['id']}", headers=admin, json={"revision": 1, "status": "inactive"}).status_code == 409
    with context["factory"]() as session:
        assert session.scalar(select(func.count()).select_from(Employee)) == 351
        logs = session.scalars(select(AuditLog).where(AuditLog.entity_id == row["id"])).all()
        assert len(logs) == 2 and {log.action for log in logs} == {"create", "update"}
        assert changed.headers["x-correlation-id"] in {log.correlation_id for log in logs}


def test_pagination_filters_and_sort_allowlist(context):
    admin = headers(context)
    response = context["client"].get("/api/v1/employees?page_number=2&page_size=7&sort=registration&descending=true", headers=admin)
    assert response.status_code == 200 and len(response.json()["items"]) == 7
    assert response.json()["total"] == 350
    assert context["client"].get("/api/v1/employees?department_id=" + demo_id("management"), headers=admin).json()["total"] == 8
    assert context["client"].get("/api/v1/employees?search=HH0001", headers=admin).json()["total"] == 1
    assert context["client"].get("/api/v1/employees?sort=password_hash", headers=admin).status_code == 422
    assert context["client"].get("/api/v1/employees?page_size=10000", headers=admin).status_code == 422


def test_invalid_inputs_never_echo_password_or_create_partial_records(context):
    admin = headers(context)
    secret = "sensitive-password-example"
    response = context["client"].post("/api/v1/users", headers=admin, json={"username": "bad username", "password": secret, "role": "admin", "organization_id": "other"})
    assert response.status_code == 422 and secret not in response.text
    assert context["client"].get("/api/v1/users", headers=admin).json()["total"] == 1
    assert context["client"].post("/api/v1/units", headers=admin, json={"name": "Unit", "timezone": "Invalid/Zone"}).status_code == 422


def test_contracts_qualifications_and_availability_validation(context):
    admin = headers(context)
    person = demo_id("hh-0001")
    url = f"/api/v1/employees/{person}"
    overlapping = {"work_pattern_id": demo_id("5x2"), "weekly_minutes": 2400, "base_salary_cents": 300000,
                   "employment_type": "simulated", "valid_from": "2026-01-02", "assumption_source": "Teste"}
    assert context["client"].post(url + "/contracts", headers=admin, json=overlapping).status_code == 409
    bad_qualification = {"qualification_id": demo_id("qualification-director"), "valid_from": "2027-01-01", "valid_until": "2026-01-01"}
    assert context["client"].post(url + "/qualifications", headers=admin, json=bad_qualification).status_code == 422
    absence = {"start_at": "2026-11-01T08:00:00-03:00", "end_at": "2026-11-01T10:00:00-03:00"}
    assert context["client"].post(url + "/availability", headers=admin, json=absence).status_code == 201
    assert context["client"].get(url + "/availability", headers=admin).status_code == 200
    absence["start_at"] = "2026-11-01T08:00:00"
    assert context["client"].post(url + "/availability", headers=admin, json=absence).status_code == 422


def test_seed_failure_rolls_back_and_restore_is_demo_only(context):
    with context["factory"].begin() as session:
        org = session.get(Organization, context["org"])
        for environment, confirmation in [("production", org.name), ("test", "wrong")]:
            with pytest.raises(ValueError):
                restore_demo(session, org, confirmation, environment)
    with context["factory"]() as session:
        org = session.get(Organization, context["org"])
        restore_demo(session, org, org.name, "test")
        broken = copy.deepcopy(load_demo())
        broken["employees"][0]["department_id"] = "unknown-department"
        with pytest.raises(IntegrityError):
            seed_demo(session, broken)
        session.rollback()
        assert session.scalar(select(func.count()).select_from(Employee)) == 350
    with context["factory"].begin() as session:
        org = session.get(Organization, context["org"])
        session.execute(update(Employee).where(Employee.id == demo_id("hh-0001")).values(name="Edited"))
        restore_demo(session, org, org.name, "test")
        seed_demo(session, load_demo())
    with context["factory"]() as session:
        assert session.get(Employee, demo_id("hh-0001")).name == "Pessoa Sintética 001"
        assert session.get(User, context["user"]) is not None


def test_expired_refresh_and_disabled_user(context):
    tokens = login(context)
    with context["factory"].begin() as session:
        session.execute(update(RefreshSession).values(expires_at=datetime.now(UTC) - timedelta(days=1)))
    assert context["client"].post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401
    tokens = login(context)
    with context["factory"].begin() as session:
        session.get(User, context["user"]).active = False
    assert context["client"].get("/api/v1/auth/me", headers={"Authorization": "Bearer " + tokens["access_token"]}).status_code == 401


def test_postgres_migrations_generate_offline_sql():
    output = io.StringIO()
    config = Config(str(PROJECT_ROOT / "backend/alembic.ini"), output_buffer=output)
    config.attributes["database_url"] = "postgresql+psycopg://chronos@localhost/chronos_test"
    command.upgrade(config, "head", sql=True)
    sql = output.getvalue()
    assert "CREATE TABLE employees" in sql and "FOREIGN KEY(organization_id, unit_id, department_id)" in sql
    assert "TIMESTAMP WITH TIME ZONE" in sql


def test_idempotency_replay_and_conflicting_payload(context):
    auth = {**headers(context), "Idempotency-Key": "create-unit-test-1042"}
    body = {"name": "Nova unidade"}
    first = context["client"].post("/api/v1/units", headers=auth, json=body)
    again = context["client"].post("/api/v1/units", headers=auth, json=body)
    assert first.status_code == again.status_code == 201
    assert first.json()["id"] == again.json()["id"]
    assert again.headers["idempotency-replayed"] == "true"
    assert context["client"].get("/api/v1/units", headers=auth).json()["total"] == 2
    assert context["client"].post("/api/v1/units", headers=auth, json={"name": "Outro conteúdo"}).status_code == 409


def test_admin_creates_scoped_user_without_exposing_password(context):
    admin = {**headers(context), "Idempotency-Key": "create-user-test-1042"}
    payload = {"username": "newmanager", "password": PASSWORD, "role": "manager", "unit_id": demo_id("horizonte-main")}
    response = context["client"].post("/api/v1/users", headers=admin, json=payload)
    assert response.status_code == 201, response.text
    assert PASSWORD not in response.text and "password_hash" not in response.text
    assert context["client"].post("/api/v1/users", headers=admin, json=payload).json()["id"] == response.json()["id"]
    payload["password"] = PASSWORD + "-changed"
    assert context["client"].post("/api/v1/users", headers=admin, json=payload).status_code == 409
    scoped = headers(context, "newmanager")
    assert context["client"].get("/api/v1/employees", headers=scoped).json()["total"] == 350
    assert context["client"].post("/api/v1/users", headers=scoped, json=payload).status_code == 403


def test_sqlite_is_opt_in_and_runtime_location_is_guarded(tmp_path):
    with pytest.raises(ValueError, match="explicitamente|exige"):
        build_engine(Settings(_env_file=None, database_url="sqlite+pysqlite:///" + (tmp_path / "db.sqlite3").as_posix()))
    with pytest.raises(ValueError, match="OneDrive"):
        build_engine(Settings(_env_file=None, allow_sqlite=True, database_url="sqlite+pysqlite:///" + (PROJECT_ROOT / "bad.sqlite3").as_posix()))


def test_settings_validation_and_unknown_routes_do_not_expose_input():
    value = "private-short-secret"
    with pytest.raises(ValueError) as error:
        Settings(_env_file=None, jwt_secret=value)
    assert value not in str(error.value)
    app = create_app(Settings(_env_file=None))
    with TestClient(app) as client:
        response = client.get("/api/v1/unknown-resource")
        assert response.status_code == 404
        assert response.json()["code"] == "HTTP_ERROR"
        assert response.json()["correlation_id"] == response.headers["x-correlation-id"]


def test_new_contract_replays_without_creating_overlap(context):
    admin = headers(context)
    body = {"unit_id": demo_id("horizonte-main"), "department_id": demo_id("management"), "job_role_id": demo_id("director"),
            "name": "Pessoa de teste", "registration": "CONTRACT001"}
    person = context["client"].post("/api/v1/employees", headers=admin, json=body).json()["id"]
    auth = {**admin, "Idempotency-Key": "create-contract-test-1042"}
    contract = {"work_pattern_id": demo_id("5x2"), "weekly_minutes": 2400, "base_salary_cents": 300000,
                "employment_type": "simulated", "valid_from": "2026-01-01", "assumption_source": "Teste sintético"}
    first = context["client"].post(f"/api/v1/employees/{person}/contracts", headers=auth, json=contract)
    second = context["client"].post(f"/api/v1/employees/{person}/contracts", headers=auth, json=contract)
    assert first.status_code == second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    assert first.json()["validation_status"] == "pending_review"


@pytest.mark.skipif(not PG_URL, reason="PostgreSQL real não disponível; configure CHRONOS_TEST_POSTGRES_URL em banco *_test")
def test_postgresql_profile_was_executed():
    assert "postgresql" in BACKENDS
