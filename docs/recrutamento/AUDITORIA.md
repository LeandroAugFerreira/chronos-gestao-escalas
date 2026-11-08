# Auditoria técnica de recrutamento — Chronos 1.0

**Escopo:** leitura estática do código-fonte no commit inicial `fdc0ba5a8ca9fc2b2b5ec14fa7d08f1a68603ce3` (08/11/2026), mais verificação automatizada posterior nesta branch. **Não é pentest, certificação jurídica, auditoria de produção ou verificação de todas as telas.**

## Parecer para recrutadores

Chronos é um projeto autoral de grande escopo, voltado a cenários de jornada e escalas, com modelagem de pessoas, contratos, competências, disponibilidade, custo hipotético, otimização CP-SAT e governança por segundo aprovador. O principal diferencial é **separar cálculo, validação independente, proposta versionada e decisão humana**.

O volume de código e testes evidencia amplitude, mas exige explicar claramente quais recursos estão prontos para demonstração, quais são simulados e quais **não** foram homologados. A amplitude não significa produto pronto para hospital real.

## Inventário inspecionado

- **API:** [main.py](../../backend/app/main.py), [auth.py](../../backend/app/api/auth.py), [browser_session.py](../../backend/app/api/browser_session.py), [dependencies.py](../../backend/app/api/dependencies.py), [optimization.py](../../backend/app/api/optimization.py), [scheduling.py](../../backend/app/api/scheduling.py), [simulation.py](../../backend/app/api/simulation.py), [analytics.py](../../backend/app/api/analytics.py).
- **Núcleo:** [optimizer.py](../../backend/app/services/optimizer.py), [optimization_snapshot.py](../../backend/app/services/optimization_snapshot.py), [optimization_worker.py](../../backend/app/services/optimization_worker.py), [seed.py](../../backend/app/services/seed.py), [security.py](../../backend/app/core/security.py), [config.py](../../backend/app/core/config.py), [database.py](../../backend/app/core/database.py), [entities.py](../../backend/app/models/entities.py).
- **Frontend:** [app.tsx](../../frontend/src/app.tsx), [login.tsx](../../frontend/src/pages/login.tsx), [optimization.tsx](../../frontend/src/pages/optimization.tsx), [overview.tsx](../../frontend/src/pages/overview.tsx), [client.ts](../../frontend/src/services/client.ts).
- **Testes e CI:** [test_optimizer.py](../../backend/tests/test_optimizer.py), [test_phase2.py](../../backend/tests/test_phase2.py), [test_phase7.py](../../backend/tests/test_phase7.py), [test_phase10.py](../../backend/tests/test_phase10.py), [workflow](../../.github/workflows/tests.yml) e [validação histórica](../github/VALIDACAO.md).
- **Estudo quantitativo:** [case-study.md](../portfolio/case-study.md), [benchmark.json](../portfolio/benchmark.json), [fixture sintética](../../data/synthetic/portfolio_benchmark.json), [portfolio_benchmark.py](../../backend/scripts/portfolio_benchmark.py).
- **Restrições:** [coverage.md](../portfolio/coverage.md), [security/phase9-findings.md](../security/phase9-findings.md).

A inspeção não cobriu linha a linha todos os arquivos, binários Windows, dependências transitivas ou configuração de serviços em produção.

## Arquitetura implementada

- Interface React/TypeScript/Vite com React Query e formulários validados, acessando a API via cliente HTTP e sessão do navegador.
- Backend FastAPI/Pydantic em módulos de recursos, calendário, cenários, finanças, otimização, analytics, autenticação e automação.
- SQLAlchemy + Alembic; banco preferencial PostgreSQL e **SQLite local explicitamente autorizado** para demonstração/testes.
- Solver OR-Tools CP-SAT em worker separado: recebe snapshot de entradas, aplica elegibilidade, limites, pausas, repousos, demanda e objetivos; verificador separado revisa resultados.
- Propostas com digest, revisão e segunda pessoa aprovadora. Resultados não equivalem a publicação automática de escala.
- n8n opcional: arquivos e contratos presentes; **execução bloqueada na configuração de desenvolvimento** após auditoria de dependências. Não ativar nesse ciclo.

## Fluxo principal auditado

1. Unidade/setor, contratos e qualificações formam o contexto de planejamento e os escopos do usuário.
2. Cenário é registrado como versão com demanda e hipóteses; validações de campo e permissões ocorrem no backend.
3. Solicitação de otimização captura snapshot assinado e enfileira trabalho para o worker, que executa CP-SAT com limites e seed.
4. Verificador independente reavalia cobertura e restrições; uma lacuna de demanda é relatada, não ocultada.
5. Proposta produzida exige transições válidas; o próprio autor do cálculo não pode aprovar sua proposta; mudanças de entrada invalidam aprovação anterior.
6. Analytics e projeções consultam versões e controlam acesso a campos de pessoal/finanças.

