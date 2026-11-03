# Chronos 1.0 — Jornadas, calendário e LaborRules

Checkpoint da Fase 4. Implementação local e multissegmento; Hospital Horizonte continua com 350 pessoas e 19 setores, sem alteração da fixture original.

## Persistência e acesso

Migration `006_calendar_rules`: configuração JSON de ciclos em `work_patterns`, novas tabelas `labor_rules`, `calendar_shifts` e `schedule_evaluations`. Total: 26 tabelas de domínio, além de `alembic_version`. Todas as novas referências usam FKs compostas por organização. Nenhuma tabela é criada pelo startup da API.

Permissões `schedule:read/write` para admin/RH/gestor, `rules:read` também para analista; `rules:write` para admin/RH. Alterar política requer escopo global. Calendário respeita unidade de origem e destino. Plantões de substituição podem atuar em outro setor da mesma unidade; habilitações são conferidas pela função cadastrada da pessoa. Necessidades próprias da atividade/setor serão integradas à cobertura e ao solver na Fase 6.

Um plantão tem pessoa fixa, setor, início/fim, título, pausas remuneradas ou não, revisão e avaliação na última gravação. Estados: `draft` e `cancelled`. Não há aprovação nem publicação de escala nesta fase. Cancelamento preserva histórico. A restauração explícita da demonstração elimina também calendário, regras e avaliações, preservando contas/escopos/auditoria conforme o fluxo anterior.

## Prévia e gravação

1. O formulário converte horas civis no fuso da unidade para UTC. Horários inexistentes ou ambíguos por mudança de fuso são recusados. Não depende do fuso do computador.
2. `POST /calendar/preview` avalia sem persistir plantão, retornando digest determinístico. Edição informa `shift_id` para excluir o próprio registro do histórico.
3. Gravação exige esse digest e reavalia os dados. Se mudou qualquer conteúdo relevante da avaliação, retorna `409 PREVIEW_EXPIRED`. O usuário reavalia e confirma novamente. Alertas podem ser preservados em rascunho com confirmação explícita; salvar não aprova a jornada.
4. Criação aceita `Idempotency-Key`; edição/cancelamento exigem revisão otimista. PostgreSQL serializa gravações de calendário por pessoa com lock. SQLite é o perfil local leve e pode exigir nova tentativa quando ocupado.
5. Plantão e snapshot da avaliação são gravados com auditoria na mesma transação. Snapshot registra fontes, parâmetros, revisão da pessoa, contratos, histórico usado e versões normativas. Avaliações antigas não são recalculadas ao ler. O calendário informa essa característica; Editar reavalia o estado atual.

A serialização por pessoa coordena alterações do calendário. Mudanças simultâneas em outras configurações não possuem bloqueio global de publicação. Aprovação com snapshot integral e controle de concorrência de todos os insumos continua na Fase 6.

## Regras e sucessão explícita

Regra contém chave/versão, critério tipado, limite/limiar em minutos, fonte, vigência exclusiva no fim, unidade, função/categoria, contrato e referência ao acordo. Organização vem do principal autenticado. Não aceita Python, SQL, DSL ou `eval`.

Versões são imutáveis pela API. Nova versão pode declarar `supersedes_id`, com mesma chave/critério/escopo/instrumento, número seguinte, início igual ou posterior e mesmo fim original. A sucessão encerra a aplicação efetiva da antecessora no início da nova versão. Não altera o registro nem snapshots anteriores. Uma única sucessora por versão impede ramificação. Alterações em escopos diferentes exigem análise de conflito; não existe precedência implícita por versão mais alta.

Regra pendente produz alerta mesmo quando o cálculo numérico passa. Uma declaração `validated` exige evidência de revisão com pelo menos 20 caracteres e registra o usuário responsável. O sistema registra a declaração; não autentica formação jurídica do declarante. Contratos/regimes/habilitações sintéticos permanecem pendentes. Não existe certificação jurídica automática.

