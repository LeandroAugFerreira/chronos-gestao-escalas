export type AutomationDefinition = { id: string; unit_id: string; code: string; name: string; enabled: boolean; owner_id: string | null; interval_minutes: number | null; next_run_at: string | null; last_run_at: string | null; revision: number; parameters: { lookahead_days: number; monitor_limit: number; deliver_n8n: boolean } }
export type AutomationExecution = { id: string; unit_id: string; code: string; source: string; attempt: number; state: string; result: Record<string, unknown>; error_code: string | null; finished_at: string | null; event_id: string }
export type QueueEntry = { id: string; unit_id: string; code?: string; kind?: string; state: string; revision: number; attempts: number; attempt_limit: number; next_attempt_at: string; error_code: string | null; created_at: string; last_http_status?: number | null }
export type AutomationNotice = { id: string; unit_id: string; code: string; title: string; body: string; entity_type: string; entity_id: string; acknowledged_at: string | null; revision: number; severity: string }
export type AutomationSuggestion = { id: string; unit_id: string; schedule_id: string; reason: string; state: string; details: { affected_assignments: number } }
export type AutomationArtifact = { id: string; unit_id: string; filename: string; content_type: string; digest: string; created_at: string; finance_required: boolean }
export type IntegrationCredential = { id: string; unit_id: string; name: string; actions: string[]; enabled: boolean; revision: number; token_once?: string }
export const automationStates: Record<string, string> = { queued: 'Na fila', running: 'Em execução', succeeded: 'Concluída', failed: 'Falha', cancelled: 'Cancelada', skipped: 'Ignorada: rotina desativada' }
export const sourceLabels: Record<string, string> = { event: 'Alteração de dados', manual: 'Solicitação manual', timer: 'Agendamento', n8n: 'Integração n8n' }
export const automationPermissions: Record<string, string> = { A01: 'optimization:read', A02: 'optimization:read', A03: 'schedule:approve', A04: 'org:read', A05: 'people:read', A06: 'optimization:write', A07: 'audit:read' }
export function executionSummary(row: AutomationExecution) {
  const value = row.result; const count = (key: string) => Array.isArray(value[key]) ? value[key].length : 0
  if (value.restricted) return 'Detalhes restritos ao perfil autorizado.'
  if (row.state === 'skipped') return 'Rotina desativada no momento do processamento.'
  if (row.state === 'failed') return 'Execução não confirmada. Consulte o motivo e as tentativas na fila.'
  const summaries: Record<string, string> = { A01: `${count('checks')} propostas conferidas.`, A02: value.no_result ? 'Sem cálculo de cobertura disponível.' : `${value.measured_runs || 0} cálculos medidos; ${count('alerts')} alertas.`, A03: `${count('notice_ids')} avisos para revisão; ${value.schedules_without_reviewer || 0} propostas sem outro aprovador.`, A04: 'Arquivo de indicadores disponível em Relatórios.', A05: `${value.inspected_records || 0} premissas conferidas; ${count('notice_ids')} pendências.`, A06: `${count('suggestion_ids')} sugestões; nenhum novo cálculo automático.`, A07: 'Alteração vinculada à trilha de auditoria.' }
  return (summaries[row.code] || 'Resultado registrado.') + (value.truncated ? ' O limite de consulta foi atingido; resultado parcial.' : '')
}
