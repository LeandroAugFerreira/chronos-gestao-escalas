# Chronos 1.0 — API e homologação local

Base: `/api/v1`. OpenAPI real em `/openapi.json`, Swagger em `/docs`. Produto e versão: Chronos 1.0. Login usa JSON e o access token é informado como Bearer. Não há cadastro público de organização nem de usuário administrador.

## Rotas públicas

| Método | Rota | Comportamento |
|---|---|---|
| GET | /health | Liveness, versão 1.0 e núcleo fase 9 |
| GET | /health/ready | 200 somente com banco e revisão 010_pattern_revision; 503 quando indisponível/desatualizado |
| GET | /demo/summary | Fixture sintética da Fase 1; independente do banco persistente |
| POST | /auth/login | organização (slug), username, password; retorna access/refresh e expires_in |
| POST | /auth/refresh | Consome refresh opaco e emite novo par; reutilização revoga a família |
| POST | /auth/logout | Revoga a família do refresh informado; 204 sem revelar existência da sessão |

Login tem limite persistido por IP/conta; configuração ausente não habilita senha/chave padrão. Refresh tokens são provas de posse; não os transmitir por URL. Respostas de API não devem ser armazenadas em cache.

O identificador de acesso pode ser um nome de usuário ou e-mail, com 3 a 80 caracteres ASCII entre letras/números, ponto, sublinhado, hífen, @ e +; o cadastro normaliza para minúsculas. O e-mail é usado apenas como identificador: não ativa SSO, verificação de titularidade ou envio de mensagens.

## Sessão web da Fase 3

`GET /session/csrf` fornece o token CSRF assinado e cookie HttpOnly correspondente. `POST /session/login`, `/session/refresh` e `/session/logout` exigem Origin permitido e `X-CSRF-Token` ligado ao contexto/família. Login recebe o mesmo JSON de `/auth/login`; refresh/logout usam cookie e não recebem refresh no corpo.

Login/refresh web retornam access_token, token_type, expires_in, csrf_token e user, sem refresh_token. O refresh fica em cookie HttpOnly/SameSite Strict, host-only; produção exige Secure/HTTPS e prefixo __Host-. O frontend usa proxy de mesma origem, sem habilitar credenciais CORS entre origens. Detalhes e limites em `docs/architecture/phase3.md`.

## Rotas protegidas

| Método | Rota | Permissão / comportamento |
|---|---|---|
| GET | /auth/me | Usuário ativo, organização e mapa de permissões/escopos |
| GET | /organizations, /organizations/{id} | org:read; somente a organização do principal |
| GET/POST e PATCH /{id} | /units | org:read / org:write global para criar; edição por escopo e revisão |
| GET/POST e PATCH /{id} | /departments | org:read / org:write na unidade; mudança de unidade não aceita setor com pessoas |
| GET/POST | /catalogs/{kind} | catalog:read / catalog:write global; job-roles, skills, qualifications; work-patterns somente leitura |
| GET/POST | /employees | people:read / people:write, com tenant e unidade |
| POST | /employees/export | people:read por organização/unidade; CSV básico de todas as páginas, filtros/ordem e auditoria |
| GET/PATCH | /employees/{id} | Nome/status/função/lotação com revision; transferência exige unidade+setor e permissão na origem/destino |
| GET/POST | /employees/{id}/contracts | Leitura finance:read; escrita people:write + finance:read; conflito por sobreposição |
| GET/POST | /employees/{id}/skills | people:read / people:write; referências dentro do tenant |
| GET/POST | /employees/{id}/qualifications | people:read / people:write; validade e status pendente de revisão |
| GET/POST | /employees/{id}/availability | people:read / people:write; instantes com fuso e intervalo positivo |
| GET/POST | /users | users:write global; criação de perfil/escopo sem eco de senha |
| GET | /roles | users:write global; matriz de seis perfis |
| GET | /audit | audit:read global; eventos da própria organização |
| GET | /analytics/workforce | org:read; quantidade de pessoas do banco no escopo permitido |
| GET | /analytics/overview | org:read; dashboard persistente, filtro unit_id, origem/data, contagens e jornadas contratuais |

