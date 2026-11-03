# Chronos 1.0 — Execução e testes da Fase 2

## Ambiente leve

Na raiz do projeto, PowerShell:

```powershell
$env:CHRONOS_RUNTIME_DIR = Join-Path $env:LOCALAPPDATA 'Chronos\1.0'
.\scripts\setup.ps1
.\scripts\create-admin.ps1
.\scripts\start-backend.ps1
```

Setup preserva `.env` existente; em uma instalação nova gera chave aleatória e SQLite fora do OneDrive, executa migrations e seed idempotente. Nenhuma senha padrão é criada. `create-admin` pede senha no terminal e não sobrescreve usuário existente. Organização para login: `horizonte`; usuário inicial: `admin`. Segredo do ambiente não é mostrado.

Abra `http://127.0.0.1:8017/docs`. Execute `/auth/login`, copie somente o access token para **Authorize** (HTTPBearer), consulte `/auth/me`, `/employees` e `/analytics/workforce`. O refresh é enviado somente a `/auth/refresh` ou `/auth/logout`. Nenhum token é necessário para health ou resumo da fixture pública. A tela de login ainda não faz parte do frontend.

Gerenciamento direto, usando Python do runtime:

```powershell
$pythonPath = Join-Path $env:CHRONOS_RUNTIME_DIR 'venv\Scripts\python.exe'
& $pythonPath .\backend\scripts\manage.py migrate
& $pythonPath .\backend\scripts\manage.py seed-demo
# Repor somente a demonstração, preservando acessos, unidades e auditoria:
& $pythonPath .\backend\scripts\manage.py restore-demo --confirm 'Hospital Horizonte'
.\scripts\check.ps1
```

## PostgreSQL principal

Configure `CHRONOS_DATABASE_URL` no ambiente ou `.env` com driver `postgresql+psycopg`, usuário, senha, host, porta e banco. Desative `CHRONOS_ALLOW_SQLITE`. Execute migrations e seed antes de iniciar a API. `/health/ready` exige a revisão atual do banco; iniciar o servidor não confirma banco pronto.

O Compose fornece somente PostgreSQL 17, bind em loopback porta 5547 e volume próprio. Exige Docker disponível e `CHRONOS_POSTGRES_PASSWORD` no ambiente; não possui senha padrão. O Compose é uma opção de reprodução, não instala Docker automaticamente.

```powershell
# Defina a senha no ambiente local antes do comando, sem versioná-la.
docker compose up -d postgres
```

Para testes, crie banco **exclusivo** com nome terminado em `_test` e configure `CHRONOS_TEST_POSTGRES_URL`. A suite cria um schema aleatório `chronos_test_<uuid>` por teste e remove somente esse schema ao finalizar. Não apontar para banco de uso real. As credenciais devem ter permissão de criar/remover schema nesse banco de teste.

```powershell
# CHRONOS_TEST_POSTGRES_URL contém a conexão do banco exclusivo de teste.
.\scripts\check-postgres.ps1
```

`backend/scripts/run_tests.py`, utilizado pelo check geral, também lê essa variável do `.env` ignorado. Sem variável, o perfil SQLite executa e a sentinela PostgreSQL é marcada skipped; isso não valida PostgreSQL. Com a variável, os testes de domínio/persistência rodam em ambos os bancos e falha de conexão é erro, não skip.

## Runtime portátil verificado nesta sessão

O pacote oficial PostgreSQL 17.11 da EDB foi extraído apenas em `chronos-runtime/postgres`; nenhum serviço ou instalação global foi criado. A origem é a [página oficial de binários](https://www.enterprisedb.com/download-postgresql-binaries), também referenciada pela [página PostgreSQL para Windows](https://www.postgresql.org/download/windows/). O cluster de teste exclusivo usa loopback 5547, SCRAM-SHA-256, shared_buffers 32 MB e até 20 conexões.

O runtime conserva `pg-test-data` e `pg-test.env` com a credencial de teste, fora do projeto. Essa configuração não permanece no `.env` principal após a validação, evitando exigir um servidor de teste ativo para o modo SQLite. Para reproduzir ambos os perfis na mesma máquina:

```powershell
$env:CHRONOS_RUNTIME_DIR = 'C:\Users\leand\.codex\visualizations\2026\10\24\01a16f80-a854-7dd2-abbc-ed567dc8b313\chronos-runtime'
.\scripts\test-portable-postgres.ps1
```

O script preserva um servidor já ativo; quando o inicia, encerra-o ao terminar, inclusive em falha dos testes. Não baixa nem instala PostgreSQL automaticamente em outra máquina. Para outro ambiente, usar o perfil PostgreSQL/Compose descrito acima.

## Cobertura

Migrations upgrade/downgrade e comparação do schema com o modelo; persistência após nova engine; importação repetida; rollback de importação quebrada; restauração restrita; senha Argon2id; JWT adulterado, vencido e claims inválidas; refresh/rotação/replay/logout; usuário desativado; limite de login após reinício; seis perfis, escopos e minimização de salário; referências de outra organização; FKs no banco; paginação/filtros/ordenação; edição concorrente; auditoria transacional; erro sem eco de segredo; idempotência; datas/contratos/indisponibilidade; SQLite opt-in e localização protegida.

SQLite não valida locking PostgreSQL, RLS, comportamento de concorrência sob carga ou operação Docker. Os testes com PostgreSQL real devem passar antes de encerrar o aceite da persistência. Nenhum teste desta fase valida solver, regras trabalhistas, automações n8n ou fluxo de aprovação.
