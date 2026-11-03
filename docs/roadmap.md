# Chronos 1.0 — Cronograma por fases

Sequência condicionada ao aceite anterior. Estimativas em dias úteis de trabalho técnico, sem compromisso de calendário; revisão ao final de cada fase. Checkpoint atual: homologação local de 27/10/2026 com exportação cadastral CSV por filtros, após a criação de vínculos pela UI. Consulte o [relatório da rodada](testing/people-export-2026-10-27-report.md). A auditoria n8n da rodada anterior continua vigente e bloqueante. Não há uma nova fase numerada ou aceite presumido. O aceite final da Fase 9 continua pendente; isso não libera produção/publicação. Capturas reais, n8n, Power BI Desktop e lacunas funcionais/operacionais constam de docs/release/status.json. Não houve publicação.

| Fase | Entregável | Estimativa inicial | Condição de saída |
|---|---|---|---|
| 1 | Planejamento, modelo, regras/solver especificados, prompt consolidado, fixture e execução mínima | 1–2 | Documentos/fixture validados, API integrada e build inicial verificados |
| 2 | PostgreSQL/SQLite leve, migrations, autenticação/RBAC, entidades e seed | 4–6 | Persistência, login e isolamento comprovados; plano abaixo |
| 3 | Identidade final, layout, gestão, dashboard conectado | 4–6 | Formulários/navegação/filtros e números reconciliados com API |
| 4 | Jornadas, calendário, LaborRules e alertas | 5–8 | Vigências, descansos, escopo e mudanças manuais testados |
| 5 | Simulação de capacidade, cenários e financeiro | 4–6 | Premissas rastreáveis, cálculos e comparações testados |
| 6 | CP-SAT, worker, diagnóstico e aprovação | 6–10 | Viável/inviável, pausas/habilitações/24x7 e decisão versionada comprovados |
| 7 | Scheduler, eventos, notificações e workflows n8n | 4–6 | Execução real, deduplicação, falhas e retentativas verificadas |
| 8 | Analytics, CSV/XLSX, Power BI, IA explicativa opcional | 3–5 | Exportações reconciliadas; métricas reproduzíveis e fallback gratuito |
| 9 | Segurança, qualidade e fluxo integrado | 4–7 | Testes de autorização, integração, navegador e recuperação aprovados |
| 10 | Documentação final, screenshots, caso e release Chronos 1.0 | 2–4 | Relatório de validação e revisão; publicação exige autorização |

## Plano concreto da Fase 2

Plano abaixo executado no checkpoint da Fase 2. Escopo e limitações reais estão no relatório, incluindo o frontend ainda referente à Fase 1.

1. Configuração tipada por ambiente, conexão SQLAlchemy, PostgreSQL principal e SQLite opt-in fora do OneDrive. Preparar Compose somente para os serviços necessários; sem exigir n8n/Redis.
2. Migrations Alembic em ordem: tenant/identidade/RBAC → organização/unidades/setores/cargos → competências/qualificações → pessoas/contratos/disponibilidade. Validar upgrade/downgrade e constraints.
3. Senhas Argon2id, JWT/refresh, rate limiting de login, seis perfis e resolução do tenant pelo principal. Testes de acesso negado e de IDs cruzados em leitura/escrita.
4. Repositórios/casos de uso com transação, auditoria, paginação, filtros/ordenação e erros correlacionados. Endpoints `/auth`, `/organizations`, `/units`, `/departments`, `/employees` e catálogos necessários.
5. Importador idempotente da fixture com mapeamento de IDs; 350 pessoas em 19 setores, contratos e habilitações. Restauração apenas em banco marcado demo, explícita e protegida; nunca em produção.
6. Testes backend de persistência, RBAC e validação; integration em PostgreSQL real, rollback, conflitos de versão e restauração. SQLite não basta para atestar PostgreSQL.
7. Documentar configuração, comandos e contratos OpenAPI; manter o checkpoint executável. Nenhum solver ou workflow será marcado pronto nessa fase.

## Aceite da Fase 2

Reinício mantém registros; seed repetida não duplica; relações de tenants diferentes são rejeitadas; credenciais inválidas/expiradas e papéis insuficientes retornam erro adequado; dados financeiros não são expostos a perfis sem permissão; migrations executam em banco vazio e existente de teste; rollback é demonstrado; endpoints protegidos e documentação correspondem ao comportamento real. Se PostgreSQL/Docker não estiver disponível, registrar pendência e não declarar essa integração concluída.

## Plano concreto da Fase 3 — Frontend

Implementado no checkpoint da Fase 3. Limites de navegação visual e operações adicionais estão no relatório específico.

