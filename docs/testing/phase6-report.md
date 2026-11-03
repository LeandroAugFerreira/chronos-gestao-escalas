# Chronos 1.0 — Relatório da Fase 6

Data: 24/10/2026. Checkpoint local de desenvolvimento, sem publicação e sem dados reais.

## Resultado entregue

OR-Tools CP-SAT calcula alocações por pessoa/atividade/plantão e verifica cobertura em intervalos exatos. Contratos, ciclos, competências, habilitações, ausências, pausas, descansos e histórico são restrições do modelo. O modo estrito exige cobertura; o diagnóstico quantifica lacunas e conserva as demais restrições. Parâmetros de dimensionamento e limites são informados pelo responsável, sem mínimos profissionais universais.

Fila persistente com lease, heartbeat, recuperação, cancelamento e resultado em subprocesso separado. O filho recebe fatos de negócio sem conexão ao banco e somente variáveis de runtime permitidas; credenciais de serviços/testes não são herdadas. Propostas e insumos são versionados e vinculados por digest. O verificador numérico independente precede submissão/aprovação; o autor não aprova sua própria proposta. Revisões individuais são explícitas e auditadas. Alterações dos fatos exigem novo cálculo.

Interface em `/otimizacao`, guardas por permissão/unidade, configuração de plantões/limites/cargos/ciclos, acompanhamento e cancelamento, alocações/lacunas e decisões. Aprovação interna não publica nem certifica validade jurídica. Escopo detalhado em [arquitetura da Fase 6](../architecture/phase6.md).

## Evidências executadas

| Verificação | Resultado |
|---|---|
| Backend: casos distintos das suites e rechecagens | 156 aprovados; sem falha/erro pendente ou skip |
| Bancos | SQLite em arquivo e PostgreSQL 17.11 real, schemas exclusivos de teste |
| Frontend | 45 testes aprovados em 6 arquivos, Vitest/Testing Library/JSDOM |
| Compilação | TypeScript e Vite aprovados; 2.342 módulos |
| Integração HTTP | Proxy Vite + FastAPI + cookies/CSRF + worker CLI/subprocesso reais; aprovada |
| Migrations | Modelo coincide com metadata; upgrade/downgrade e constraints nos dois bancos |
| Banco local | Migration 008, 32 tabelas, integridade OK e zero violações de FK |
| Identidade/fixture | Prompt Mestre/SHA-256 e Chronos 1.0 verificados; 350 pessoas e 19 setores reproduzíveis |
| Dependências | OR-Tools 9.15.6755 em Python 3.13/Windows; `pip check` sem conflito |
| Navegação visual real | Pendente; nenhum navegador automatizado usado |

Os 156 casos são a união por identificador de teste, sem contar repetições como novos casos. A primeira regressão completa executou 143 casos: 141 passaram e dois tiveram erro de preparação por falta de memória no host (Argon2 e PostgreSQL). Não houve alteração de parâmetros de segurança. Ambos passaram nas rechecagens em sequência. A rodada final de 40 casos passou, incluindo novas verificações; uma rodada adicional de quatro casos confirmou o isolamento final do processo e execução/cancelamento/sigilo reais do worker. Os XML locais do backend preservam o histórico; a evidência do frontend é a saída bem-sucedida do Vitest. `phase6-checks.json` consolida os resultados finais e as contagens distintas.

A primeira compilação também encontrou uma falha transitória de acesso a arquivo em node_modules; a repetição passou. Avisos remanescentes: depreciação do adaptador httpx/Starlette nos testes e comentários de tree-shaking de Zod descartados pelo Rollup. Não houve downgrade de segurança nem instalação global.

## Casos relevantes

- Cobertura contínua de 24 horas com ótimo conhecido e resultado repetível com seed/uma thread; falta de pessoal produz INFEASIBLE no estrito e minutos-pessoa de lacuna no diagnóstico.
- Pausa não cobre demanda, mesmo remunerada. Uma pessoa não cobre duas atividades simultaneamente. Limites diário/semanal, descanso semanal e teto de pessoas distintas permanecem obrigatórios.
- Competência ausente, habilitação ausente/vencida, ausência, contrato ambíguo/ausente, ciclo e compromissos históricos impedem alocação. Descanso de outra unidade e deslocamento são preservados.
- Sucessão de regra altera a restrição aplicável; verificador rejeita identificadores adulterados/seleção incompatível. Orçamento de tempo esgotado retorna UNKNOWN, sem afirmar inviabilidade.
- Cancelamento na fila e durante execução real; lease expirado recuperado com token novo; trabalhador antigo não confirma resultado. Custos e alocações pessoais são removidos para leitor agregado; gestor sem acesso financeiro não cria objetivo de custo.
- Submissão/aprovação com revisão/digest, bloqueios de premissas e lacunas, proibição de autoaprovação, decisão auditada e versão filha. A anterior permanece aprovada até a decisão da filha e seu conteúdo histórico é preservado.
- Mudança dos dados bloqueia submissão por STALE_INPUTS. Um teste com duas transações simultâneas confirmou, nos dois bancos, que a submissão aguarda a escrita concorrente e, após a confirmação dessa escrita, exige recálculo. Essa rodada adicional teve dois testes aprovados.

## HTTP e desempenho observado

O smoke criou banco e contas efêmeros fora do projeto. Confirmou 350 pessoas da fixture e mais uma pessoa de teste, login/cookie HttpOnly, revogação/logout, calendário, cenários, financeiro e worker em processo CLI separado. O cenário com 351 pessoas foi calculado em 2,975 s; a execução supervisionada e consultas da otimização consumiram 17,398 s na medição do smoke. Para uma demanda sintética de 420 minutos-pessoa, retornou OPTIMAL, cobertura 420 e lacuna zero. A proposta ficou em rascunho; submissão com premissas pendentes retornou 409. O banco principal não foi usado pelo smoke.

Essas medições descrevem instâncias específicas e incluem efeitos do host; não são benchmark de escala hospitalar mensal nem SLA. O caso de cobertura 24 horas é um teste separado, com três pessoas, não uma comprovação de dimensionamento do Hospital Horizonte.

Build medido: entrada 477,95 kB, chunk de otimização 23,31 kB, calendário 23,54 kB e gráficos compartilhados 365,17 kB, sem gzip. Inspeção visual/responsiva no navegador continua pendente pelo bloqueio já registrado na sessão; HTTP e JSDOM não substituem essa inspeção. Nenhum screenshot foi fabricado.

## Preservação do ambiente

Backup SQLite pré-migration: `chronos-before-phase6-008.sqlite3`, no runtime externo já usado pelo projeto. Integridade do backup e banco principal verificadas. Atualização de 007 para 008 e seed idempotente sem reimportar a fixture. Permanecem 350 colaboradores, 19 setores e 20 indisponibilidades UTC. Não foram criadas automaticamente regras, jornadas de calendário, cenários, projeções, jobs, propostas, decisões ou revisões no banco principal.

Segredos e bancos não estão no repositório. Nenhum outro projeto foi alterado. API/Vite/PostgreSQL e workers usados nos testes são encerrados pelos scripts; não foi criado serviço do Windows. A plataforma continua versão 1.0, fase 6, `published=false` e `release_ready=false`.

## Próxima etapa

Fase 7: eventos/outbox, scheduler opcional, central de automações e workflows n8n com deduplicação, retentativas, autenticação e execução real em teste. Nada foi ativado ou enviado a destinos externos nesta fase.
