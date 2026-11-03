# Chronos 1.0 — Especificação de otimização

OR-Tools CP-SAT foi implementado no checkpoint da Fase 6, independente de IA e n8n. Esta especificação preserva o alvo completo; [escopo efetivo e limites da implementação](phase6.md) distinguem as funções disponíveis das extensões futuras. Há propostas de escala, sem publicação externa ou certificação jurídica.

## Entradas

Snapshot de organização/unidades, período e fuso, contratos, jornadas, intervalos, habilitações e competências válidas, equivalências de substituição autorizadas, disponibilidade/ausências, preferências, histórico de plantões/folgas, demanda por atividade e intervalo, custos/premissas e versões de LaborRules. Incluir alocações anteriores e posteriores necessárias para verificar descansos e ciclos nas bordas.

Turnos candidatos aceitam durações configuráveis, virada de dia, pausas explícitas e janela de passagem de plantão. A malha temporal é configurável (ex.: 15 min), mas mudanças de regra/demanda/pausa serão pontos de quebra exatos; não arredondar para criar cobertura artificial. Operação 24x7 gera demanda em todos os intervalos necessários, inclusive madrugada, fins de semana e feriados, conforme calendário do setor.

## Modelo

Índices: pessoa `e`, candidato de plantão/posto `s`, atividade `a`, setor `d`, intervalo `t`. Decisão binária `x[e,s,a]` significa pessoa alocada à atividade naquele candidato. A elegibilidade pré-calculada exige contrato, competência E habilitação válidos e disponibilidade durante toda a atividade. Pessoas sem elegibilidade nem recebem variável.

Restrições rígidas:

- Não sobrepor trabalho de uma pessoa entre setores/unidades/atividades. Uma pessoa não cobre dois postos no mesmo intervalo.
- Cobertura ativa soma apenas candidatos presentes e fora de pausa, com a competência/qualificação exigida; `sum(x ativos) >= demanda[d,a,t]` no modo estrito.
- Minutos trabalhados por janela ≤ limite aplicável por contrato/regra; contabilizar corretamente intervalos, revezamentos, adicional noturno para custos e compensações juridicamente validadas.
- Combinações incompatíveis por descanso real, intervalo intrajornada, folgas, dias consecutivos e ciclos são proibidas. Padrões 12x36 exigem o descanso contratual/regulatório, não apenas uma folga no calendário.
- Respeitar ausências, preferências que forem restrições contratuais, deslocamento entre unidades e compromissos nas bordas do horizonte.
- Substituição depende de matriz de equivalência/habilitação e escopo aprovado. Não substituir médico/enfermeiro/técnico com base apenas em habilidade parecida.
- Continuidade obrigatória e sobreposição de passagem de plantão, quando configuradas, são cobertas com pessoas elegíveis. Continuidade desejável é preferência separada.
- Versão aprovada permanece fixa; propor uma alteração cria versão filha com diferenças e nova aprovação.

Preferências ponderadas: equilibrar horas e plantões/noites/finais de semana por pessoas elegíveis, respeitar folgas preferidas, reduzir custo, trocas e deslocamentos, preservar continuidade desejável. Pesos e precedência fazem parte do snapshot; não usar ponderação que permita violar regra rígida.

## Lacunas e inviabilidade

**Modo estrito:** dimensionamento obrigatório é restrição rígida. Se impossível, retornar INFEASIBLE com diagnóstico, sem escala publicável.

**Modo diagnóstico:** modelo separado acrescenta `gap[d,a,t] >= 0`, `cobertura + gap >= demanda`. Objetivo lexicográfico: primeiro minimizar lacunas por criticidade, depois preferências/custos. Nunca relaxar elegibilidade, descanso, contrato ou limite legal. Resultado é uma proposta incompleta para análise e não pode ser classificado como cobertura completa ou publicado.

O pré-processamento identifica demanda sem candidato, falta de competência, credencial vencida, indisponibilidade e conflitos com descansos. Assumption literals por família podem apoiar análise de conjuntos conflitantes; o diagnóstico não será apresentado como prova mínima se não for. Sugestões: alterar demanda autorizada, turno/ciclo, capacitar ou contratar perfil específico; não remover silenciosamente descanso ou habilitação.

## Execução e resultado

API cria job idempotente e retorna 202 + run_id. Worker tem limite de tempo/memória, heartbeat, cancelamento cooperativo e limite de concorrência. Persistir seed, quantidade de workers, versão OR-Tools/algoritmo, hash de entrada/regras, hardware disponível, tempos, status, objective, best_bound, gap de otimização e lacunas operacionais separadamente.

Status CP-SAT: OPTIMAL, FEASIBLE, INFEASIBLE, MODEL_INVALID e UNKNOWN; timeout sem solução não prova inviabilidade. FEASIBLE não significa ótimo. Após solver, avaliador independente verifica todas as restrições e emite relatório antes da submissão. Conformidade com regras configuradas não é certificação jurídica.

Referência: [Google OR-Tools CP-SAT](https://developers.google.com/optimization/cp/cp_solver/).

## Critérios de aceite e evolução

Fixtures pequenas com ótimo conhecido, solução inviável, ausência, competência insuficiente, descanso, pausa, noite, fim de semana, 24x7, troca/substituição, credencial vencida, várias unidades, horizonte com bordas, regra nova durante período, timeout e cancelamento. Reprodutibilidade com seed e um worker nas fixtures determinísticas. Medir cobertura por minutos-posto (numerador e denominador), conflitos, tempo e custo; `horas necessárias / horas médias` é apenas estimativa preliminar de capacidade.
