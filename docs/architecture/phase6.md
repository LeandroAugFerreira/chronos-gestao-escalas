# Chronos 1.0 — Fase 6: otimização e aprovação

O checkpoint implementa OR-Tools CP-SAT local, fila persistente, propostas imutáveis e decisões auditadas. Não ativa regras trabalhistas nem aprova registros da demonstração automaticamente. Hospital Horizonte continua com 350 pessoas e 19 setores; nenhuma constante do solver depende de um setor hospitalar.

## Entradas e elegibilidade

Um cenário da Fase 5 define a população e atividades. Ao criar o job, a API captura fatos atuais dessa população: contratos, ciclos, qualificações, competências, ausências, calendário, propostas já aprovadas e regras com suas versões. O snapshot não contém salários; custos opcionais são estimativas por plantão com fonte própria e permissão financeira. O HMAC-SHA256 dos insumos identifica o conteúdo sem permitir adivinhação de valores privados.

O horizonte tem até 31 dias, dentro do mês do cenário. Plantões são intervalos completos, inclusive suas partes fora do horizonte; somente a demanda é recortada. Instantes são UTC e dias/semanas são calculados no fuso da unidade. Horários civis inexistentes ou ambíguos são rejeitados. A semana vai de segunda a domingo. O histórico anterior e posterior é considerado, inclusive compromissos de outras unidades. A malha usa bordas exatas de demanda, pausas, plantões e dias; não arredonda para criar cobertura.

Os sete limites operacionais são obrigatórios e não têm valores normativos de reserva. Regras vigentes e limites contratuais restringem esses parâmetros; valores pendentes podem sustentar uma hipótese numérica, mas bloqueiam aprovação. Ausência/ambiguidade de contrato, indisponibilidade, competência ausente e habilitação vencida impedem a alocação. No modo `verified`, a habilitação também precisa estar revisada. `hypothesis` aceita credenciais sintéticas vigentes para simulação e sempre bloqueia aprovação. Ciclo estruturado com data inicial restringe os dias e a duração; configuração ausente fica expressamente pendente. Mudança de contrato dentro de um plantão é rejeitada conservadoramente.

Cada candidato pertence a uma pessoa, atividade e plantão. Uma pessoa não cobre atividades simultâneas. Pausas remuneradas ou não ficam fora da cobertura. Substituições entre setores exigem autorização explícita e cargos por atividade, além de todas as competências/habilitações. A população permanece na unidade escolhida; compromissos de outras unidades restringem descanso e deslocamento, mas esta versão não transfere pessoas entre unidades.

## Restrições e objetivos

O modelo aplica cobertura por intervalo, limites diários e semanais, descanso entre plantões, descanso semanal contínuo, dias consecutivos, ausências, ciclos, qualificações e teto opcional de pessoas distintas por atividade/dia. Janelas adicionais com início/fim exatos permitem sobreposição de passagem de plantão e prioridade específica. Dimensionamento vem de demanda e fontes parametrizadas, sem mínimo hospitalar universal.

No modo estrito, toda demanda é obrigatória. No diagnóstico, variáveis de lacuna permitem quantificar minutos-pessoa descobertos, preservando as demais restrições. A ordem lexicográfica é: lacunas por prioridade decrescente, minutos alocados, custo/equilíbrio de minutos/preferências. O último objetivo usa pesos explícitos; considera turno preferido e dias de folga preferidos. Não há prova de núcleo mínimo de inviabilidade: os diagnósticos informam opções descartadas, intervalos sem candidatos e lacunas. Justiça por categoria profissional, distribuição específica de noites e continuidade clínica longitudinal exigem modelos adicionais; não são inferidas do equilíbrio de minutos.

O verificador independente do CP-SAT reconta cobertura, minutos, sobreposições, descanso, elegibilidade e continuidade antes de produzir proposta. Ele compartilha primitivas temporais e políticas com o modelo, sem consultar variáveis/constraints do solver. Não é um auditor jurídico independente. `UNKNOWN` significa ausência de conclusão no limite; `FEASIBLE` não comprova ótimo. O ótimo só é declarado para os objetivos efetivamente concluídos.

## Execução e recuperação