Escopo resolve separadamente cada permissão. Financeiro não recebe lista de pessoas; Gestor não recebe salário. Catálogos são compartilhados dentro da própria organização. `PATCH /catalogs/{kind}/{id}` permite renomear funções/competências/qualificações com permissão global e revisão; jornadas são consultadas nesse catálogo e cadastradas em /work-patterns. Não há exclusão pública ou alteração de perfil/senha de usuários por esses endpoints.

## Listas e concorrência

Listas de unidades, setores, catálogos, pessoas, usuários e auditoria usam `page_number` (>=1), `page_size` (1–100) e retornam `items`, `total`, `page`, `page_size`. Pessoas aceitam busca, unidade, setor, status e sort allowlist (`name`, `registration`, `status`) com `descending`. Unidades/setores aceitam busca; setores aceitam unidade. Ordenações secundárias por ID preservam paginação estável.

POSTs de cadastro aceitam `Idempotency-Key` opaca (8–128 caracteres permitidos). Mesmo ator/tenant/rota/chave e conteúdo não repetem efeito; resposta inclui `Idempotency-Replayed: true`. Conteúdo divergente retorna 409. A representação retornada no replay é a atual do registro. Senhas e payload integral não são guardados no registro de idempotência.

PATCH de pessoa exige `revision`. Revisão antiga retorna 409 `STALE_VERSION`; não sobrescreve a alteração concorrente. Integridade, atualização e auditoria são transacionais. Access tokens revogados por logout/refresh reutilizado deixam de autorizar imediatamente.

## Erros e segurança

Formato: `code`, `message`, `correlation_id`, com `field_errors` contendo apenas localização/tipo quando aplicável. Nunca incluir entrada/senha, SQL ou credencial de conexão. Header `X-Correlation-ID` liga requisição/auditoria. Principais estados: 401 autenticação, 403 permissão, 404 registro fora do escopo/inexistente, 409 conflito/integridade/revisão, 422 validação, 429 login limitado, 503 banco/configuração indisponível. JWT tem algoritmo fixo, issuer/audience e claims obrigatórias. CORS somente para origens configuradas.

## Domínios futuros preservados

`/schedules`, `/optimization`, `/approvals`, `/automations`, `/notifications` e analytics completo continuam previstos. Jobs longos retornarão 202, com status consultável. Solver e automações continuam nas fases correspondentes; LaborRules possui os critérios limitados documentados na Fase 4. Veja cronograma e especificações dos respectivos domínios.

## Calendário e LaborRules — Fase 4

| Método | Caminho | Contrato |
|---|---|---|
| GET | /calendar | schedule:read; start/end com fuso, até 62 dias; filtros unit_id/department_id/employee_id; paginação até 100; somente rascunhos que interceptam a janela |
| POST | /calendar/preview?shift_id=opcional | schedule:write; pessoa/setor/início/fim/pausas/título; edição exclui o próprio registro; retorna resultado e digest, sem gravar |
| POST | /calendar | schedule:write; mesmo conteúdo + preview_digest; prévia divergente retorna 409; Idempotency-Key suportada |
| PATCH | /calendar/{id} | schedule:write; mesmo conteúdo + preview_digest + revision; pessoa fixa; mantém snapshot de cada revisão |
| POST | /calendar/{id}/cancel | schedule:write; revision obrigatória; preserva registro/histórico; não há exclusão pública |
| GET | /calendar/{id}/evaluations | schedule:read; snapshots imutáveis por revisão, dentro do escopo da unidade |
| GET | /labor-rules | rules:read; escopo organizacional/local e por contrato; paginação |
| POST | /labor-rules | rules:write global; versão imutável; fonte/vigência/limites/escopo; status pendente ou declaração de validação com evidência; supersedes_id opcional e estritamente validado |
| POST | /work-patterns | rules:write global; nome/descrição e configuration opcional com cycle de work/rest e shift_minutes; sempre pending_review |

