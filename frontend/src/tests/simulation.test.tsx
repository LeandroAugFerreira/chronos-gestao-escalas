import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, it, vi } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { FinancialForm, ScenarioForm } from '../components/simulation-forms'
import { FinancialPage, ProjectionView, ScenariosPage } from '../pages/simulation'
import { api, ApiError } from '../services/client'
import { money, type Projection, type Scenario } from '../types/simulation'

vi.mock('../hooks/auth', () => ({ useAuth: () => ({ user: { permissions: { 'scenario:read': null, 'scenario:write': null, 'finance:read': null, 'finance:simulate': null } } }) }))
vi.mock('recharts', () => ({ ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>, BarChart: () => <div />, Bar: () => null, XAxis: () => null, YAxis: () => null, Tooltip: () => null, CartesianGrid: () => null }))
const unit = { id: 'u1', name: 'Unidade de teste', timezone: 'America/Sao_Paulo', operation: '24x7', revision: 1 }
const dept = { id: 'd1', name: 'Operações', unit_id: 'u1', group: 'Operacional', operation: '24x7', cost_center: '', revision: 1 }
const scenario: Scenario = { id: 's1', unit_id: 'u1', department_id: null, key: 'horas-40', version: 1, parent_id: null, name: 'Hipótese de jornada', reference_month: '2026-11-01', created_at: '2026-10-24T00:00:00Z', digest: 'a'.repeat(64) }
const projection: Projection = { currency: 'BRL', months: [{ index: 1, month: '2026-11', existing_payroll_cents: 10000, new_hire_payroll_cents: 0, base_payroll_cents: 10000, average_headcount: '1', contract_days_missing: 0, total_cents: 20000, components: [{ component_index: 0, name: 'Treinamento único', category: 'training', amount_cents: 10000 }] }], annual_total_cents: 130000, annual_base_payroll_cents: 120000, annual_components_cents: { training: 10000 }, monthly_average_cents: 10833, missing_categories: ['charge'], rounding: 'Arredondamento por componente', scope: 'Hipótese documentada', source: 'Orçamento sintético', notices: [] }
beforeEach(() => { vi.restoreAllMocks() })
function mount(node: React.ReactNode) { const cache = new QueryClient({ defaultOptions: { queries: { retry: false } } }); return render(<QueryClientProvider client={cache}><MemoryRouter>{node}</MemoryRouter></QueryClientProvider>) }
function scenarioForm(previous?: Scenario) { const onSaved = vi.fn(); render(<ScenarioForm previous={previous} units={[unit]} departments={[dept]} patterns={[]} skills={[]} qualifications={[]} onSaved={onSaved} onPending={vi.fn()} />); return onSaved }
async function fillScenario() {
  await userEvent.type(screen.getByLabelText('Nome do cenário'), 'Jornada hipotética')
  await userEvent.type(screen.getByLabelText('Grupo do cenário'), 'jornada-40')
  fireEvent.change(screen.getByLabelText('Mês de referência'), { target: { value: '2026-11' } })
  await userEvent.type(screen.getByLabelText('Fonte e condições da hipótese'), 'Hipótese sintética para comparar jornadas')
}
async function fillFinancial() {
  await userEvent.type(screen.getByLabelText('Nome da projeção'), 'Projeção hipotética')
  await userEvent.type(screen.getByLabelText('Fonte e escopo financeiro'), 'Premissas hipotéticas de custos')
}
it('formata centavos exatos inclusive limite elevado e negativos menores que um real', () => {
  expect(money(9000000000000001)).toContain('90.000.000.000.000,01')
  expect(money(-1)).toContain('-R$')
  expect(money(-1)).toContain('0,01')
})
it('exige fonte e cria cenário em minutos sem incluir salários no corpo', async () => {
  const send = vi.spyOn(api, 'send').mockResolvedValue({ id: 's1' })
  const saved = scenarioForm(); await userEvent.click(screen.getByRole('button', { name: 'Calcular e salvar versão 1' }))
  expect(await screen.findByText('Informe a fonte ou descreva a hipótese.')).toBeInTheDocument()
  expect(send).not.toHaveBeenCalled()
  await fillScenario(); await userEvent.type(screen.getByLabelText('Meta semanal em horas (opcional)'), '40')
  await userEvent.click(screen.getByRole('button', { name: 'Calcular e salvar versão 1' }))
  await waitFor(() => expect(saved).toHaveBeenCalledOnce())
  expect(send.mock.calls[0][2]).toMatchObject({ reference_month: '2026-11-01', target_weekly_minutes: 2400, source: 'Hipótese sintética para comparar jornadas' })
  expect(JSON.stringify(send.mock.calls[0][2])).not.toContain('salary')
})
it('deriva próxima versão normalizando referências opcionais nulas', async () => {
  const send = vi.spyOn(api, 'send').mockResolvedValue({ id: 's2' })
  const previous = { ...scenario, inputs: { ...scenario, source: 'Fonte sintética de origem', mode: 'calendar', work_pattern_id: null, cycle_anchor: null, start_time: '08:00', break_minutes: 0, eligibility: 'verified', target_weekly_minutes: 2400, demands: [] } }
  const saved = scenarioForm(previous)
  await userEvent.click(screen.getByRole('button', { name: 'Calcular e salvar versão 2' }))
  await waitFor(() => expect(saved).toHaveBeenCalledOnce())
  expect(send.mock.calls[0][2]).toMatchObject({ parent_id: 's1', version: 2, key: 'horas-40' })
})
it('mantém formulário quando cálculo do cenário falha', async () => {
  vi.spyOn(api, 'send').mockRejectedValue(new ApiError(422, 'PATTERN_CONFIGURATION_REQUIRED', 'Configure o ciclo antes de simular.'))
  const saved = scenarioForm(); await fillScenario(); await userEvent.click(screen.getByRole('button', { name: 'Calcular e salvar versão 1' }))
  expect(await screen.findByText('Configure o ciclo antes de simular.')).toBeInTheDocument()
  expect(saved).not.toHaveBeenCalled()
  expect(screen.getByLabelText('Nome do cenário')).toHaveValue('Jornada hipotética')
})
it('financeiro avalia antes de persistir e invalida prévia ao editar', async () => {
  const send = vi.spyOn(api, 'send').mockResolvedValue(projection); const preview = vi.fn(); const saved = vi.fn()
  render(<FinancialForm scenario={scenario} onSaved={saved} onPending={vi.fn()} onPreview={preview} />)
  await fillFinancial(); await userEvent.click(screen.getByRole('button', { name: 'Calcular prévia financeira' }))
  await screen.findByRole('button', { name: 'Salvar projeção imutável' })
  expect(send.mock.calls[0][0]).toBe('/financial/preview')
  expect(saved).not.toHaveBeenCalled()
  await userEvent.type(screen.getByLabelText('Nome da projeção'), ' alterada')
  expect(screen.getByRole('button', { name: 'Calcular prévia financeira' })).toBeInTheDocument()
})
it('parcela única é enviada como centavos e recorrência explícita', async () => {
  const send = vi.spyOn(api, 'send').mockResolvedValueOnce(projection).mockResolvedValueOnce({ id: 'f1' }); const saved = vi.fn()
  render(<FinancialForm scenario={scenario} onSaved={saved} onPending={vi.fn()} onPreview={vi.fn()} />)
  await fillFinancial(); await userEvent.click(screen.getByRole('button', { name: 'Adicionar parcela' }))
  await userEvent.type(screen.getByLabelText('Nome da parcela 1'), 'Transição única')
  await userEvent.clear(screen.getByLabelText('Valor em centavos 1')); await userEvent.type(screen.getByLabelText('Valor em centavos 1'), '10000')
  await userEvent.selectOptions(screen.getByLabelText('Recorrência 1'), 'once')
  await userEvent.type(screen.getByLabelText('Fonte da parcela 1'), 'Orçamento sintético de treinamento')
  await userEvent.click(screen.getByRole('button', { name: 'Calcular prévia financeira' }))
  await screen.findByRole('button', { name: 'Salvar projeção imutável' })
  expect(send.mock.calls[0][2]).toMatchObject({ components: [expect.objectContaining({ amount_cents: 10000, recurrence: 'once' })] })
  await userEvent.click(screen.getByRole('button', { name: 'Salvar projeção imutável' }))
  await waitFor(() => expect(saved).toHaveBeenCalledOnce())
  expect(send.mock.calls[1][0]).toBe('/financial')
})
it('mostra total anual recebido sem multiplicar parcela única por doze', () => {
  render(<ProjectionView result={projection} />)
  expect(screen.getAllByText(/R\$\s1\.300,00/).length).toBeGreaterThan(0)
  expect(screen.getByText(/Encargos/)).toBeInTheDocument()
  expect(screen.queryByText(/R\$\s2\.400,00/)).not.toBeInTheDocument()
})
it('trocar para cálculo de horas exige informar o divisor, sem valor universal preenchido', async () => {
  const send = vi.spyOn(api, 'send').mockResolvedValue(projection)
  render(<FinancialForm scenario={scenario} onSaved={vi.fn()} onPending={vi.fn()} onPreview={vi.fn()} />)
  await fillFinancial(); await userEvent.click(screen.getByRole('button', { name: 'Adicionar parcela' }))
  await userEvent.selectOptions(screen.getByLabelText('Tipo de cálculo 1'), 'hours')
  expect(screen.getByLabelText('Divisor mensal em minutos 1')).toHaveValue(0)
  await userEvent.type(screen.getByLabelText('Nome da parcela 1'), 'Adicional hipotético')
  await userEvent.type(screen.getByLabelText('Fonte da parcela 1'), 'Premissa de teste condicionada à revisão')
  await userEvent.click(screen.getByRole('button', { name: 'Calcular prévia financeira' }))
  expect(send).not.toHaveBeenCalled()
  await userEvent.selectOptions(screen.getByLabelText('Tipo de cálculo 1'), 'fixed')
  await userEvent.click(screen.getByRole('button', { name: 'Calcular prévia financeira' }))
  await screen.findByRole('button', { name: 'Salvar projeção imutável' })
  expect(send.mock.calls[0][2]).toMatchObject({ components: [expect.objectContaining({ kind: 'fixed', monthly_divisor_minutes: 1 })] })
})
it('cenários e financeiro vazios identificam pré-requisitos', async () => {
  vi.spyOn(api, 'get').mockImplementation(async path => { const items = path.startsWith('/units') ? [unit] : path.startsWith('/departments') ? [dept] : []; return { items, total: items.length, page: 1, page_size: 100 } })
  const first = mount(<ScenariosPage />)
  expect(await screen.findByText(/Nenhum cenário calculado/)).toBeInTheDocument(); first.unmount()
  mount(<FinancialPage />)
  expect(await screen.findByText(/Crie primeiro um cenário/)).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Configurar projeção' })).toBeDisabled()
})
