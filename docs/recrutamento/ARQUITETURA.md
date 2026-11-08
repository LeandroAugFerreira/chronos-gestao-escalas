# Chronos 1.0 — arquitetura auditada para recrutamento

**Diagramas de componentes e processo derivados do código.** Não representam cluster, backend hospedado ou integração de transporte/IA pública.

## Arquitetura lógica

~~~mermaid
flowchart LR
  V[Visitante autenticado] --> UI[React + TypeScript / Vite]
  UI --> C[client.ts / sessão do navegador]
  C --> API[FastAPI: rotas v1]
  API --> SEC[RBAC por ação e unidade]
  API --> VAL[Pydantic / regras de domínio]
  VAL --> ORM[SQLAlchemy e Alembic]
  ORM --> DB[(PostgreSQL alvo ou SQLite local explícito)]
  API --> SNAP[Snapshot de cenário / digests]
  SNAP --> QUEUE[Registro de execução no banco]
  QUEUE --> WORKER[Worker de otimização]
  WORKER --> CP[OR-Tools CP-SAT]
  CP --> VERIFY[Verificador independente de restrições]
  VERIFY --> ORM
  ORM --> REV[Proposta versionada]
  REV --> DEC[Submissão / segundo aprovador]
  DEC --> ORM
  API --> AGG[Analytics e relatório autorizado]
  AGG --> ORM
  N8N[Integração n8n opcional] -.-> BLOCK[Execução bloqueada por auditoria]
~~~

As telas consultam as APIs protegidas; o worker não é obrigatório para simples login/visão geral e só executa cálculos quando acionado em ambiente autorizado.

## Fluxo de otimização auditado

~~~mermaid
sequenceDiagram
  autonumber
  actor G as Gestor autorizado
  participant UI as React / OptimizationPage
  participant API as API FastAPI
  participant DB as Banco e snapshot
  participant W as Worker CP-SAT
  participant V as Verificador
  actor A as Outro aprovador
  G->>UI: Escolhe cenário e opções
  UI->>API: POST /api/v1/optimization
  API->>DB: Confere escopo e grava snapshot/digest
  DB-->>UI: Execução enfileirada
  W->>DB: Retira tarefa autorizada
  W->>W: CP-SAT sobre snapshot
  W->>V: Confere atribuições / cobertura / limites
  V->>DB: Salva resultado e lacunas
  G->>UI: Analisa proposta e bloqueios
  UI->>API: POST /api/v1/schedules/{id}/decision (submit)
  API->>DB: Revalida digest e restrições
  A->>API: POST /api/v1/schedules/{id}/decision (approve)
  API->>DB: Rejeita autoaprovação e entradas antigas
  DB-->>A: Decisão rastreável
~~~

## Governança da proposta

~~~mermaid
stateDiagram-v2
  [*] --> draft
  draft --> submitted: submit
  submitted --> approved: approve, outro responsável
  submitted --> rejected: reject
  approved --> superseded: nova versão aprovada
~~~

**Observação:** são transições presentes no código de decisão. Uma escala pode permanecer em rascunho/bloqueada se faltar cobertura, revisão de premissas, digest íntegro ou autorização. A transição do pai para superseded depende de aprovar uma versão sucessora válida.

## Separação de responsabilidades

| Componente | Evidência |
| --- | --- |
| API + middlewares, cabeçalhos de segurança | [backend/app/main.py](../../backend/app/main.py) |
| Auth via Argon2id/JWT/refresh | [backend/app/core/security.py](../../backend/app/core/security.py) |
| Cookies e CSRF para navegador | [backend/app/api/browser_session.py](../../backend/app/api/browser_session.py) |
| Escopo de usuário por permissão/unidade | [backend/app/api/dependencies.py](../../backend/app/api/dependencies.py) |
| Modelo relacional e histórico | [backend/app/models/entities.py](../../backend/app/models/entities.py) |
| Migrations | [backend/alembic/versions](../../backend/alembic/versions) |
| Preparação, solução CP-SAT, verificação | [backend/app/services/optimizer.py](../../backend/app/services/optimizer.py) |
| Snapshot assinado | [backend/app/services/optimization_snapshot.py](../../backend/app/services/optimization_snapshot.py) |
| Fila/worker | [backend/app/services/optimization_worker.py](../../backend/app/services/optimization_worker.py) |
| Revisão/aprovação | [backend/app/api/optimization.py](../../backend/app/api/optimization.py) |
| Frontend/rotas | [frontend/src/app.tsx](../../frontend/src/app.tsx) |
| Cliente da API | [frontend/src/services/client.ts](../../frontend/src/services/client.ts) |

## Modelagem e limites

Os dados têm organização e unidade, versões de calendário/cenário/solução e vínculos de contrato/qualificação. A SQLAlchemy representa relações e migrações Alembic; schemas e consultas controlam leitura de dados sensíveis. PostgreSQL é o alvo declarado; SQLite é permitido somente em contexto local de teste/demo fora do projeto/OneDrive.

A execução do solver não prova validade jurídica ou clínica; as fontes/regras configuradas precisam de revisão específica. **Automação n8n está bloqueada** após auditoria de dependências; o diagrama não a conecta a um runtime ativo.

[Auditoria](AUDITORIA.md) · [Estudo de caso](ESTUDO_DE_CASO.md).
