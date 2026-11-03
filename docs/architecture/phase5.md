# Chronos 1.0 — Cenários, capacidade e financeiro

Checkpoint local da Fase 5. Hospital Horizonte é o cenário de demonstração; unidade, setor, função, ciclo, atividades e premissas continuam configuráveis para outros segmentos. Não há publicação, solver, aprovação nem ativação de automações nesta fase.

## Dados, versões e acesso

Migration `007_scenarios_finance`: `scenario_versions` e `financial_runs`, com FKs compostas por organização/unidade. Total: 28 tabelas de domínio, sete migrations, além de `alembic_version`.

Cenário registra unidade, população de um setor ou de toda a unidade, mês de referência, chave/versão, antecessora, autor, fonte e premissas. A versão seguinte exige mesma chave/unidade/população/mês. Não existe edição ou exclusão pública: cada cálculo salva outra versão. Uniques e idempotência impedem duplicações concorrentes da mesma intenção. A restauração explícita da demonstração também remove cenários e projeções, preservando a proteção anterior de contas/auditoria.

Snapshots guardam resultado de capacidade, evidências e base salarial em campos separados. A resposta pública de capacidade nunca inclui salários ou a base salarial, nem as evidências pessoais completas. Seu fingerprint é HMAC para evitar que um hash público de valores privados facilite inferências. `scenario:read` permite consultar agregados; `scenario:write` permite calcular versões no escopo autorizado. Admin/RH/Gestor/Analista têm escrita, Financeiro tem leitura. Demo não recebe essas permissões.

Evidências pessoais exigem também `people:read` na unidade. Projeções exigem `finance:read`, `finance:simulate` e leitura do cenário na unidade; Financeiro, RH e Admin podem calcular, respeitando seus escopos. Leitura de projeções existentes exige permissão financeira. Não há lista nominal de pessoas nem contratos individuais nas respostas de projeção.

Resultados são imutáveis após a gravação. A criação lê dados em transação normal do banco; não oferece um corte global serializável de todos os cadastros sob edição concorrente. Aprovação com controle integral de insumos continua na Fase 6. Uma alteração cadastral exige novo cenário para aparecer nos resultados; não recalcula versões existentes.

## Capacidade: um mês civil

População: colaboradores ativos no momento da captura, lotados na unidade/setor escolhido. Contratos são congelados até 12 meses após o mês de referência para apoiar a projeção financeira. Até 1.000 pessoas por cenário síncrono e 2.000 plantões existentes no mês; acima disso, escolher um setor. Processamento em worker para cenários maiores fica na Fase 6.

Modos:

- **Calendário:** usa plantões em rascunho que interceptam o mês, incluindo a parte de turnos iniciados antes da fronteira. Reavalia cada plantão pelo LaborRules, sem alterar o calendário. Atuações em outro setor conservam o destino do plantão.
- **Ciclo:** usa configuração estruturada de `work_patterns` (`work/rest` e duração), âncora comum, horário local e intervalo não remunerado. Gera intervalos temporários somente em memória, sem gravar plantões. Reutiliza o LaborRules em uma amostra de um plantão por pessoa. Essa amostra não avalia o ciclo hipotético completo e nunca autoriza a escala.

Habilitações `verified` exigem comprovação cadastrada; `hypothesis` admite habilitações sintéticas válidas como hipótese. Ambas respeitam validade e competências exigidas pela função. O sistema não verifica conselhos profissionais externos. Dados de demonstração continuam pendentes de revisão.

Disponibilidade bruta = união dos intervalos de trabalho no mês, menos a união das indisponibilidades. Não há dupla contagem de sobreposições. Pausas não contribuem para trabalho; pausas pagas podem contribuir para a base remunerável bruta. Intervalos são recortados pelo mês e por dias locais para validade de contratos/habilitações. Horários civis ambíguos/inexistentes são recusados.

Orçamento contratual nominal = soma dos limites semanais aplicáveis por dia / 7, limitado pela meta semanal quando informada. A soma dos numeradores inteiros é dividida por 7 apenas ao final: quatro semanas de 2.400 minutos resultam em exatamente 9.600 minutos. O piso em minutos é aplicado uma vez por pessoa. O orçamento efetivo é o menor entre esse orçamento e os minutos elegíveis disponíveis. Esse rateio semanal é uma premissa agregada, sem distribuir jornadas ou salário.

Demanda por atividade registra setor de atuação, horário/duração, dias da semana, quantidade escolhida, competências, habilitações e fonte. Aplica-se ao mês de referência. Minutos exigidos = duração dos intervalos no mês × pessoas exigidas. Potencial elegível usa somente as interseções disponíveis no setor de destino e é limitado pelo orçamento de cada pessoa. Requisitos profissionais não recebem quantitativos universais.

As capacidades por atividade compartilham pessoas e **não podem ser somadas** como se fossem equipes independentes. A lacuna exibida é um limite inferior de falta em minutos, não uma prova de preenchimento de postos. Lacuna zero não demonstra cobertura de todos os turnos, continuidade assistencial ou viabilidade da escala. Atribuição, simultaneidade e dimensionamento ficam com o solver da Fase 6.

