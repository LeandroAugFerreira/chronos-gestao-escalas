# Chronos 1.0 — Arquivos da Fase 2

Somente o projeto Chronos foi alterado. `.env` local contém segredos e não entra no manifesto/repositório. Venv, binários PostgreSQL, bancos e credenciais de teste ficam no runtime externo exclusivo, sem instalações globais.

## Arquivos existentes atualizados

- `.env.example`
- `README.md`
- `CHANGELOG.md`
- `release.json`
- `backend/requirements.txt`
- `backend/requirements-lock.txt`
- `backend/app/core/config.py`
- `backend/app/main.py`
- `backend/app/api/routes.py`
- `backend/tests/test_checkpoint.py`
- `scripts/setup.ps1`
- `scripts/check.ps1`
- `docs/roadmap.md`
- `docs/database/model.md`
- `docs/api/api.md`
- `docs/requirements/requirements.md`
- `docs/testing/acceptance.md`

## Arquivos adicionados

- `backend/alembic/env.py`
- `backend/alembic/script.py.mako`
- `backend/alembic/versions/001_identity.py`
- `backend/alembic/versions/002_organization.py`
- `backend/alembic/versions/003_people.py`
- `backend/alembic/versions/004_idempotency.py`
- `backend/alembic.ini`
- `backend/app/api/auth.py`
- `backend/app/api/dependencies.py`
- `backend/app/api/resources.py`
- `backend/app/core/database.py`
- `backend/app/core/security.py`
- `backend/app/models/entities.py`
- `backend/app/repositories/scoped.py`
- `backend/app/schemas/phase2.py`
- `backend/app/services/audit.py`
- `backend/app/services/auth.py`
- `backend/app/services/idempotency.py`
- `backend/app/services/seed.py`
- `backend/scripts/manage.py`
- `backend/scripts/run_tests.py`
- `backend/tests/test_phase2.py`
- `docker-compose.yml`
- `docs/architecture/phase2.md`
- `docs/testing/phase2-checks.json`
- `docs/testing/phase2-report.md`
- `docs/testing/phase2.md`
- `scripts/check-postgres.ps1`
- `scripts/create-admin.ps1`
- `scripts/test-portable-postgres.ps1`
- `docs/testing/phase2-file-manifest.md` (este manifesto).

## Fora do repositório

Runtime: `C:\Users\leand\.codex\visualizations\2026\10\24\01a16f80-a854-7dd2-abbc-ed567dc8b313\chronos-runtime`. Contém dependências isoladas, SQLite, PostgreSQL portátil, cluster exclusivo de teste e `pg-test.env` privado. Não incluir em release ou publicação.