Critérios: max_daily, max_weekly, min_break, min_rest, min_weekly_rest. Além deles: sobreposição, indisponibilidade, contrato vigente/carga semanal, competências e habilitações da função. Fontes sem revisão e famílias ausentes aparecem nos achados. Gravar rascunho não autoriza, publica ou aprova jornada. Ver arquitetura da Fase 4 para semântica de janelas, sucessões e limites.

As pausas exigem início/fim internos ao plantão, sem sobreposição; paid distingue trabalho de base remunerável. Datas de regras e plantões exigem fuso e precisão de minutos. Fonte é texto, nunca código executável. Não existem PATCH/DELETE de regra nem aprovação de calendário nesta entrega.

## Cenários e financeiro — Fase 5

| Método | Caminho | Contrato |
|---|---|---|
| GET | /scenarios | scenario:read; filtro unit_id e paginação; somente metadados públicos |
| POST | /scenarios | scenario:write/read no escopo; unidade/população, mês no dia 1, modo calendar/cycle, fonte, demanda; Idempotency-Key; versão 1 ou sucessora explícita |
| GET | /scenarios/{id} | scenario:read; entradas e agregados de capacidade; sem base salarial/evidências pessoais |
| GET | /scenarios/{id}/evidence | scenario:read + people:read na unidade; evidência técnica de capacidade, sem salários |
| POST | /scenarios/compare | scenario:read; left_id/right_id da mesma unidade/população/mês; variações agregadas |
| POST | /financial/preview | scenario:read + finance:read/simulate na unidade; projeção sobre snapshot; sem persistência |
| POST | /financial | mesmas permissões; salva projeção imutável e auditoria; Idempotency-Key |
| GET | /financial | finance:read; filtro scenario_id e paginação por escopo de unidade |
| GET | /financial/{id} | finance:read; premissas/resultados congelados, sem lista de salários individuais |
| POST | /financial/compare | finance:read; left_id/right_id; mesma população/mês; comparação monetária e checagem salarial nominal limitada |
| POST | /financial/{id}/sensitivity | finance:read/simulate; driver hours_volume/fixed_costs/charges_rate e delta_bps entre −5000 e +5000; não grava/muta original |

Cenários usam reference_month como data no primeiro dia do mês. Meta semanal em minutos; ciclo exige work_pattern_id estruturado e cycle_anchor. Demanda por atividade aplica ao mês e inclui setor, início local, duração até 1440 minutos, weekdays 0=segunda até 6=domingo, quantidade, competências/habilitações e fonte. Não há valores normativos universais. Até 1.000 pessoas/2.000 plantões por cenário síncrono.

Projeção percorre 12 meses. Valores de entrada/saída em centavos, taxas em pontos-base (100=1%), volumes em minutos. Componentes fixed/percent/hours têm fonte, vigência relativa M1–M12, sazonalidade e recorrência monthly/once. Horas exigem salário-base e divisor explicitamente informados; razão de conversão e inclusão de hora-base são premissas, sem padrão jurídico. Extras/noturno usam modelo hours; encargos podem escolher base payroll/overtime/night/payroll_and_additions. Novas contratações e exclusões justificadas são opcionais. Categorias ausentes permanecem pendentes.

Não há PATCH/DELETE público de cenários/projeções nem aprovação nesta fase. Versões anteriores permanecem imutáveis. Percentual de comparação com base zero retorna null. Erros adicionais: INCOMPARABLE, PATTERN_CONFIGURATION_REQUIRED, AMBIGUOUS_TIME, AMBIGUOUS_PAYROLL, CURRENCY_MISMATCH e limites de população/valores. Dados salariais não aparecem em respostas de capacidade, mesmo para quem criou o cenário.