`POST /optimization` retorna 202, sem executar solver na requisição. O worker CLI reserva a tarefa com lease de 30 segundos, heartbeat a cada 2 segundos, token de posse e até três tentativas. Reserva e finalização são serializadas por organização; heartbeat renova apenas uma posse ainda válida. Uma tarefa abandonada pode ser recuperada; o trabalhador antigo não pode confirmar seu resultado. Cancelamento na fila é imediato; em execução, o supervisor interrompe somente seu próprio processo solver. A CLI deve permanecer ativa para consumir a fila.

O solver recebe somente o snapshot JSON em stdin; não abre o banco. O supervisor remove variáveis de credenciais do ambiente herdado, usa arquivos temporários fora do projeto e não devolve traceback ao cliente. Limites: 500 pessoas, 20 mil fatos por tabela, 500 mil combinações examinadas, 25 mil variáveis de alocação, 20 mil células e 1–120 segundos solicitados. Há tolerância de 30 segundos para início/preparação/finalização do subprocesso. O parâmetro de memória CP-SAT é 512 MiB; não é limite físico do processo imposto pelo sistema operacional. O worker local processa uma tarefa por vez; vários workers compartilham a mesma fila com leases. Concorrência global e isolamento de recursos de produção ficam para infraestrutura posterior.

O resultado registra versão OR-Tools/algoritmo, seed, quantidade de threads, hardware, tempos, estágios, objetivo/limite, motivos de descarte e cobertura. Com seed e uma thread, os pequenos casos determinísticos são reproduzíveis. Ordem de agendamento do sistema e limite de tempo não garantem resultado idêntico para qualquer instância grande.

## Propostas e decisões

Resultado viável e verificado cria um rascunho, inclusive diagnóstico incompleto, com bloqueios visíveis. Proposta não altera o calendário manual. O conteúdo é imutável; revisão usa nova execução e versão filha. Versões aprovadas são compromissos fixos para novos cálculos, exceto a versão pai explicitamente substituída no mesmo horizonte/população. A versão anterior só é marcada substituída ao aprovar a filha.

Rascunho → em revisão → aprovado internamente ou rejeitado. A aprovação exige responsável diferente do autor do cálculo. Submissão e aprovação conferem revisão/digest, recapturam todos os insumos e repetem a verificação numérica. O lock de organização serializa escritas autenticadas de negócio, worker e operações CLI relevantes; dados modificados desde o cálculo retornam `STALE_INPUTS`. Isso é conservador: alterações em catálogos e regras da organização podem exigir recálculo mesmo sem afetar a solução final.

Não há override de lacunas, competências ou descanso. Habilitações, contratos, jornadas, demanda e histórico precisam de revisão explícita; cinco famílias de regras devem estar vigentes, revisadas e sem conflito. Transição de limites dentro de janelas de dia/semana bloqueia a aprovação conservadoramente. Revisões individuais registram ator, fonte, evidência e digest, sem certificar validade jurídica. Para regras, usa-se a sucessão versionada existente da Fase 4. Um cenário pode receber anotação de revisão sem alterar seu conteúdo original. Revisão nova exige novo cálculo.

Uma escala aprovada internamente não é publicada. Não há integração externa, notificações, scheduler ou n8n nesta fase. Qualquer publicação continua condicionada à autorização do usuário.

## Interface e operação local

`/otimizacao` permite configurar plantões, limites, cargos, ciclos, elegibilidade, custos autorizados e horizonte; acompanhar fila, cancelar, inspecionar alocações/lacunas, derivar versão e registrar decisões. O formulário não preenche limites jurídicos. Janelas adicionais, seed/threads e outros pesos também estão na API tipada. Perfis sem `people:read` recebem resultados agregados, sem alocações individuais. Valores de custos são removidos para perfis sem `finance:read`, inclusive objetivo monetário. O snapshot bruto não é retornado pela API.

Em terminal separado, com o mesmo runtime dos demais componentes:

```powershell
.\scripts\start-worker.ps1
# Consumir no máximo uma tarefa e encerrar:
.\scripts\start-worker.ps1 -Once
```

Fontes técnicas verificadas em 24/10/2026: [CP-SAT](https://developers.google.com/optimization/cp/cp_solver), [escalas de profissionais](https://developers.google.com/optimization/scheduling/employee_scheduling), [distribuição OR-Tools 9.15.6755](https://pypi.org/project/ortools/). Instalação testada em Python 3.13/Windows, restrita ao venv local. Nenhum limite numérico desta documentação constitui orientação jurídica.