1. Implementar login/logout e estado de sessão seguro, guardas de rota e tratamento de 401/403; não guardar credenciais no localStorage. Definir refresh em cookie HttpOnly/CSRF ou BFF antes de habilitar renovação automática no navegador.
2. Conectar o dashboard à API persistente. Mostrar origem/período dos dados e estados vazios/erro; remover dependência da fixture pública nas telas operacionais. Cobertura/custos/conformidade ainda não calculados ficam explicitamente indisponíveis.
3. Criar componentes e layout com Tailwind, RHF/Zod nos formulários e TanStack Query para paginação, filtros, atualização de cache e conflitos de revisão.
4. Implementar telas de colaboradores, setores, unidades, catálogos e acessos autorizados. Completar as operações de edição/transferência que essas telas exigirem, com mesmas garantias de tenant, integridade e escopo no backend.
5. Testar login, navegação, formulários, validação, restrições de papel/unidade, erro de rede, edição concorrente, teclado e responsividade. Fazer navegação real se a ferramenta permitir; registrar limitações sem contornar bloqueios.
6. Atualizar documentação e roteiro de demonstração. Não iniciar calendário/LaborRules, simulador ou solver nesta fase.

## Plano concreto da Fase 4 — Jornadas, calendário e LaborRules

1. Consultar novamente as fontes normativas oficiais e instrumentos aplicáveis. Resolver vigências e exceções antes da ativação; regras sem revisão ficam pendentes, sem certificação jurídica.
2. Implementar migrations e modelos de jornadas, turnos/pausas, calendários, ausências e regras versionadas com escopo de organização/unidade/categoria/contrato/acordo.
3. Implementar cálculos determinísticos de duração, virada de dia, descanso intrajornada/interjornada e limites por janela. Preservar histórico nas bordas do período e diferenças entre tempo real e remunerável.
4. Criar calendário semanal/mensal conectado à API, com ajustes manuais autorizados e avaliação antes de confirmar. Atualização de regra não altera silenciosamente uma versão aprovada.
5. Emitir os quatro resultados de conformidade previstos, com evidência/fonte/versão e alertas claros. 5x2, 4x3, 12x36, plantões e regimes especiais não são liberados apenas pelo nome.
6. Testar vigências, fronteiras temporais, descanso, indisponibilidade, escopos, regras ausentes, conflito entre fontes e edição de calendário. Revisar visualmente a interface quando a ferramenta permitir, preservando os limites já registrados.
7. Atualizar documentação e roteiro. Não implementar simulador financeiro, solver ou n8n nesta fase.

## Plano concreto da Fase 5 — Simuladores e financeiro

1. Versionar cenários e premissas de demanda/capacidade, com unidade, atividade, competência, vigência, fonte e responsável; nenhum quantitativo hospitalar universal.
2. Simular jornadas e ciclos por população elegível, confrontando disponibilidade/carga e requisitos, com hipóteses pendentes explicitadas. Reutilizar LaborRules e seus snapshots; não confundir capacidade agregada com uma escala viável.
3. Implementar cálculos monetários exatos em centavos/Decimal: folha-base, encargos parametrizados, adicionais, horas extras, contratações e custos de transição. Separar horas reais de remuneráveis, respeitar condição de aplicação de cada parcela.
4. Comparar cenários com manutenção salarial e fontes rastreáveis; exibir impacto, limitações e sensibilidade das premissas. Não inventar convenções, alíquotas ou pisos profissionais.
5. Telas de simulação e comparativos ligadas à API com permissões financeiras; teste de arredondamento, vigência, casos-limite, isolamento, reconciliação e reprodutibilidade.
6. Atualizar documentação e roteiro. OR-Tools/aprovações permanecem na Fase 6; n8n na Fase 7; nenhuma publicação sem autorização.

## Plano concreto da Fase 6 — Otimização e aprovação

1. Implementar OR-Tools CP-SAT e execução em worker com status, cancelamento, limites, seed e versão dos insumos. Validar compatibilidade do runtime e dependências antes de instalar.
2. Converter demanda por intervalo/atividade em postos, considerando simultaneidade, competências, habilitações, indisponibilidade, pausas e descanso; preservar contexto fora do horizonte. Usar quantitativos parametrizados e fontes profissionais aplicáveis.
3. Integrar contratos e LaborRules sem transformar limites pendentes em regras jurídicas aprovadas. Diferenciar hipóteses, solução viável e escala juridicamente revisada; diagnosticar inviabilidade e lacunas obrigatórias.
4. Separar restrições obrigatórias de preferências e objetivos (custos, equilíbrio de plantões, continuidade, substituições); persistir modelo/solução/diagnóstico reproduzível por versão.
5. Implementar revisão/submissão/aprovação com hash completo de insumos, escopos e transação; mudança de dado relevante exige nova versão. Publicação externa continua dependente de autorização explícita.
6. Testar viabilidade/inviabilidade, cobertura 24x7, pausas/habilitações, alteração concorrente, recuperação de job e decisões. n8n/scheduler permanecem na Fase 7.