Indisponibilidades antigas: AvailabilityInput agora normaliza explicitamente UTC, inclusive no SQLite. O reparador de demonstração é CLI restrito, não uma rota pública. Veja relatório da Fase 5.

## Otimização e propostas — Fase 6

| Método | Caminho | Contrato |
|---|---|---|
| POST | /optimization | optimization:write + scenario:read + people:read + schedule:read na unidade; OptimizationInput; retorna 202; Idempotency-Key; fila sem execução na requisição |
| GET | /optimization | optimization:read; filtro unit_id e paginação |
| GET | /optimization/{id} | optimization:read; estado, revisão, tentativas, heartbeat, insumos públicos, resultado e schedule_id; snapshot privado omitido |
| POST | /optimization/{id}/cancel | optimization:write; revision; cancela queued ou solicita parada de running |
| GET | /schedules | optimization:read; filtro unit_id e paginação |
| GET | /schedules/{id} | optimization:read; proposta, verificação e decisões históricas |
| POST | /schedules/{id}/decision | revision, schedule_digest, action submit/approve/reject e reason; submit exige optimization:write; approve/reject exigem schedule:approve; aprovação por pessoa distinta do autor |
| GET | /optimization-review-targets | rules:write; kind contract/work_pattern/qualification/scenario; paginação; digest do conteúdo atual e rótulo sem salário; contratos exigem finance:read; dados pessoais/cenários respeitam escopo |
| POST | /optimization-reviews | rules:write + escopos adicionais; kind, entity_id, entity_digest, source, evidence; contrato/habilitação exigem people:write; jornada exige permissão global; registra revisão humana individual |

OptimizationInput exige cenário, nome, start_date/end_date exclusivo (até 31 dias no mês), 1–12 plantões candidatos e limits. Cada plantão define nome, hora local, duração, pausa interna e dias da semana. Os sete limites são max_daily_minutes, max_weekly_minutes, min_rest_minutes, min_break_minutes, break_threshold_minutes, min_weekly_rest_minutes e max_consecutive_days, todos explícitos, com source/validation_status/review_evidence. Nenhum limite jurídico é preenchido automaticamente.

Opções: mode strict/diagnostic; eligibility verified/hypothesis; activity_job_role_ids por índice da atividade; cycle_anchors por jornada; history_review_evidence; allow_cross_department; cross_unit_travel_minutes; continuity_max_people_per_activity_day; coverage_windows por atividade, com início/fim UTC, quantidade, prioridade e revisão; parent_schedule_id; seconds 1–120; seed; workers 1–4; balance_weight/preference_weight/cost_weight. Custos cost_cents por plantão exigem cost_source e finance:read, assim como objetivo monetário ativo.

Não há PATCH/DELETE público de insumos, solução ou proposta. Nova versão é novo job ligado à proposta pai, com mesma unidade, população e horizonte. Aprovação recaptura os insumos e repete verificação numérica; responde 409 STALE_INPUTS se algo mudou, APPROVAL_BLOCKED para pendências/lacunas, REVISION_CONFLICT para revisão/digest desatualizados e 403 SECOND_REVIEWER_REQUIRED para autoaprovação. Rejeição registra justificativa sem exigir recálculo. A versão pai aprovada só é substituída ao aprovar a filha. Nenhuma ação publica externamente.

Perfis: admin/hr/manager leem e criam cálculos/aprovam dentro do escopo; analyst lê agregados. Alocações são omitidas sem people:read; custos e componente monetário do objetivo são omitidos sem finance:read. Revisões são fonte/evidência declaradas pelo responsável, não certificação jurídica.