Vigência de regra por contrato é limitada à validade desse contrato. Fronteiras dividem o período para detectar famílias sem regra. Critérios com parâmetros divergentes na mesma vigência preservam as verificações individuais e geram pendência de conflito. Quando uma vigência muda dentro de uma janela diária/semanal, compara-se conservadoramente a janela completa e emite-se `WINDOW_TRANSITION`; não há rateio automático.

## Critérios executáveis e limites

- Máximo de minutos de trabalho por dia civil local e por semana civil de segunda a domingo.
- Intervalo contínuo mínimo, condicionado ao total de trabalho ultrapassar o limiar configurado. Pausas contíguas formam um intervalo contínuo mesmo com remunerações diferentes.
- Descanso entre plantões, consultando plantões anteriores e posteriores conhecidos. Sem adjacência conhecida, emite pendência de histórico.
- Maior descanso contínuo dentro de semana civil, considerando ocupação por plantões e seu histórico conhecido. É um critério configurável de planejamento, sem representar todas as condições de repouso semanal, domingos ou compensações mensais.
- Limite semanal contratado, sem compensação automática; contrato único e vigente em cada dia; situação ativa; sobreposição; indisponibilidade; competências e validade/comprovação de habilitações exigidas pela função.

Intervalos são `[início,fim)`. Persistência em UTC, minutos inteiros; dias e semanas no fuso da unidade. Plantões até 72 horas são um limite técnico de entrada, sem autorização jurídica. Cálculos usam todo o histórico persistido da pessoa, inclusive fora da janela exibida. Sem deduplicar tempo em plantões sobrepostos: o conflito é emitido e o total conservador pode contar ambos.

Tempo transcorrido, trabalho (exclui todas as pausas) e remunerável (exclui somente as pausas não remuneradas) são distintos. Remunerável é uma base de minutos declarados, sem hora noturna reduzida, adicionais, pisos ou reflexos. Esses cálculos financeiros serão tratados na Fase 5. Ausência de plantão fora da janela representa somente o planejamento conhecido, sem prova de descanso efetivamente realizado.

Quatro resultados, com prioridade não conformidade → pendência → ausência de regra → conformidade configurada. Todos os achados permanecem visíveis, inclusive quando outra condição determina o resultado agregado:

- Conforme com as regras configuradas.
- Não conforme com as regras configuradas.
- Pendente de validação jurídica.
- Não avaliado por ausência de regra aplicável.

Regimes 5x2, 4x3, 12x36 e personalizados são referências. Novos regimes podem declarar ciclo de trabalho/descanso e duração de plantão; o ciclo não gera plantões nesta fase. Não se infere validade nem se força o ciclo no calendário manual. Simulação e geração serão integradas nas Fases 5/6.

Não foram implementados nesta fase: dimensionamento/otimização de cobertura 24x7, feriados por município, rodízio de domingos, compensações/banco de horas, excepcionalidades profissionais completas, ponto realizado, aprovação, financeiro, OR-Tools ou n8n. O resultado de conformidade limita-se aos critérios configurados e avaliados; não é certificado de atendimento a toda a legislação.

## Interface e roteiro

Menu Calendário: selecionar unidade, semana/mês, setor e pessoa; Novo plantão; informar período/pausas; avaliar; conferir critérios/evidências; confirmar rascunho. Selecionar um plantão para consultar avaliações históricas, editar/reavaliar ou cancelar. Ao filtrar uma pessoa, consultar/cadastrar indisponibilidade (cadastro requer `people:write`). Não há edição/exclusão de indisponibilidades nesta entrega.

Menu Jornadas e regras: consultar regimes; cadastrar hipótese de ciclo; registrar regra com fonte/vigência/escopo; criar sucessora explícita preservando condições. A demonstração começa sem regras numéricas ativadas. Para demonstrar violações, cadastrar uma hipótese com um limite escolhido, manter revisão pendente e comparar o resultado com um plantão. Não inserir essa hipótese como norma universal.

Inspeção visual real em navegador continua pendente conforme bloqueio registrado na Fase 1. Validações disponíveis: testes de componente/JSDOM, build e integração HTTP real por proxy, sem navegação automatizada alternativa.
