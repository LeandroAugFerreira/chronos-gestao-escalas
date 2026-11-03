# Chronos 1.0 — Requisitos e rastreabilidade

Nome oficial: **Chronos — Gestão Inteligente de Jornadas e Escalas**. Identificação de entrega: **Chronos 1.0**. Data-base: 24/10/2026, America/Sao_Paulo.

O Prompt Mestre consolidado é a especificação completa. Este documento organiza sua implementação; não elimina exigências. O produto é multissegmento e o cliente de demonstração é fictício. Nenhum atendimento clínico, dado de paciente ou dado real de trabalhador é necessário.

## Escopo por módulo

| ID | Módulo e resultado exigido | Fases | Verificação de aceite |
|---|---|---|---|
| RF01 | Dashboard com pessoal, unidades, jornadas, pendências, horas, demanda, cobertura, custos e automações; gráficos de distribuição e evolução | 3, 5, 8 | Totais reconciliados com consultas do banco/API e filtros; nenhum indicador operacional fixo no frontend |
| RF02 | Organizações, unidades, setores, funções, centros de custo, funcionamento e equipes configuráveis | 2, 3 | CRUD persistido com integridade referencial e isolamento entre organizações |
| RF03 | Colaboradores, contratos, competências, qualificações com validade, disponibilidade, restrições, preferências; busca/importação/exportação | 2, 3 | Importação transacional, validação por linha, paginação, exportação autorizada e dados exclusivamente fictícios |
| RF04 | 5x2, 4x3, 12x36, plantões, diurno/noturno, administrativo, regimes especiais, revezamento e personalizados; 6x1 histórica/exceção fundamentada | 4 | Calendário semanal/mensal, intervalos e ausências; mudança manual autorizada revalidada; nenhuma modalidade liberada apenas pelo nome |
| RF05 | Cenários independentes: referência 44h, hipóteses 42h/40h, 4x3 e personalizados; capacidade, déficit, lacunas, riscos e comparação | 5 | Mesma entrada produz mesmos cálculos; estimativa por horas não é contratação definitiva |
| RF06 | OR-Tools CP-SAT: pessoas habilitadas, demanda por intervalo, restrições contratuais/legais, descansos, indisponibilidade, substituições, continuidade, equilíbrio de plantões | 6 | Soluções viáveis e inviáveis; lacunas explícitas; solver não relaxa restrições de habilitação ou descanso |
| RF07 | Simulador financeiro: salários, benefícios, encargos, adicionais, extras, contratação, treinamento, produtividade/retrabalho simulados | 5 | Decimal/centavos; premissas e origens separadas dos resultados; comparação mensal/anual e cenários de teste |
| RF08 | Central de automações A01–A07: verificações, cobertura, aprovação, relatórios, vigência, reotimização assistida, auditoria | 7 | Execução real com histórico, responsável, tentativas, erro e estado; funciona sem n8n |
| RF09 | Rascunho → Em análise → Aprovado → Publicado; rejeição, cancelamento e substituição versionada | 6 | Decisão com ator/data/justificativa; aprovação vinculada ao hash exato da versão; publicação interna fictícia explícita |
| RF10 | Analytics, filtros, histórico, comparações, exportação CSV/XLSX e dataset Power BI | 8 | Exportação reconciliada com o cenário; metodologia reproduzível; ganhos simulados identificados |
| RF11 | LaborRules: fontes, dispositivos, vigência, categoria, acordo, versão, validação, exceção e histórico | 4 | Quatro classificações de conformidade; regra sem aplicabilidade não gera aprovação automática |
| RF12 | Administração, usuários, seis perfis, RBAC, integrações, notificações e auditoria | 2–9 | Permissões efetivas na API, isolamento entre organizações, trilha de operações críticas |
| RF13 | IA explicativa opcional e desacoplada, fallback determinístico gratuito | 8 | Sem dependência de Ollama/serviço pago; nenhuma IA decide cálculo ou validade de regra |
| RF14 | Workflows n8n exportáveis e autenticados: escala pendente, cobertura, relatório, disponibilidade | 7 | JSON importado e executado em ambiente de teste; idempotência, retentativas e falha de integração exercitadas |

## Requisitos não funcionais