## Plano concreto da Fase 7 — Automações e n8n

1. Implementar eventos/outbox transacionais e execuções persistentes com responsável, origem, estado, tentativas, erro seguro, idempotência e trilha auditável.
2. Adicionar scheduler local opcional e rotinas A01–A07 conforme processos: revisão de vigências, cobertura, pendências, relatórios e reotimização assistida. Não revisar regras nem aprovar propostas automaticamente.
3. Criar workflows n8n exportáveis com autenticação, deduplicação, retentativas, timeout e falha explícita. O núcleo deve funcionar sem n8n.
4. Expor central de automações e histórico por papel/unidade. Destinos externos e notificações reais exigem autorização; usar receptores de teste locais para validar transporte.
5. Testar reinício/recuperação, concorrência, replay, falha temporária/permanente, escopos e workflows efetivamente importados/executados. Não declarar integração pronta apenas por JSON presente.
6. Atualizar documentação e evidências. Manter versão Chronos 1.0, sem publicação externa e sem alterações em outros projetos.

## Plano concreto da Fase 8 — Analytics, exportações e explicações

1. Ampliar analytics com fontes/períodos, filtros, histórico e métricas reconciliadas de jornadas, cobertura, custos e execuções. Distinguir estimativas de resultados observados; não alegar ganho de mercado sem medição.
2. Exportar CSV/XLSX de cenários/propostas/resultados, com grão e versões identificados, proteção contra fórmulas, limites e autorização por campo/unidade.
3. Preparar dataset e documentação Power BI: dimensões, fatos, relacionamentos, atualização e segurança. Não publicar em conta/cloud nem embutir credenciais sem autorização.
4. Implementar explicações determinísticas gratuitas e, se aplicável, adaptador de IA opcional desacoplado. Nenhuma IA decide validade jurídica, cálculo financeiro ou restrições do solver; serviços externos permanecem desativados por padrão.
5. Testar reconciliação, fronteiras temporais, permissões, arquivos efetivamente abertos/recalculados e isolamento das explicações. Preservar as pendências de QA visual e de segurança para revisão integrada.
6. Atualizar documentação e evidências. A versão continua Chronos 1.0; publicação externa segue dependente de autorização.

## Plano concreto da Fase 9 — Segurança, qualidade e fluxo integrado

1. Revisar autorização por tenant/unidade/campo, sessões, cookies/CSRF, recuperação, limites e auditoria em todos os módulos, incluindo arquivos e sugestões.
2. Exercitar o fluxo integrado: cadastros/revisões → cenário → projeção → solver → revisão/decisão → automações → analytics/exportação. Preservar snapshots e trilhas; nenhum ganho ou aprovação implícita.
3. Validar backup/restauração em cópia isolada, falhas/reinício e recuperação de filas. Proteger dados de demonstração e segredos locais.
4. Revisar dependências e configurações de desenvolvimento/produção, sem ativar serviços externos nem publicar. Documentar riscos confirmados e correções.
5. Executar QA real de navegador, teclado, responsividade e temas quando o ambiente permitir. O bloqueio de automação visual anterior não deve ser contornado; registrar a pendência se persistir.
6. Conferir exportações no Excel e preparação Power BI no aplicativo nativo quando disponível, distinguindo esses controles do recálculo já realizado pela ferramenta de artefatos.
7. Consolidar evidências e limites; não declarar pronto para produção nem iniciar publicação da Fase 10 sem revisão e autorização.

## Plano concreto da Fase 10 — Entrega para revisão

1. Consolidar manual, instalação/operação, roteiro de demonstração, estudo de caso e mapa de requisitos com estados parciais/bloqueados explícitos.
2. Medir microensaio reproduzível entre política manual simulada em código e solver, com mesmos insumos/verificador, unidades/hashes e sem ganho humano inventado.
3. Preparar plano de screenshots. Manter capturas/QA pendentes enquanto persistir o bloqueio de navegador; não fabricar imagens.
4. Gerar pacote local de revisão com fontes/build/fixture/documentos, exclusões de segredos/runtimes/bancos e manifesto/hashes verificados.
5. Registrar testes da preparação separadamente das evidências históricas do núcleo. Conservar nome oficial Chronos 1.0 em UTF-8 e flags de publicação/liberação falsas.
6. Antes do aceite final, resolver bloqueios e revisar lacunas funcionais/operacionais. Publicar somente com autorização explícita de conteúdo e destino; nenhuma aprovação é presumida pela preparação do ZIP.
