# Chronos — estudo de caso verificável para Desenvolvedor Full Stack/Python

**Natureza:** aplicação autoral demonstrativa. Hospital Horizonte é organização **inteiramente fictícia** (350 colaboradores, 19 setores) para explorar jornadas, competências, disponibilidade e custos; não é implantação hospitalar.

## Resumo para recrutador (30 segundos)

O Chronos transforma premissas de demanda e disponibilidade em cenários versionados para revisão de escalas. Usa Python/FastAPI, React/TypeScript, SQLAlchemy, Alembic e OR-Tools CP-SAT para calcular alternativas sujeitas a regras configuradas. O solver não toma decisões sozinho: resultados passam por verificador independente e aprovação de outra pessoa antes de serem considerados aprovados.

## Problema e usuários

**Problema:** calendários, ausências, competências, contratos e hipóteses de custo são interdependentes. Um planejamento não rastreável pode esconder lacunas de cobertura ou a origem de uma decisão.

**Usuários previstos no código:** administrador, RH, gestor, financeiro, analista e consulta demonstrativa, com permissões por função e, quando aplicável, por unidade. Usuários de demonstração não podem ver informações de pessoal individual, salários ou executar mudanças.

**Critério de sucesso de engenharia:** produzir propostas cujas entradas, limitações e decisões possam ser auditadas, sem apresentar cálculos como conformidade legal por padrão.

## Requisitos e componentes efetivos

- Estrutura: unidades, setores, funções, competências, pessoas e contratos com vigências.
- Jornadas: calendário, disponibilidade, limites diários/semanais, repousos e competências.
- Cenários: snapshots/digests, comparação, projeção financeira hipotética e séries de consulta.
- Otimização: modelo CP-SAT, verificação independente, modos estrito/diagnóstico, lacunas explícitas.
- Governança: proposta, revisão, regras para aprovação por outro ator, trilha auditável e histórico.
- Interface: dashboards, fluxos de planejamento, tema claro/escuro e navegação por permissões.
- Automação: rotinas locais com outbox/retentativas; integração n8n permanece bloqueada.

Código de apoio: [API](../../backend/app/api), [services](../../backend/app/services), [frontend](../../frontend/src), [modelo](../../backend/app/models/entities.py), [cobertura de requisitos](../portfolio/coverage.md).

## Stack e responsabilidades

| Camada | Escolha | Papel |
| --- | --- | --- |
| Frontend | React, TypeScript, Vite, React Query, Zod | Formulários, navegação, estado assíncrono e visualização |
| Backend | FastAPI, Pydantic | Validação, autorização, orquestração de casos de uso |
| Persistência | SQLAlchemy, Alembic, PostgreSQL/SQLite opcional | Histórico, escopos, versões, idempotência |
| Otimização | OR-Tools CP-SAT | Construir alternativas sujeitas a restrições e objetivos |
| Integridade | Verificador independente, hash/digest, auditoria | Checagem do resultado antes da decisão |
| Segurança | Argon2id, JWT, refresh HttpOnly e CSRF | Autenticação, sessão, política de privilégios |
| QA | pytest, Vitest, CI e smoke Chromium | Regressão e evidência reproduzível |

## Regra central para explicar na entrevista

**O solver não aprova escalas.** Uma entrada de cenário gera snapshot. O CP-SAT retorna atribuições/estado de solução; um verificador distinto checa restrições; premissas sem revisão e demanda descoberta impedem aprovação. Uma proposta deve ser submetida e aprovada por outro usuário autorizado. Se a origem mudar, o digest deixa de corresponder e a aprovação é recusada.

Referências: [optimizer.py](../../backend/app/services/optimizer.py), [optimization.py](../../backend/app/api/optimization.py), [optimization_snapshot.py](../../backend/app/services/optimization_snapshot.py).

## Um benchmark sem alegações infladas

O benchmark de [2026 no repositório](../portfolio/benchmark.json), baseado na [fixture](../../data/synthetic/portfolio_benchmark.json), avalia **uma atividade em um único dia**. Três repetições, seed 1042 e um único worker; custos por turno de R$ 480 são hipotéticos.

| População fictícia | First-fit | Solver Chronos | Interpretação |
| --- | --- | --- | --- |
| 3 profissionais | 1.440/1.440 postos-minuto; R$ 1.440 imputados | Mesma cobertura/custo | Ambos resolvem o caso pequeno |
| 2 profissionais | 960/1.440, lacuna 480; R$ 960 imputados | Mesma cobertura/custo e lacuna | Menor custo decorre de escala incompleta, não economia |

**Não há ganho humano medido.** A marca OPTIMAL no modo diagnóstico não afirma cobertura completa. Nenhum percentual de produtividade, ROI, salário observado ou dimensionamento clínico decorre dessa amostra.

## Demonstração para entrevistas

1. Abrir [tour estático de benchmark](https://leandroaugferreira.github.io/chronos-demo.html) (quando publicado): alterar 3→2 e explicar que a lacuna precisa aparecer.
2. Mostrar [benchmark.json](../portfolio/benchmark.json), [fixture](../../data/synthetic/portfolio_benchmark.json) e [teste de evidência](../../backend/tests/test_recruiting_evidence.py).
3. Mostrar arquitetura e verificador OR-Tools; explicar o que acontece quando uma regra impede a cobertura.
4. Abrir evidência de testes no Actions e apontar limitações. **Não** chamar tour de “solver online”.

## Desafios de engenharia visíveis no código

- Modelar elegibilidade em presença de competências, vínculos, regras vigentes e diferentes unidades.
- Evitar que otimização em background perca vínculo com as entradas que foram aprovadas.
- Garantir segregação entre criador da proposta e aprovador.
- Evitar vazamento de registros individuais na consulta agregada.
- Garantir que orçamento hipotético, cobertura parcial e regras “validadas na fixture” não sejam interpretados como validade legal.

**Nota de autoria:** isso descreve problemas tratados pelo sistema, não comprova histórias pessoais de debugging. Antes da entrevista, o autor deve registrar um problema que realmente enfrentou e como o investigou; não inventar incidentes.

## Limites e próximos passos

Ainda faltam habilitação segura de n8n, homologação PostgreSQL recente, validação completa de navegador/acessibilidade, Power BI Desktop nativo, infraestrutura/controle de produção e validações legais específicas. É inadequado promover o produto a serviço clínico ou trabalhista homologado sem essas etapas.

[Auditoria](AUDITORIA.md) · [Arquitetura](ARQUITETURA.md) · [Roteiro de demo](ROTEIRO_DEMO.md) · [Perguntas técnicas](ENTREVISTA_TECNICA.md).
