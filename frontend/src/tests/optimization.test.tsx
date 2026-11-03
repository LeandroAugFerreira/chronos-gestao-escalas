import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, it, vi } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { OptimizationForm, OptimizationPage, AssignmentTable } from '../pages/optimization'
import { api, ApiError } from '../services/client'
import type { Scenario } from '../types/simulation'

vi.mock('../hooks/auth', () => ({ useAuth: () => ({ user: { id: 'u', permissions: { 'optimization:read': null, 'optimization:write': null, 'scenario:read': null, 'finance:read': null } } }) }))
const scenario: Scenario = { id: 's', unit_id: 'unit', department_id: null, key: 'test', version: 1, parent_id: null, name: 'Cenário de cobertura', reference_month: '2026-11-01', created_at: '', digest: 'd'.repeat(64), inputs: { demands: [{ name: 'Atendimento' }] } }
const previous = { name: 'Cálculo de cobertura', start_date: '2026-11-02', end_date: '2026-11-03', mode: 'diagnostic', eligibility: 'verified',
  templates: [{ name: 'Diurno', start_time: '08:00', duration_minutes: 480, break_after_minutes: 240, break_minutes: 30, break_paid: false, weekdays: [0], cost_cents: 0 }],
  limits: { max_daily_minutes: 480, max_weekly_minutes: 2400, min_rest_minutes: 660, min_break_minutes: 30, break_threshold_minutes: 360, min_weekly_rest_minutes: 1440, max_consecutive_days: 5, source: 'Hipótese para teste de interface', validation_status: 'pending_review', review_evidence: '' },
  activity_job_role_ids: { '0': ['role'] }, history_review_evidence: 'Histórico sintético conferido pelo responsável', cycle_anchors: { pattern: '2026-11-02' } }
beforeEach(() => vi.restoreAllMocks())
function mount(node: React.ReactNode) { const client = new QueryClient({ defaultOptions: { queries: { retry: false } } }); return render(<QueryClientProvider client={client}><MemoryRouter>{node}</MemoryRouter></QueryClientProvider>) }
function form(copy?: Record<string, unknown>, parentId?: string) { const onSaved = vi.fn(); render(<OptimizationForm scenario={scenario} roles={[{ id: 'role', name: 'Atendente' }]} patterns={[{ id: 'pattern', name: 'Jornada de teste' }]} previous={copy} parentId={parentId} onSaved={onSaved} />); return onSaved }

it('mantém limites vazios e exige entrada explícita antes do cálculo', async () => {
  const send = vi.spyOn(api, 'send'); form()
  expect(screen.getByLabelText('Limite diário (min)')).toHaveValue(null)
  expect(screen.getByLabelText('Descanso entre jornadas (min)')).toHaveValue(null)
  await userEvent.click(screen.getByRole('button', { name: 'Enviar para cálculo' }))
  expect(send).not.toHaveBeenCalled()
})
it('envia hipótese com minutos, cargos e pausas sem validar premissas automaticamente', async () => {
  const send = vi.spyOn(api, 'send').mockResolvedValue({ id: 'job', state: 'queued' }); const saved = form(previous)
  await userEvent.click(screen.getByRole('button', { name: 'Enviar para cálculo' }))
  await waitFor(() => expect(saved).toHaveBeenCalledOnce())
  expect(send.mock.calls[0][2]).toMatchObject({ scenario_id: 's', mode: 'diagnostic', activity_job_role_ids: { '0': ['role'] }, limits: { validation_status: 'pending_review', min_rest_minutes: 660 }, templates: [{ break_minutes: 30, break_after_minutes: 240 }] })
  expect(typeof send.mock.calls[0][3]).toBe('string')
})
it('deriva uma nova versão vinculada à proposta anterior', async () => {
  const send = vi.spyOn(api, 'send').mockResolvedValue({ id: 'job2' }); form(previous, 'parent')
  await userEvent.click(screen.getByRole('button', { name: 'Enviar para cálculo' }))
  await waitFor(() => expect(send).toHaveBeenCalledOnce())
  expect(send.mock.calls[0][2]).toMatchObject({ parent_schedule_id: 'parent', scenario_id: 's' })
})
it('preserva os dados do formulário quando há conflito de referência', async () => {
  vi.spyOn(api, 'send').mockRejectedValue(new ApiError(409, 'STALE_INPUTS', 'Dados mudaram. Gere uma nova versão.')); form(previous)
  await userEvent.click(screen.getByRole('button', { name: 'Enviar para cálculo' }))
  expect(await screen.findByText('Dados mudaram. Gere uma nova versão.')).toBeInTheDocument()
  expect(screen.getByLabelText('Nome do cálculo')).toHaveValue('Cálculo de cobertura')
})
it('exibe ausência de cenários sem apresentar cobertura presumida', async () => {
  vi.spyOn(api, 'get').mockResolvedValue({ items: [], total: 0, page: 1, page_size: 100 }); mount(<OptimizationPage />)
  expect(await screen.findByText('cenário com atividades e demanda')).toHaveAttribute('href', '/cenarios')
  expect(screen.getByRole('button', { name: 'Configurar otimização' })).toBeDisabled()
})
it('distingue tempo limite sem conclusão de inviabilidade', async () => {
  vi.spyOn(api, 'get').mockImplementation(async path => {
    if (path === '/optimization/job') return { id: 'job', state: 'succeeded', name: 'Sem conclusão', unit_id: 'unit', attempts: 1, result: { solver_status: 'UNKNOWN', seconds: 20, variables: 100, coverage_cells: 30, approval_blockers: [], stages: [], candidate_rejections: {}, verification: { valid: false } } } as never
    if (path.startsWith('/optimization?')) return { items: [{ id: 'job', state: 'succeeded', name: 'Sem conclusão' }], total: 1 } as never
    return { items: [], total: 0 } as never
  })
  mount(<OptimizationPage />)
  await screen.findByRole('option', { name: 'Sem conclusão · Cálculo concluído' })
  fireEvent.change(screen.getByLabelText('Processamento para consultar'), { target: { value: 'job' } })
  expect(await screen.findByText('Limite atingido sem conclusão de viabilidade')).toBeInTheDocument()
  expect(screen.queryByText('Não há solução para as restrições informadas')).not.toBeInTheDocument()
})
it('mostra a pausa fora da cobertura e identifica a alocação', () => {
  render(<AssignmentTable people={[]} items={[{ candidate_id: 1, employee_id: 'p', activity_index: 0, department_id: 'd', label: 'Diurno', start_at: '2026-11-02T08:00:00-03:00', end_at: '2026-11-02T16:00:00-03:00', breaks: [{ start_at: '2026-11-02T12:00:00-03:00', end_at: '2026-11-02T12:30:00-03:00', paid: false }] }]} />)
  expect(screen.getByRole('table')).toHaveAccessibleName('Alocações propostas')
  expect(screen.getByText('Diurno')).toBeInTheDocument()
})
