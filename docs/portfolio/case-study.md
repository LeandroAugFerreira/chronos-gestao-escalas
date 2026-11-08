# Chronos 1.0 — Estudo de caso fictício Hospital Horizonte

## Cliente e problema

Hospital Horizonte é uma instituição fictícia de médio porte, com 350 colaboradores em 19 setores assistenciais, administrativos e operacionais. A operação hospitalar é contínua, mas cada setor tem suas próprias necessidades. Os quantitativos da demonstração são premissas sintéticas, sem mínimos profissionais universais ou comprovação de dimensionamento clínico.

O problema proposto é preparar escalas e comparar jornadas diante de demanda, competências, ausências, descansos e custos. O diagnóstico é uma hipótese de negócio do case: planejamento disperso dificulta identificar lacunas, preservar revisões e explicar alternativas. Não houve entrevista, observação de hospital real ou medição de um processo humano anterior.

## Solução desenvolvida

O Chronos reúne cadastro/escopo por unidade, calendário, regras com fontes/vigências, cenários congelados, projeção financeira, otimização OR-Tools, revisão por segundo responsável, automações locais e exportações. A marca temporal abstrata e o domínio configurável permitem outros segmentos. A demonstração não envolve pacientes nem dados reais de trabalhadores.

O fluxo passa de dados e hipóteses para cálculos rastreáveis, proposta versionada e decisão humana. A origem, o digest e a versão permitem verificar o que foi considerado. Mudanças posteriores não transformam uma proposta antiga em uma nova aprovação.

Decisões técnicas: monólito modular FastAPI/SQLAlchemy/Alembic; PostgreSQL de referência e SQLite local opt-in; React/TypeScript; CP-SAT com verificador independente; centavos/Decimal; outbox e workers com lease; RBAC por campo/unidade; explicações determinísticas gratuitas. Bancos/caches ficam fora do OneDrive. O núcleo funciona sem IA paga e sem n8n.

## Antes e depois simulados

O processo anterior é representado por uma política **first-fit cronológica**, implementada em código: seleciona candidatos por ordem de horário e profissional, aceitando somente restrições verificadas. O processo automatizado usa o solver Chronos com os mesmos insumos e verificador. Isso é comparação de algoritmos, sem tempo de cliques, trabalho humano ou produtividade real medidos.

O [microensaio medido](benchmark.json) e a [fixture reproduzível](../../data/synthetic/portfolio_benchmark.json) cobrem **uma atividade durante um dia**, com três e dois profissionais fictícios. Três repetições sequenciais, seed 1042 e um worker; versão de Python/OR-Tools, arquitetura, hashes e tempos constam do JSON. Tempos incluem preparo da política/pipeline e podem incluir carregamento inicial de bibliotecas; a mediana não é um SLA.

| População do microensaio | Política first-fit | Chronos CP-SAT | Interpretação |
|---|---|---|---|
| 3 profissionais | 1.440/1.440 postos-minuto; 3 atribuições; custo imputado de 144.000 centavos | Mesmos cobertura, atribuições e custo; resultado numérico completo | As duas políticas resolveram este caso pequeno |
| 2 profissionais | 960/1.440 postos-minuto; 480 descobertos; custo imputado de 96.000 centavos | Mesmos cobertura e custo em modo diagnóstico, com lacuna explícita | A escala é incompleta; menor custo não demonstra economia |

O custo fictício é 48.000 centavos por plantão, declarado no input. Não é salário, piso ou projeção anual. Os dois casos retornam zero categorias de erro de restrição no verificador, e o caso de duas pessoas continua sem cobertura completa. A marca `OPTIMAL` do modo diagnóstico não apaga essa lacuna.

Os tempos medidos ficam no JSON, com mínimo/mediana/máximo; não se apresenta ganho percentual de produtividade humana, economia observada ou extrapolação para o hospital. Este microensaio não demonstrou superioridade de cobertura/custo no caso pequeno. A evidência de governança e dos demais requisitos vem dos testes integrados, não desta comparação isolada.

Reprodução:

```powershell
& $pythonPath .\backend\scripts\portfolio_benchmark.py --output 'C:\PASTA_DE_TESTE\benchmark-novo.json' --repetitions 3
```

## Resultados técnicos registrados

Na Fase 9, 253 testes backend passaram em SQLite/PostgreSQL e 62 testes de frontend passaram após correção de dependências. O smoke HTTP mediu cerca de 3,89 s para o cenário e 16,306 s para o trecho do worker naquele ambiente isolado com **351 pessoas**: 350 da fixture e uma cadastrada pelo próprio teste. Esses tempos são observações daquele teste, não benchmark comparativo com o trabalho manual ou promessa para o hospital completo.

O fluxo integrado exercitou revisão, cálculo, submissão, recusa de autoaprovação, aprovação por segundo responsável, automação local, relatórios e persistência após nova instância. Backup/restauração SQLite e dump/restore PostgreSQL foram verificados em cópias isoladas. A atualização de revisão preservou todas as colunas e registros anteriores do banco principal. O [relatório da Fase 9](../testing/phase9-report.md) é a fonte desses resultados históricos.

## Limitações e evolução

O n8n permanece com partida bloqueada após auditoria de dependências; sua execução real na Fase 7 é evidência histórica. Um smoke limitado de navegador real (login, Dashboard e acesso à área de otimização) foi aprovado posteriormente no CI, com capturas de dados sintéticos. QA integral de navegador, teclado/contraste/responsividade e Power BI Desktop continuam pendentes. Parte da manutenção especializada é via API; importação genérica e publicação interna final ainda não estão concluídas/liberadas. O [mapa de cobertura](coverage.md) torna os limites verificáveis.

Próximas decisões: remediar/revalidar n8n, concluir QA acessível e visual, validar Power BI nativo, revisar lacunas funcionais/operacionais e obter aceite de release. Nenhuma publicação, certificação jurídica, implantação hospitalar ou resultado clínico real é alegado por este case.