| ID | Exigência verificável |
|---|---|
| RNF01 | Python/FastAPI/Pydantic, SQLAlchemy/Alembic/PostgreSQL; React/TypeScript/Vite/Router/Query; Tailwind, RHF/Zod, Recharts ou Plotly nas telas que os exigirem |
| RNF02 | Monólito modular; regras, matemática, financeiro e automações desacoplados da API e do segmento hospitalar |
| RNF03 | JWT, hash de senha seguro, RBAC no servidor, escopo obrigatório de organização, validação de entrada e CORS explícito |
| RNF04 | Minimização LGPD; sem CPF, paciente ou motivo médico; retenção/exclusão documentadas; segredos apenas no ambiente |
| RNF05 | UTC nos instantes persistidos, fuso da unidade nos cálculos de dia/semana, turnos atravessando meia-noite, minutos inteiros e valores monetários exatos |
| RNF06 | Auditoria, correlation_id, idempotência, exceções sem segredos, tarefas longas em worker; sem dupla execução após retentativa |
| RNF07 | Dark inicial, light persistido, identidade temporal abstrata, responsividade e acessibilidade por teclado/contraste; sem símbolo médico na marca |
| RNF08 | Execução leve no Windows, sem instalação global; caches, venv e bancos ativos fora do OneDrive; Docker Compose opcional |
| RNF09 | Testes executados por fase, reprodutibilidade de dados/solver, métricas medidas; não declarar recurso concluído por presença de arquivo |
| RNF10 | Nenhum deploy, repositório remoto, integração com custo ou envio externo sem autorização; trabalho limitado à pasta Chronos |
| RNF11 | Paginação, filtros, ordenação, OpenAPI, erros padronizados; logs operacionais com política de retenção configurável |

## Cenário Hospital Horizonte

Uma organização, uma unidade principal e 350 pessoas com lotação única. Os 19 setores incluem áreas assistenciais, administrativas e operacionais. Enfermagem é um setor de apoio e também um conjunto de funções em outros setores; nenhuma pessoa é contada duas vezes. Credenciais são fictícias, sem números reais de conselhos.

O funcionamento hospitalar é 24x7; cada setor tem horário e demanda próprios. Requisitos de dimensionamento são parametrizáveis por atividade, competência, qualificação, localidade, intervalo e fonte. Os quantitativos da fixture são premissas de teste, sem validade normativa e sem comprovação de cobertura.

Outros segmentos previstos: hospitais/clínicas, supermercados, indústrias, logística, hotéis, restaurantes, segurança, call centers, ensino e serviços. Não haverá enumeração de setores hospitalares no núcleo do domínio.

## Limite deste checkpoint

A Fase 1 entregou documentação, fixture reproduzível e integração mínima de leitura. A Fase 2 acrescentou persistência, migrations, autenticação/RBAC e cadastros protegidos. A Fase 3 implementou login/sessão web, dashboard do banco e telas de gestão, com testes de componentes/HTTP e inspeção visual ainda pendente. A Fase 4 acrescentou calendário semanal/mensal, rascunhos/pausas, indisponibilidade, prévia obrigatória, regras tipadas versionadas e histórico de avaliação. As avaliações limitam-se aos critérios configurados e ao planejamento conhecido, sem certificação jurídica. A Fase 5 acrescentou cenários versionados, capacidade agregada, demanda parametrizada e projeções financeiras de 12 meses com comparativos/sensibilidade. A Fase 6 acrescentou CP-SAT, fila/worker local, diagnóstico de lacunas, propostas imutáveis, revisões individuais e decisões internas com insumos conferidos e segundo responsável. A Fase 7 acrescentou outbox transacional, rotinas A01–A07, consumidor/scheduler local opcional, alertas, CSV de indicadores, sugestões de recálculo e quatro workflows n8n realmente executados em loopback. Não há aprovação ou ativação de regras automáticas. A Fase 8 acrescentou analytics por versão, CSV/XLSX autorizados, preparação local de dataset Power BI e explicações determinísticas gratuitas. A Fase 9 acrescentou limites/configuração de segurança, revisão persistente de jornadas e recuperação/fluxo integrado validados. Aceite final continua pendente por bloqueio de dependências n8n, QA de navegador e execução no Power BI Desktop; Excel nativo foi conferido em somente leitura. Nenhuma publicação externa foi realizada. Limites concretos estão em docs/architecture/phase6.md, phase7.md e phase8.md.