Estado succeeded indica que o processamento concluiu, mesmo com resultado CP-SAT INFEASIBLE/UNKNOWN. Somente solução FEASIBLE/OPTIMAL e verificação válida cria proposta. Job failed contém error_code seguro, sem traceback; limites de modelo e worker são documentados na arquitetura. O consumidor CLI é iniciado separadamente e não depende de n8n.

## Automações e integração — Fase 7

| Método | Caminho | Contrato |
|---|---|---|
| GET | /automations | automation:read; filtro unit_id/paginação; definições e integration_configured sem URL/token |
| PATCH | /automations/{id} | automation:manage + permissão da rotina; revision/enabled/owner_id/interval_minutes/parameters; responsável ativo e autorizado ao habilitar |
| POST | /automations/{id}/run | automation:run + permissão da rotina; revision; 202 e evento; Idempotency-Key |
| GET | /automation-events | automation:read; filtro unit_id/paginação; fila e metadados, sem lease_token; referências pessoais/auditoria protegidas |
| GET | /automation-executions | automation:read; unit_id/code/paginação; detalhes exigem permissão da rotina, incluindo audit:read para A07 |
| GET | /automation-deliveries | automation:read; paginação; estado/HTTP/tentativas, sem tokens |
| POST | /automation-queue/{kind}/{id}/{action} | automation:run na unidade; kind events/deliveries, action retry/cancel, revision; retentativa somente failed e cancelamento queued/running |
| GET | /automation-notices | automation:read; comum ou destinado ao usuário, sempre dentro do escopo |
| POST | /automation-notices/{id}/acknowledge | destinatário autorizado, ou automation:run para aviso comum; revision; ciência sem certificar solução |
| GET | /automation-artifacts | automation:read; paginação; arquivos financeiros filtrados por finance:read |
| GET | /automation-artifacts/{id} | automation:read + finance:read quando aplicável; JSON com filename/content_type/digest/content CSV |
| GET | /automation-suggestions | optimization:read; sugestões por escopo, origem/motivo/contagem; sem criar solver automaticamente |
| GET/POST | /integration-credentials | integration:manage na unidade; criação exige automation:run e people:write se autorizar disponibilidade; token_once somente na criação |
| POST | /integration-credentials/{id}/revoke | integration:manage; revision; revogação efetiva para requisições seguintes |
| POST | /integration/automation-events | Bearer de serviço com ação workflow_callback; request_id/event_id/definition_id UUID, code A02/A03/A04/A06 e sent_at aware; entrega precisa estar vinculada à unidade e running/succeeded |
| POST | /integration/availability | Bearer de serviço com ação availability + people:write atual; request_id/sent_at/employee_id e AvailabilityInput; 201, idempotente por recibo |

As permissões de integração são revalidadas pelo responsável atual da chave, não pelo payload. Uma requisição nova precisa estar dentro de cinco minutos; repetição idêntica devolve o recibo e a mesma entidade, e conteúdo diferente com o mesmo request_id retorna 409 REPLAY_CONFLICT. O HMAC exclui apenas sent_at. Header opcional X-Chronos-Workflow-Execution registra a execução informada pelo n8n. Tokens não são retornados em listagens e não aparecem em auditoria.

Parameters: lookahead_days 1–366, monitor_limit 1–500 e deliver_n8n false por padrão. Agenda usa intervalo de 1–10080 minutos; null significa sem agenda temporal. Definições/eventos não executam por simples GET. A ativação do scheduler é opção da CLI. A07 exige audit:read; resultados restritos são devolvidos com restricted=true, sem apresentar ausência de acesso como zero achados. O adaptador n8n desta fase aceita somente loopback development/test; a base e o token ficam no ambiente privado.

Erros adicionais: OWNER_PERMISSION_REQUIRED, N8N_NOT_CONFIGURED, AUTOMATION_UNAVAILABLE, REPLAY_CONFLICT, STALE_INTEGRATION_REQUEST, INVALID_INTEGRATION_TOKEN e INVALID_EXECUTION_REFERENCE. Erros de execução/entrega são códigos sanitizados, sem traceback, body de terceiros ou credencial. Não há rota de publicação ou aprovação automática.

