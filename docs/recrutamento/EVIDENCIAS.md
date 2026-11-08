# Evidências auditáveis e limites — Chronos 1.0

**Revisão:** 08/11/2026. **Origem:** main no commit fdc0ba5a8ca9fc2b2b5ec14fa7d08f1a68603ce3. **Execução nova:** [GitHub Actions #42512605602](https://github.com/LeandroAugFerreira/chronos-gestao-escalas/actions/runs/42512605602).

## Natureza das evidências

- **Lido:** comportamento identificado em código, sem execução específica daquele método.
- **Executado no CI:** comando rodou em runner temporário com logs verificáveis.
- **Histórico:** execução documentada anteriormente, não é uma aprovação nova.
- **Simulado:** fixture sem cliente, funcionários ou produtividade reais.
- **Pendente:** operação ou infraestrutura ainda não validada.

## Execução observada

| Componente | Resultado | Limites |
| --- | --- | --- |
| Backend Python 3.13 / pytest | **184 aprovados, 1 ignorado, 1 aviso** | PostgreSQL ignorado por falta de banco descartável |
| Frontend React/TypeScript / Vitest | **88 testes em 10 arquivos aprovados** | Componentes e serviços; não todas as jornadas por navegador |
| Build do frontend | **Aprovado** | Compilação não é implantação |
| Chromium Playwright | **Aprovado** | Login por formulário, dashboard da fixture e acesso à tela de otimização; não gera/aprova escalas pela UI |
| Microensaio first-fit e OR-Tools | **Testes de regressão aprovados** | Novos testes em [test_recruiting_evidence.py](../../backend/tests/test_recruiting_evidence.py) validam hash e executam uma repetição |
| Tour público | Estático, sem API | [chronos-demo.html](https://leandroaugferreira.github.io/chronos-demo.html) mostra resultados históricos em dois cenários, não executa solver |

**Diferença importante:** o backend ganhou dois testes; os 88 testes frontend já existiam. O teste de navegador, com dados fictícios e autenticação real, foi acrescentado nesta revisão.

## Isolamento do smoke

O job definido em [.github/workflows/tests.yml](../../.github/workflows/tests.yml) usa Ubuntu 24.04, Python 3.13, Node 22, Playwright 1.56.0 e Chromium.

1. Gera segredo JWT e senha de QA aleatórios em memória.
2. Cria SQLite temporário fora do repositório e habilita o uso somente em ambiente test.
3. Aplica migrations Alembic, popula a fixture fictícia e cria um usuário administrativo efêmero.
4. Inicia API e Vite somente em 127.0.0.1.
5. Chromium faz login pelo formulário real, valida indicadores do dashboard e visita a área de otimização.
6. Produz screenshots da fixture em artifact de sete dias e encerra os serviços.

**Não** aciona n8n, SMTP, IA externa, banco pessoal, PostgreSQL produtivo ou worker de cálculo de longa duração.

## Microensaio verificável

| População | First-fit | Chronos CP-SAT | Conclusão |
| --- | --- | --- | --- |
| 3 profissionais fictícios | 1.440/1.440 postos-min; R$ 1.440 imputados | Mesmo resultado | Cobertura completa no caso pequeno |
| 2 profissionais fictícios | 960/1.440; lacuna 480; R$ 960 imputados | Mesmo resultado | Cobertura parcial: custo menor não representa economia |

Fonte histórica: [benchmark.json](../portfolio/benchmark.json), [fixture](../../data/synthetic/portfolio_benchmark.json), [script](../../backend/scripts/portfolio_benchmark.py).

O novo teste roda uma repetição, validando invariantes; **não** compara tempos de máquinas diferentes. A marca OPTIMAL no modo diagnóstico **não** significa cobertura integral. Nada autoriza afirmar superioridade do solver, ROI ou ganhos de trabalho humano nesse cenário.

## Evidências anteriores

- [Validação 02/11/2026](../github/VALIDACAO.md): 182 aprovados, um ignorado no backend, 88 frontend e build.
- [Fase 9](../testing/phase9-report.md): evidências históricas com worker, governança, recuperação e outros cenários.
- [Case do Hospital Horizonte](../portfolio/case-study.md): distinção entre cenários sintéticos, limites de escopo e medições históricas.

## Pendências

- PostgreSQL efêmero não executado nesta revisão.
- Fluxo completo de criar cenário, otimizar, submeter e aprovar por cliques não exercitado no novo smoke.
- Sem teste de invasão, homologação trabalhista/clínica, deploy seguro, Power BI Desktop nativo ou execução do EXE Windows.
- n8n continua bloqueado por dependências, conforme [auditoria de segurança](../security/phase9-findings.md).

[AUDITORIA.md](AUDITORIA.md) · [PLANO_DE_MELHORIAS.md](PLANO_DE_MELHORIAS.md).
