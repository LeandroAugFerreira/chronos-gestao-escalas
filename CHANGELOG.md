# Chronos 1.0 — Changelog

## Chronos 1.0 — identidade, Windows e manual online (2026-11-01)

- Identidade própria em azul profundo, cobre e papel, símbolo vetorial e assinatura do autor. Login, navegação, dashboard e componentes compartilhados atualizados; temas e permissões preservados.
- Iniciador desktop com base fictícia por instalação, acesso demo de consulta, criação inicial de administrador próprio, API/interface no mesmo endereço local e workers de otimização/eventos. Sem n8n ou agendamento automático.
- Worker compatível com executável sem console, com protocolo de arquivos para o processo do otimizador e encerramento controlado.
- Manual HTML com índice, roteiro para visitantes/recrutadores e orientações dos módulos. Página do portfólio preparada com download do aplicativo e código-fonte como alternativa técnica.
- Build frontend aprovado; 88 testes frontend e 47 testes backend de otimização, worker e empacotador aprovados. Relatórios do executável são registrados separadamente após validação do binário.

## Chronos 1.0 — execução local e manual (2026-10-27)

- Manual passo a passo e PDF de nove páginas com instruções dos módulos, interpretação dos resultados e operação local.
- Cadastro de acessos aceita e-mail como identificador, com normalização em minúsculas e os mesmos papéis/escopos. Não ativa login social ou envio de e-mail.
- Testes de acesso por e-mail, autenticação/RBAC e formulário; banco de demonstração preservado, sem migration ou publicação.

## Chronos 1.0 — exportação cadastral (2026-10-27)

- CSV do cadastro básico na tela de colaboradores e em POST /employees/export, com filtros e ordem compartilhados com a listagem, todas as páginas e escopo por organização/unidade.
- Saída sem salários, contratos ou evidências; UTF-8/BOM, proteção de fórmulas, limites sem truncamento, hash/tamanho conferidos no cliente e auditoria sem dados pessoais integrais.
- Testes de reconciliação, permissões, limites, falhas e integração dos filtros. Nenhuma migration, instalação de dependências ou alteração do banco principal.
- Pacote local atualizado; n8n, QA visual, Power BI Desktop e aceite de produção/publicação permanecem pendentes.

## Chronos 1.0 — homologação local (2026-10-27)

- Criação de contratos, qualificações e competências no detalhe do colaborador, com permissões por unidade, centavos exatos, vigências e idempotência em retentativas.
- Indicadores de revisão refletem a API; indisponibilidade reutiliza o formulário com fuso da unidade.
- 19 novos testes frontend e dois casos de API executados em SQLite e PostgreSQL; nenhuma migration ou gravação no banco principal.
- Candidata n8n 2.45.4 auditada sem instalação/partida: 8 itens críticos e 81 altos. Bloqueio mantido.
- Novo pacote local de revisão; navegador, Power BI Desktop e aceite de produção/publicação continuam pendentes.

## Chronos 1.0 — preparação local da Fase 10 (2026-10-26)

- Manual, handover, roteiro, estudo de caso e mapa de cobertura com pendências explícitas.
- Microensaio first-fit/CP-SAT com insumos iguais, 3/2 profissionais fictícios e sem alegação de produtividade humana.
- Empacotador/verificador ZIP com seleção de fontes, exclusão de segredos/bancos/runtimes, hashes, limites e proteção de caminhos/sobrescrita.
- Nome oficial dos metadados corrigido para UTF-8. Núcleo, banco e regras permanecem no checkpoint validado da Fase 9.
- Plano de capturas preparado; screenshots/QA, n8n e Power BI Desktop seguem pendentes. Pacote de revisão sem liberação de produção ou publicação.

## Chronos 1.0 — checkpoint da Fase 9 (2026-10-26)

- Limites de corpo/recebimento HTTP, framing, compressão, cabeçalhos e erros 500 seguros; origens explícitas e perfil de produção restrito.
- Coluna revision de WorkPattern via migration 010_pattern_revision, mantendo incremento/digest e rejeição de revisão obsoleta.
- Backup SQLite e restauração apenas em pasta nova; suspensão de sessões/chaves/rotinas/filas na cópia. Dump/restore nativo PostgreSQL testado em banco descartável.
- Vitest 5.0.5 corrige os avisos encontrados no frontend; auditorias finais frontend/Python sem avisos conhecidos.
- n8n 2.44.6 e candidata 2.44.7 mantêm avisos altos/críticos: partida/setup/smoke bloqueados, sem remover runtime ou workflows. Consumidor local preservado.
- Fluxo integrado e smoke HTTP real; Excel nativo em somente leitura. Navegador e Power BI Desktop permanecem pendentes; produção/publicação não liberadas.

## Chronos 1.0 — checkpoint da Fase 8 (2026-10-25)

