# Chronos 1.0 — Manifesto da Fase 3

Arquivos autorais criados/atualizados exclusivamente no Chronos. `.env`, node_modules, build, caches e bancos ativos não entram no manifesto. Os bancos e binários de teste permanecem no runtime externo da tarefa.

## Arquivos atualizados

- `.env.example`
- `README.md`
- `CHANGELOG.md`
- `release.json`
- `backend/app/core/config.py`
- `backend/app/main.py`
- `backend/app/models/entities.py`
- `backend/app/schemas/phase2.py`
- `backend/app/api/routes.py`
- `backend/app/api/resources.py`
- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/vite.config.ts`
- `frontend/src/main.tsx`
- `frontend/src/styles/app.css`
- `scripts/check.ps1`
- `docs/api/api.md`
- `docs/database/model.md`
- `docs/requirements/requirements.md`
- `docs/testing/acceptance.md`
- `docs/roadmap.md`

## Arquivos adicionados

- `backend/alembic/versions/005_catalog_revisions.py`
- `backend/app/api/browser_session.py`
- `backend/scripts/smoke_phase3.py`
- `backend/tests/test_phase3.py`
- `docs/architecture/phase3.md`
- `docs/testing/phase3-checks.json`
- `docs/testing/phase3-report.md`
- `frontend/src/app.tsx`
- `frontend/src/components/forms.tsx`
- `frontend/src/components/ui.tsx`
- `frontend/src/hooks/auth.tsx`
- `frontend/src/hooks/data.ts`
- `frontend/src/pages/administration.tsx`
- `frontend/src/pages/employees.tsx`
- `frontend/src/pages/login.tsx`
- `frontend/src/pages/overview.tsx`
- `frontend/src/pages/structure.tsx`
- `frontend/src/services/client.ts`
- `frontend/src/tests/client.test.ts`
- `frontend/src/tests/forms.test.tsx`
- `frontend/src/tests/pages.test.tsx`
- `frontend/src/tests/setup.ts`
- `frontend/src/types/domain.ts`
- `frontend/vitest.config.ts`
- `docs/testing/phase3-file-manifest.md` (este manifesto).

## Arquivo removido

- `frontend/src/services/api.ts` — cliente antigo exclusivo da fixture; substituído por `services/client.ts`, autenticado. A rota histórica backend /demo/summary foi preservada.