Evidências congelam intervalos disponíveis/remuneráveis/elegíveis por pessoa, limites contratuais, competências/habilitações e validade, ausência considerada, configuração do ciclo e avaliações LaborRules. Agregados trazem versão do algoritmo, alertas e escopo da amostra, sempre com revisão pendente.

## Financeiro: 12 meses explícitos

`FinancialRun` é uma projeção imutável sobre um cenário. Moeda BRL; não há conversão cambial automática. O mês de referência é M1; M12 encerra o horizonte. Meses têm duração civil real. Não se multiplica um custo mensal qualquer por doze.

Base salarial existente: por contrato e pessoa, salário mensal × dias contratuais ativos no mês / dias civis do mês. Arredonda esse componente para centavos. Contratos ambíguos impedem a projeção. Dias sem contrato não são remunerados no modelo e geram alerta; não significam desligamento nem economia comprovada. Esse rateio é uma premissa explícita de cálculo, não regra universal de folha. A redução da meta semanal **não reduz salário**. Salários futuros não são reajustados automaticamente.

Novas contratações: grupos hipotéticos com quantidade, salário mensal em centavos, meses inicial/final e fonte. Acrescentam salário durante sua vigência. Não aumentam automaticamente a capacidade: habilitações e turnos dessas pessoas precisam de outra simulação.

| Modelo de parcela | Cálculo |
|---|---|
| Fixa | valor em centavos × quantidade declarada ou pessoas médias no mês |
| Percentual | base explícita × pontos-base / 10.000 |
| Horas | salário-base hipotético / divisor mensal em minutos × minutos reais × razão de conversão × multiplicador |

Bases percentuais: salários, extras, noturno ou salários + esses dois adicionais. Extras/noturno usam o modelo de horas, com salário e divisor explícitos; não existe divisor universal. As parcelas de horas são calculadas antes das bases de encargos, independentemente da ordem de entrada. Encargos não incidem automaticamente sobre outros encargos. Valores fixos por pessoa usam a quantidade média ponderada pelos dias contratuais, incluindo contratações hipotéticas.

Na parcela de horas, multiplicador = adicional em pontos-base / 10.000, mais 1 somente se `include_base_hour` for declarado. Conversão de minutos é razão explícita; padrão 1:1, sem inferência automática de hora noturna reduzida. O volume mensal é informado pelo responsável; não é extraído ou classificado juridicamente do calendário nesta fase. Minutos remuneráveis são mostrados com seis casas decimais, mas o valor monetário usa a precisão integral do cálculo Decimal.

Cada parcela tem fonte, revisão declarada, vigência por índices de mês, meses sazonais e recorrência. Mensal aplica nos meses selecionados dentro da vigência; única aplica apenas em seu mês inicial. Exclusões de categoria exigem justificativa/fonte. Categoria omitida permanece como ausência de premissa, não custo zero validado. Benefícios, encargos, extras, noturno, contratação, treinamento e outros são configuráveis.

Centavos inteiros nas entradas/saídas; Decimal em cálculos intermediários com precisão 40. Política `ROUND_HALF_UP`: por contrato/pessoa/mês e por parcela/mês; totais somam centavos já arredondados. Média mensal é uma métrica própria arredondada; não se espera que média × 12 reproduza sempre o total. Intercâmbio monetário limita-se a 9×10¹⁵ centavos. A interface preserva os dígitos de centavos inclusive em valores elevados e negativos de comparação.

Comparações exigem mesma unidade/população/mês. Percentual com base zero é indefinido (`null`). Checagem de manutenção salarial compara salários nominais em vigências contratuais sobrepostas dos snapshots; não certifica remuneração integral nem continuidade de vínculo. Sensibilidade varia volume de horas, valores fixos ou taxas de encargos de −50% a +50%; calcula outra hipótese sem modificar ou gravar a projeção original.

Todas as projeções permanecem pendentes de revisão; a declaração `validated` de uma premissa exige evidência do responsável, sem equivaler a certificação trabalhista, contábil ou fiscal. Não há recolhimentos, pagamentos, folha oficial, importação de convenções ou índices automáticos.

## Interface e reprodução

Menu **Cenários**: selecionar população/mês, calendário ou ciclo estruturado, meta e elegibilidade; informar fonte; adicionar demanda por atividade; calcular/salvar; consultar e derivar próxima versão; comparar duas versões. Para ciclos, primeiro cadastrar um regime estruturado em Jornadas e regras.

Menu **Simulador financeiro**: escolher cenário, definir premissas/parcelas/contratações/exclusões; calcular prévia; revisar gráfico e reconciliação mensal; salvar. Duplicar/ajustar gera outra projeção. Comparação e sensibilidade preservam originais. Campos de taxa são pontos-base (100 = 1%) e valores são centavos; divisor de horas deve ser preenchido.

Backend: `services/capacity.py`, `services/financial.py`, contratos em `schemas/simulation.py`. `project(reference_month, payroll_snapshot, assumptions)` é puro e reproduz resultados financeiros usando somente o snapshot e premissas congeladas. Versões de algoritmo são registradas. O smoke HTTP usa outro banco e processos locais próprios, encerrados no final. QA visual em navegador permanece pendente pelo bloqueio previamente registrado.
