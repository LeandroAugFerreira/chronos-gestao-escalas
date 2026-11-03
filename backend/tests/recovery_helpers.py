"""Native pg_dump/pg_restore against a fresh, uniquely named disposable DB."""
import os
from pathlib import Path
import shutil
import subprocess
from uuid import uuid4
from fastapi.testclient import TestClient
import psycopg
from psycopg import sql
import pytest
from sqlalchemy import func, select, text
from app.core.config import Settings
from app.main import create_app
from app.models import entities as m
from app.services.recovery import quiesce_restored_copy
from test_phase2 import headers
from test_phase6 import enqueue
from test_phase7 import configure, integration_key


def verify_postgres_recovery(ctx, tmp_path):
    directory = os.getenv("CHRONOS_PG_BIN")
    dump = str(Path(directory)/"pg_dump.exe") if directory else shutil.which("pg_dump")
    restore = str(Path(directory)/"pg_restore.exe") if directory else shutil.which("pg_restore")
    if not dump or not restore:
        pytest.skip("Ferramentas nativas PostgreSQL não configuradas; use CHRONOS_PG_BIN")
    run,_ = enqueue(ctx); auth = headers(ctx); configure(ctx,"A04"); integration_key(ctx)
    url = ctx["engine"].url
    assert url.database.endswith("_test")
    with ctx["factory"]() as session:
        schema = session.scalar(text("SELECT current_schema()"))
    assert schema.startswith("chronos_test_")
    fresh = "chronos_recovery_"+uuid4().hex[:12]+"_test"
    credentials = {"host":url.host,"port":url.port or 5432,"user":url.username,"password":url.password,"dbname":url.database}
    env = {**os.environ,"PGHOST":url.host,"PGPORT":str(url.port or 5432),"PGUSER":url.username,"PGPASSWORD":url.password,"PGDATABASE":url.database}
    archive = tmp_path/"recovery.dump"
    subprocess.run([dump,"--format=custom","--no-owner","--no-acl","--schema="+schema,"--file="+str(archive)],env=env,check=True,capture_output=True,timeout=60)
    created, app = False, None
    try:
        with psycopg.connect(**credentials,autocommit=True) as admin:
            admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(fresh)))
        created = True
        subprocess.run([restore,"--no-owner","--no-acl","--single-transaction","--exit-on-error","--dbname="+fresh,str(archive)],env=env|{"PGDATABASE":fresh},check=True,capture_output=True,timeout=60)
        settings = Settings(_env_file=None,environment="test",database_url=url.set(database=fresh).render_as_string(hide_password=False),jwt_secret=ctx["settings"].jwt_secret)
        app = create_app(settings)
        with app.state.session_factory.begin() as session:
            assert session.scalar(select(func.count()).select_from(m.Employee)) == 350
            assert session.scalar(select(func.count()).select_from(m.Department)) == 19
            before = session.get(m.ScenarioVersion,run["scenario_id"]).digest
            safety = quiesce_restored_copy(session)
            assert safety["sessions_revoked"] > 0 and safety["credentials_disabled"] == 1
            assert safety["optimization_runs_cancelled"] == 1 and safety["automations_disabled"] == 1
        with TestClient(app) as client:
            assert client.get("/api/v1/auth/me",headers=auth).status_code == 401
            assert client.get("/api/v1/health/ready").status_code == 200
        with app.state.session_factory() as session:
            assert session.get(m.OptimizationRun,run["id"]).state == "cancelled"
            assert session.get(m.ScenarioVersion,run["scenario_id"]).digest == before
        with ctx["factory"]() as session:
            assert session.get(m.OptimizationRun,run["id"]).state == "queued"
            assert session.scalar(select(func.count()).select_from(m.IntegrationCredential).where(m.IntegrationCredential.enabled.is_(True))) == 1
        assert ctx["client"].get("/api/v1/auth/me",headers=auth).status_code == 200
    finally:
        if app: app.state.engine.dispose()
        if created:
            assert fresh.startswith("chronos_recovery_") and fresh.endswith("_test")
            with psycopg.connect(**credentials,autocommit=True) as admin:
                admin.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=%s AND pid<>pg_backend_pid()",(fresh,))
                admin.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(fresh)))