## Fase 8 — Analytics e exportações

| Método | Caminho | Contrato |
|---|---|---|
| GET | /analytics/history | scenario:read; unit_id obrigatório, reference_month opcional no dia 1, paginação até 100 |
| GET | /analytics/options/{scenario_id} | Versão no escopo; até 100 otimizações/projeções recentes conforme respectivas permissões |
| POST | /analytics/report | scenario_id obrigatório; optimization_id e financial_id opcionais, include_people=false; mesma versão/unidade; tabelas, manifest e explicação |
| POST | /analytics/export | Mesmo corpo + format csv/xlsx; base64, filename, content_type, byte_length, sha256, data_sha256; preparação auditada |

Todos exigem sessão autenticada, tenant e escopos atuais. Ausência de resultado é nulo; não há zero implícito. Erros: REPORT_REFERENCE (422), REPORT_PERIOD (422), REPORT_LIMIT (422), REPORT_RECONCILIATION (409), EXPORT_PRECISION/EXPORT_TEXT (422), além de 401/403/404. Limites de 20.000 linhas e 8 MiB. Respostas no-store. Sem publicação ou envio à IA externa. [Detalhes](../architecture/phase8.md).

## Fase 9 — Limites e operação

Corpos API limitados a 1 MiB/10 s por padrão antes do parsing. REQUEST_TOO_LARGE (413), REQUEST_FRAMING (400), REQUEST_ENCODING (415), REQUEST_BODY_TIMEOUT (408). Erro inesperado retorna INTERNAL_ERROR (500) sem traceback, com X-Correlation-ID e no-store. Cabeçalhos nosniff/DENY/no-referrer/Permissions-Policy adicionados. Produção exige origens HTTPS explícitas e não expõe docs/OpenAPI.

Health identifica fase 9; ready exige 010_pattern_revision. A revisão de jornadas mantém o digest e o incremento agora persistente; digest obsoleto retorna 409. A integração n8n development fica bloqueada pela auditoria, sem remover endpoints testados com receptores sintéticos no modo test. Não há endpoint de restauração ou publicação: recuperação é CLI apenas em destino novo. [Arquitetura](../architecture/phase9.md).

## Exportação cadastral — homologação de 27/10/2026

`POST /api/v1/employees/export` exige Bearer com `people:read`. JSON aceita somente `unit_id`, `department_id`, `status` (`active`/`inactive`), `search` (até 120 caracteres), `sort` (`name`/`registration`/`status`) e `descending`. Campos opcionais de seleção podem ser omitidos ou nulos; `search`, `sort` e `descending` usam os defaults da listagem. Não aceita paginação, organização arbitrária, campos extras ou inclusão de salários. Exemplo: `{"unit_id": null, "department_id": null, "status": "active", "search": "HH", "sort": "registration", "descending": false}`.

A resposta JSON traz `content` base64 do CSV, `encoding=base64`, `content_type`, nome, SHA-256, tamanho, `row_count`, colunas, `export_id`, data UTC e aviso de armazenamento/proteção de texto. Máximo de 20.000 linhas e 8 MiB de CSV; excesso retorna 422 `PEOPLE_EXPORT_LIMIT`, sem arquivo parcial ou auditoria de sucesso. Uma seleção sem dados retorna cabeçalho e zero linhas. Unidade/setor fora do escopo resultam em seleção vazia, sem expor sua existência. O arquivo inclui apenas os dez campos de `EmployeeOutput` do cadastro básico, com texto perigoso protegido por apóstrofo; não inclui vínculos profissionais ou financeiros. A preparação é auditada como `people.export`; não prova download ou abertura do arquivo. Veja o [relatório](../testing/people-export-2026-10-27-report.md).
