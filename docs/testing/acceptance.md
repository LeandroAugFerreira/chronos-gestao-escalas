# Chronos 1.0 — Critérios e estratégia de testes

Checkpoint atual: Fase 3. Cobertura executada e resultados em `phase3-report.md`; relatórios das fases anteriores permanecem históricos. Interface foi testada por componentes/HTTP; revisão visual de navegador permanece pendente. Solver, regras e automações seguem nas fases correspondentes.

## Fase 1

- Prompt consolidado com as 25 seções originais e controle da atualização, hashes de origem/saída, identidade Chronos 1.0 e cliente atualizado.
- Arquitetura modular, banco/tenancy, motor de regras, CP-SAT, financeiro, automações, requisitos, cronograma e Fase 2 documentados.
- Fixture reproduzível com 350 pessoas, 19 setores, funções, competências, qualificações, contratos e disponibilidade; nenhuma comprovação de dimensionamento clínico.
- API real de leitura; OpenAPI com versão 1.0; erros seguros; CORS restrito; nenhum endpoint de pessoas sem autenticação.
- Frontend React/TS compila, consulta a API, filtra setores, navega e persiste tema; falha de API visível.
- Critérios operacionais de cobertura/conformidade/otimização explicitamente não avaliados nesta fase.

## Fases seguintes

Backend: regras de negócio, duração/virada de dia, vigências, intervalos/descansos, custos exatos, API, RBAC, tenant e persistência. Otimização: ótimo conhecido, viável, inviável, limites rígidos, competências/habilitações, pausas, demanda e continuidade 24x7, preferências, múltiplas unidades e reprodutibilidade. Frontend: formulários, navegação, filtros/paginação, calendário, simulação, aprovação, falha de rede, teclado e responsividade. Integração: banco/API/UI, worker, scheduler, workflows e recuperação de falhas.

Fluxo E2E final: Login → carregar empresa → escala atual → cenário → otimização → resultados → submissão → aprovação → publicação interna fictícia → dashboard. O fluxo não é aceito com botões estáticos ou testes que só verificam arquivos.

Casos sintéticos preservados: escala válida; lacuna; indisponível; conflito de descanso; excesso semanal; contratação; fim de semana; feriado; 42h; 40h; 4x3 hipotética; mudança por vigência; integração falha; reprocessamento; acesso não autorizado. Novos casos: 12x36 sem acordo aplicável, qualificação expirada, passagem de plantão, substituição indevida e continuidade 24 horas.

## Medições de portfólio

Registrar tempo total e do solver, conflitos, cobertura por minutos-posto, quantidade de propostas viáveis, custo, intervenções humanas, automações bem-sucedidas/tentadas, tempo de importação e quantidade de avaliações de regras. Comparar processo manual **simulado** com metodologia/entradas iguais e hardware/seed registrados. Nenhum ganho de produtividade será alegado antes da medição.

O relatório desta fase separa executado/aprovado, falhou/corrigido e não executado. Testes futuros descritos aqui não contam como aprovação atual.

## Checkpoint da Fase 9

A revisão técnica e os testes do núcleo estão registrados em [phase9-report.md](phase9-report.md). A partida n8n segue bloqueada por avisos de dependências não remediados; QA de navegador e Power BI Desktop permanecem pendentes. Excel nativo foi conferido em somente leitura. O checkpoint não equivale ao aceite final de produção nem autoriza publicar.
