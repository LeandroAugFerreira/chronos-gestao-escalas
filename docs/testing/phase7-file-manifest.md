# Chronos 1.0 — Manifesto da Fase 7

Arquivos autorais adicionados/atualizados nesta etapa. Não inclui .env, chaves/credenciais privadas, bancos, venv, caches, binários, node_modules ou build. Prompt Mestre consolidado e fixture preservados.

- `README.md`, `CHANGELOG.md`, `release.json`, `.env.example`
- `backend/alembic/versions/009_automations.py`
- `backend/app/models/entities.py`, `backend/app/core/config.py`, `backend/app/core/security.py`
- `backend/app/api/dependencies.py`, `backend/app/api/routes.py`, `backend/app/api/automation.py`, `backend/app/main.py`
- `backend/app/schemas/automation.py`
- `backend/app/services/audit.py`, `backend/app/services/seed.py`
- `backend/app/services/automation_events.py`, `backend/app/services/automations.py`, `backend/app/services/automation_worker.py`
- `backend/scripts/automation_worker.py`, `backend/scripts/smoke_phase7.py`
- `backend/tests/test_phase7.py`
- `frontend/src/App.tsx`, `frontend/src/pages/automation.tsx`, `frontend/src/pages/optimization.tsx`, `frontend/src/pages/overview.tsx`
- `frontend/src/types/automation.ts`, `frontend/src/tests/automation.test.tsx`
- `scripts/start-automations.ps1`, `scripts/setup-n8n.ps1`, `scripts/start-n8n.ps1`
- `automation/n8n/generate_workflows.py`, `automation/n8n/README.md`
- `automation/n8n/A02-alerta-cobertura.json`, `automation/n8n/A03-escala-pendente.json`, `automation/n8n/A04-relatorio-programado.json`, `automation/n8n/A06-disponibilidade.json`
- `automation/n8n/package.json`, `automation/n8n/package-lock.json`, `automation/n8n/runtime.json`
- `docs/architecture/phase7.md`, `docs/database/model.md`, `docs/api/api.md`
- `docs/business-process/processes.md`, `docs/requirements/requirements.md`, `docs/roadmap.md`
- `docs/testing/phase7-report.md`, `docs/testing/phase7-checks.json`