- Analytics com seleção explícita de cenário/execução/projeção, histórico por mês/unidade, fontes, períodos e hashes.
- CSV/XLSX autorizados e reconciliados, proteção de fórmulas, dados tipados, limites e auditoria de preparação do download.
- Dataset local Power BI com grãos, relacionamentos, consultas M, medidas DAX e instruções de atualização/segurança.
- Explicações determinísticas gratuitas sem IA externa, sem alterar cálculos ou aprovações.
- XLSX reaberto, recalculado e renderizado pela ferramenta de artefatos. QA de navegador e Excel/Power BI Desktop permanecem pendentes; sem publicação.
- Schema permanece em 009_automations; 350 colaboradores e 19 setores preservados no banco principal. Evidências em docs/testing/phase8-report.md.

## 25/10/2026 — Checkpoint da Fase 7

Outbox transacional e rotinas A01–A07, consumidor local com leases/retentativas/cancelamento, scheduler opcional e definições desativadas por padrão. Alertas internos deduplicados, avisos para outro aprovador, CSV de indicadores protegido e sugestões de reotimização sem trocar a proposta existente. Central de automações e links para preparar nova versão. Credenciais de serviço por unidade/ação, revogação, timestamps/recibos e replay protegido. Quatro workflows n8n importados e executados em loopback com callback confirmado. Node 24 e n8n preparados apenas no runtime externo, preservando o Node do frontend. Migration 009 e 41 tabelas, sem ativação automática no banco principal. Sem publicação externa; analytics/XLSX/Power BI ficam na Fase 8.

## 24/10/2026 — Checkpoint da Fase 6

OR-Tools 9.15 CP-SAT em subprocesso supervisionado, fila persistente com leases/heartbeat/cancelamento/recuperação, snapshots sem salários e diagnóstico estrito ou com lacunas. Cobertura por intervalos exatos, pausas, contratos/ciclos, competências/habilitações, indisponibilidade, descansos e histórico. Propostas versionadas, verificação numérica independente, revisão individual de premissas e submissão/aprovação/rejeição auditadas. Aprovação por outro responsável e recaptura transacional de insumos; alterações exigem nova versão. Tela de otimização integrada ao menu e permissões. Oitava migration, 32 tabelas. Nenhuma regra/premissa da demonstração foi validada automaticamente; nada foi publicado. n8n/scheduler seguem na Fase 7.

## 24/10/2026 — Checkpoint da Fase 5

Cenários imutáveis com capacidade por calendário/ciclo, demanda por atividade e snapshots. Projeções financeiras de 12 meses, Decimal/centavos, parcelas fixas/percentuais/horas, recorrência/sazonalidade, contratações, comparativos e sensibilidade. Salários contratuais preservados ao mudar metas; nenhuma alíquota/divisor universal. Sétima migration e 28 tabelas; permissões financeiras independentes. Normalização UTC de indisponibilidades na API/importador e reparação conservadora de 20 registros sintéticos legados confirmados no SQLite. Sem publicação; solver/aprovações seguem na Fase 6.

## 24/10/2026 — Checkpoint da Fase 4

Calendário semanal/mensal com plantões, pausas remuneradas/não remuneradas, indisponibilidades, prévia obrigatória, rascunhos, revisão/cancelamento e avaliações históricas. LaborRules tipado com escopo, vigência, fontes, sucessão explícita de versões e quatro resultados; contratos, competências, habilitações e histórico nas bordas considerados. Jornada por ciclo configurável sem autorização jurídica por nome. Sexta migration, 26 tabelas. Consultas a fontes oficiais documentadas; nenhum mínimo hospitalar universal ativado. Testes nos dois bancos, componentes e HTTP real; QA visual segue pendente. Sem publicação.

## 24/10/2026 — Checkpoint da Fase 3

Login e sessão web com cookie HttpOnly/CSRF; access token em memória. Dashboard integrado ao banco com filtro e gráficos. Gestão de colaboradores, lotação, unidades, setores, catálogos, criação de acessos e auditoria. Formulários RHF/Zod, Tailwind, temas, navegação móvel e estados de rede. Quinta migration para revisão de catálogos. Testes em SQLite/PostgreSQL, componentes e HTTP real via proxy. Inspeção visual no navegador permanece pendente; sem publicação.

## 24/10/2026 — Checkpoint da Fase 2

SQLAlchemy, PostgreSQL/psycopg e SQLite opt-in; quatro migrations Alembic e 23 tabelas. Autenticação Argon2id/JWT, refresh rotacionado, revogação, rate limit persistente, RBAC por organização/unidade e consultas salariais restritas. Cadastros protegidos, paginação, filtros, revisão otimista, auditoria transacional e idempotência. Importação reproduzível de 350 pessoas e restauração protegida da demonstração. PostgreSQL 17.11 portátil usado para validação real; sem serviço global ou publicação. Relatório em `docs/testing/phase2-report.md`.

## 24/10/2026 — Checkpoint da Fase 1

Identidade Chronos 1.0 e Prompt Mestre consolidado. Cenário Hospital Horizonte com 350 pessoas, 19 setores e configuração multissegmento. Requisitos, arquitetura, modelo relacional, LaborRules, CP-SAT, financeiro, processos/n8n, aceite e cronograma documentados. Primeira API FastAPI e frontend React/TypeScript de leitura de fixture sintética reproduzível.

Não constitui release funcional completo. Persistência e autenticação são Fase 2; calendário, simuladores, solver e automações seguem no plano incremental. Não houve publicação ou integração externa de negócio.
