"""Executable acceptance checks against a disposable installation and real HTTP."""
import json
import os
from pathlib import Path
import secrets
import sqlite3
import subprocess
import sys
import time


def run(url, folder, bundle, factory):
    import httpx
    from desktop.runtime import create_administrator, prepare
    from desktop.window import ControlWindow
    from app.services.seed import demo_id
    from app.services.optimization_worker import solver_environment
    from app.models.entities import Employee

    window = ControlWindow(url, folder, bundle, factory, hidden=True)
    window.root.update_idletasks(); window.root.update(); window.root.destroy()
    assert (bundle / "help/chronos-manual.html").is_file() or (bundle.parent / "portfolio/chronos-manual.html").is_file()
    with httpx.Client(base_url=url, headers={"Origin": url}, timeout=30) as client:
        for path in ("/login", "/calendario"):
            response = client.get(path)
            assert response.status_code == 200 and "chronos-mark.svg" in response.text
        assert client.get("/api/v1/unknown-route").status_code == 404
        assert client.get("/assets/missing-file.js").status_code == 404
        assert client.get("/api/v1/health/ready").json()["status"] == "ready"
        assert client.get("/api/v1/employees").status_code == 401
        def login(username, password):
            csrf = client.get("/api/v1/session/csrf").json()["csrf_token"]
            response = client.post("/api/v1/session/login", headers={"X-CSRF-Token": csrf},
                json={"organization": "horizonte", "username": username, "password": password})
            assert response.status_code == 200, response.text
            return response.json()
        demo = login("demo", "ChronosDemo@2026")
        headers = {"Authorization": "Bearer " + demo["access_token"]}
        overview = client.get("/api/v1/analytics/overview", headers=headers).json()
        assert overview["employee_count"] == 350 and overview["department_count"] == 19
        assert client.get("/api/v1/employees", headers=headers).status_code == 403
        assert client.post("/api/v1/users", headers=headers, json={}).status_code == 403
        assert client.post("/api/v1/session/logout", headers={"X-CSRF-Token": demo["csrf_token"]}).status_code == 204
        password = secrets.token_urlsafe(24)
        create_administrator(factory, "desktop-test", password)
        account = login("desktop-test", password)
        headers = {"Authorization": "Bearer " + account["access_token"]}
        with factory() as session:
            person = session.get(Employee, demo_id("hh-0001"))
            unit, department = person.unit_id, person.department_id
        body = {"unit_id": unit, "department_id": department, "key": "desktop-probe", "name": "Teste isolado de desktop",
            "reference_month": "2026-11-01", "source": "Hipótese exclusiva de autoteste",
            "demands": [{"name": "Cobertura sintética", "department_id": department, "start_time": "08:00", "duration_minutes": 480,
                "weekdays": list(range(7)), "required_staff": 1, "source": "Teste sintético sem valor normativo"}]}
        response = client.post("/api/v1/scenarios", headers=headers, json=body)
        assert response.status_code == 201, response.text
        probe = json.loads((bundle / "desktop/solver-probe.json").read_text(encoding="utf-8"))
        options = probe["options"] | {"scenario_id": response.json()["id"], "eligibility": "hypothesis", "mode": "diagnostic", "cycle_anchors": {}, "activity_job_role_ids": {}}
        response = client.post("/api/v1/optimization", headers=headers | {"Idempotency-Key": "desktop-acceptance-2026-11-01"}, json=options)
        assert response.status_code == 202, response.text
        ident = response.json()["id"]
        deadline = time.monotonic() + 75
        while True:
            result = client.get("/api/v1/optimization/" + ident, headers=headers).json()
            if result["state"] not in ("queued", "running"):
                break
            assert time.monotonic() < deadline, result
            time.sleep(.5)
        assert result["state"] == "succeeded", result
        assert client.post("/api/v1/session/logout", headers={"X-CSRF-Token": account["csrf_token"]}).status_code == 204
    source, target = folder / "probe-input.json", folder / "probe-output.json"
    source.write_text(json.dumps(probe), encoding="utf-8")
    command = [sys.executable] + ([] if getattr(sys, "frozen", False) else [str(bundle / "desktop/launcher.py")])
    command += ["--chronos-solver", str(source), str(target)]
    environment = solver_environment()
    for key in ("_PYI_APPLICATION_HOME_DIR", "_PYI_ARCHIVE_FILE", "_PYI_PARENT_PROCESS_LEVEL"):
        if key in os.environ:
            environment[key] = os.environ[key]
    subprocess.run(command, env=environment, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        timeout=60, check=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    result = json.loads(target.read_text(encoding="utf-8"))["result"]
    assert result["solver_status"] == "OPTIMAL" and result["verification"]["valid"]
    assert result["verification"]["covered_staff_minutes"] == 1440
    prepare(folder, url)
    with sqlite3.connect(folder / "chronos-demo.sqlite3") as connection:
        assert connection.execute("pragma integrity_check").fetchone()[0] == "ok"
        assert connection.execute("pragma foreign_key_check").fetchall() == []
        assert connection.execute("select count(*) from employees").fetchone()[0] == 350
        assert connection.execute("select count(*) from users").fetchone()[0] == 2
    (folder / "self-test.json").write_text(json.dumps({"product": "Chronos 1.0", "frozen": bool(getattr(sys, "frozen", False)),
        "frontend_spa": True, "csrf_login_logout": True, "demo_read_only": True, "administrator_created": True,
        "optimization_queue": "succeeded", "ortools_probe": "OPTIMAL", "seed_idempotent": True, "database_integrity": "ok",
        "tk_initialized": True, "n8n": False, "scheduler": False}, indent=2), encoding="utf-8")
