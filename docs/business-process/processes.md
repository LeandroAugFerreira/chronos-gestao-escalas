# Chronos 1.0 — Processos, custos e automações

## Planejamento e aprovação

Importar/cadastrar estrutura → validar dados e regras → selecionar unidade/setor/período → gerar cenário versionado → calcular capacidade/financeiro → solicitar otimização → analisar cobertura/conflitos → submeter → aprovar ou rejeitar → publicar internamente no ambiente fictício. Nenhum envio para sistema externo é implícito.

Estados: Rascunho → Em análise → Aprovado → Publicado. Em análise pode ser Rejeitado ou Cancelado; versão substituída aponta para sucessora. Reedição de versão em análise/aprovada/publicada cria rascunho filho. O hash avaliado e a permissão do aprovador são verificados em transação; submissão com regra pendente, lacuna obrigatória ou avaliação não concluída não permite atestar/publicar uma escala conforme. Auditoria registra ator, data, justificativa e diferenças.

Administrador gerencia configuração; RH pessoas/jornadas/regras/cenários; Gestor equipes/propostas/aprovações dentro do escopo; Financeiro custos agregados; Analista indicadores/simulações autorizadas; Demo leitura limitada. Uma matriz de permissões por endpoint será implementada na Fase 2, sem confiar no frontend.

## Simulador financeiro (Fase 5)

Custos mensais: salários-base + encargos configurados sobre bases explícitas + benefícios + extras e adicionais calculados segundo regra aplicável + contratação + treinamento + outros custos documentados. Custos anuais respeitam recorrência e sazonalidade cadastradas, não multiplicam parcelas únicas por doze. Não há alíquota nem piso salarial universal embutido.

Guardar valor, moeda, unidade, base de incidência, fonte, vigência, responsável e caráter sintético de cada premissa. Usar centavos/Decimal com política de arredondamento por componente e reconciliação do total. Encargos percentuais e fixos separados; custos de hora dependem do divisor aplicável, não de uma constante para todos. Preservação salarial e contratos são avaliados pelo LaborRules. Ganhos hipotéticos de produtividade/retrabalho aparecem como hipóteses, não medição real.

## Catálogo A01–A07 (Fase 7)

| Código | Trigger | Ação e resultado |
|---|---|---|
| A01 | Agenda/alteração de cenário | Verificar conflitos e status; persistir relatório |
| A02 | Mudança de demanda ou escala | Medir lacunas por intervalo/competência; criar alerta deduplicado |
| A03 | Submissão | Registrar notificação interna para aprovador autorizado |
| A04 | Agenda | Consultar indicadores, gerar arquivo, guardar referência e execução |
| A05 | Agenda de vigências | Alertar revisão; nunca ativar regra sem validação |
| A06 | Disponibilidade alterada | Identificar versões afetadas e propor job de reotimização; não trocar escala aprovada |
| A07 | Mudança relevante | Gravar auditoria de regras, permissões, escalas e decisões |

Definição: identificador, nome/descrição, trigger, enabled/status, responsável, última/próxima execução e parâmetros. Execução: event_id, tenant, correlation_id, idempotency_key, tentativa, início/fim, resultado, erro sanitizado e próxima tentativa. Estados queued/running/succeeded/failed/cancelled; retentativa com backoff, limite e recuperação de lease expirado. Chave única impede duplicar efeitos após timeout. Nenhuma notificação é enviada externamente por padrão.

## Workflows n8n preservados

1. Nova escala pendente: evento autenticado → validar payload → localizar gestor → registrar notificação → aguardar decisão.
2. Alerta de cobertura: evento → criticidade → deduplicação → registrar alerta → notificar responsável no canal autorizado.
3. Relatório programado: schedule → API → indicadores → arquivo → armazenamento local → registrar execução.
4. Disponibilidade: webhook → validar evento e tenant → atualizar registro → identificar impacto → solicitar reotimização.

Os quatro workflows foram exportados em JSON, desativados por padrão e sem segredos. A Fase 7 implementa autenticação, escopo, timestamps, replay protection, limites, retries e histórico, com teste real de importação/execução no n8n local. A API e o scheduler do Chronos oferecem os mesmos casos de uso sem n8n; nenhum envio externo foi ativado. A06 registra sugestões e prepara o fluxo de nova versão, sem disparar otimização ou aprovação automática. Veja automation/n8n/README.md e docs/architecture/phase7.md para a configuração e os limites efetivos.