**Limites de prova:** o backend/testes sustentam regras, mas uma implantação hospitalar real, dimensionamento clínico, conformidade trabalhista ou ganhos de produtividade **não** foram demonstrados.

## Segurança e governança: pontos concretos

- [security.py](../../backend/app/core/security.py): Argon2id para senhas, JWT com expiração/issuer/audience e refresh token aleatório armazenado somente por hash.
- [browser_session.py](../../backend/app/api/browser_session.py): cookies de refresh HttpOnly/SameSite strict, CSRF assinado ligado à família de sessão e validação de origem.
- [dependencies.py](../../backend/app/api/dependencies.py): checa sessão ativa, papéis com escopo por unidade e permissão, e não amplia uma permissão pelo escopo de outra.
- [config.py](../../backend/app/core/config.py): em produção exige segredo, banco, cookie Secure/origens HTTPS e bloqueia SQLite; não gera fallback de segredo.
- [optimization.py](../../backend/app/api/optimization.py): segundo aprovador e digest de entradas/proposta são validados antes da aprovação.
- [request_limits.py](../../backend/app/core/request_limits.py): limite HTTP e cabeçalhos de segurança.
- [phase9-findings.md](../security/phase9-findings.md): bloqueio conhecido do n8n com dependências vulneráveis. **Este projeto não deve desativar o bloqueio por conveniência de uma demo.**

Esses controles não equivalem a pentest, varredura atualizada de toda a árvore de dependências, política de retenção de pessoas, compliance ou liberação pública.

## Constatações de melhoria

| Prioridade | Observação fundamentada | Medida |
| --- | --- | --- |
| Alta | Demonstração de navegador ainda era uma lacuna da preparação original | Adicionar smoke com Chromium, banco temporário, fixture sintética e credenciais aleatórias |
| Alta | Microensaio first-fit versus CP-SAT pode ser erroneamente apresentado como economia | Teste reproduzível e divulgação explícita dos empates/lacunas |
| Alta | n8n bloqueado pelo status de dependências | Preservar bloqueio; revisão de segurança independente antes de eventual reativação |
| Alta | Não há liberação de produção/validação jurídica ou clínica | Não reivindicar conformidade, economia ou operação real |
| Média | Configuração demo local depende de setup/credenciais geradas | Tour web **estático**, sem backend, contas ou banco público |
| Média | PostgreSQL não foi rehomologado nesta execução por ausência de banco descartável | Testar migrações/isolamento em PostgreSQL efêmero antes da produção |
| Média | QA visual, teclado, responsividade e todos os fluxos não são exaustivos | Ampliar E2E gradualmente, com capturas e critérios verificáveis |
| Média | Referências antigas de fases/release e manuais podem divergir do código atual | Consolidar as evidências novas sem apagar o histórico |
| Média | Power BI Desktop, importação nativa e DAX não homologados | Tratar como preparação de dataset, não dashboard Power BI completo |

## Implementado, sintético e pendente

| Capacidade | Situação |
| --- | --- |
| Cadastro de unidades, departamentos, funcionários, competências, jornadas | Código real + testes de API/integração |
| Cenários, simulação financeira, comparação e rastreabilidade | Código real + testes, com valores hipotéticos |
| Otimização CP-SAT, verificador independente e bloqueios | Código real + testes; critérios jurídicos não certificados |
| Proposta, revisão por outro responsável, auditoria | Código real + testes de governança |
| Automação interna local | Código real + testes; rotinas externas desativadas por padrão |
| n8n | Integração opcional presente, **bloqueada por segurança** |
| Hospital Horizonte 350 pessoas, 19 setores | **Fixture inteiramente fictícia**, não cliente |
| Microbenchmark 3/2 profissionais | Evidência histórica reproduzível de **uma atividade/um dia**, sem superioridade observada no caso pequeno |
| Publicação da API na internet e operação real | **Não implantado/comprovado** |
| Conformidade trabalhista, adequação clínica, ROI | **Não comprovado** |

## Verificações novas

A branch de revisão acrescenta [test_recruiting_evidence.py](../../backend/tests/test_recruiting_evidence.py), que verifica hash/declarações do benchmark e executa o solver sobre a fixture com uma repetição. Também configura [smoke de navegador](../../backend/scripts/browser_smoke_recruiting.py) em runner isolado. **A validação foi concluída:** [GitHub Actions #42513492013](https://github.com/LeandroAugFerreira/chronos-gestao-escalas/actions/runs/42513492013) aprovou os testes e o navegador no commit revisto; detalhes em [EVIDENCIAS.md](EVIDENCIAS.md).

## Recomendação

Para entrevistas: Chronos deve ser apresentado como **plataforma demonstrativa de planejamento com otimização e governança**, não como “IA que gera escalas juridicamente corretas” nem “hospital implantado”. Priorize explicar snapshots, CP-SAT, lacunas de demanda e segregação de aprovação. Veja [ESTUDO_DE_CASO.md](ESTUDO_DE_CASO.md) e [PLANO_DE_MELHORIAS.md](PLANO_DE_MELHORIAS.md).
