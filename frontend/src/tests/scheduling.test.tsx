import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, it, vi } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { CalendarPage, RuleForm, ShiftForm } from '../pages/scheduling'
import { api, ApiError } from '../services/client'
import { calendarDays, civilToISO } from '../services/calendar'
import type { Employee } from '../types/domain'
import type { Shift } from '../types/scheduling'

vi.mock('../hooks/auth', () => ({ useAuth: () => ({ user: { permissions: { 'schedule:read': null, 'schedule:write': null, 'people:read': null, 'rules:write': null } } }) }))
const unit = { id: 'u1', name: 'Unidade 1', timezone: 'America/Sao_Paulo', operation: '24x7', revision: 1 }
const dept = { id: 'd1', name: 'Operações', unit_id: 'u1', group: 'Operacional', operation: '24x7', cost_center: '', revision: 1 }
const person: Employee = { id: 'e1', organization_id: 'o1', unit_id: 'u1', department_id: 'd1', job_role_id: 'r1', name: 'Pessoa de teste', registration: 'HH1', status: 'active', synthetic: true, revision: 1 }
const result = { status: 'pending', label: 'Pendente de validação jurídica', actual_minutes: 480, payable_minutes: 480, elapsed_minutes: 480, digest: 'a'.repeat(64), scope: 'Planejamento conhecido', findings: [{ code: 'RULE_MISSING', status: 'missing', message: 'Regra ausente', evidence: { kind: 'min_rest' } }] }
beforeEach(() => { vi.restoreAllMocks() })
function form() { const onSaved = vi.fn(); render(<ShiftForm unit={unit} employees={[person]} departments={[dept]} onSaved={onSaved} onPending={vi.fn()} />); return onSaved }
async function fillShift() {
  await userEvent.selectOptions(screen.getByLabelText('Colaborador'), 'e1')
  await userEvent.selectOptions(screen.getByLabelText('Setor de atuação'), 'd1')
  fireEvent.change(screen.getByLabelText('Início'), { target: { value: '2026-11-02T08:00' } })
  fireEvent.change(screen.getByLabelText('Fim'), { target: { value: '2026-11-02T16:00' } })
}
it('converte fuso explicitamente, rejeita horários de verão ambíguos e cruza mês bissexto', () => {
  expect(civilToISO('2026-11-02T08:00', 'America/Sao_Paulo')).toBe('2026-11-02T11:00:00.000Z')
  expect(() => civilToISO('2026-03-08T02:30', 'America/New_York')).toThrow('inexistente ou ambíguo')
  expect(() => civilToISO('2026-11-01T01:30', 'America/New_York')).toThrow('inexistente ou ambíguo')
  expect(calendarDays('2028-02-10', 'month')).toHaveLength(29)
  expect(calendarDays('2026-11-01', 'week')[0]).toBe('2026-10-26')
})
it('exige avaliar antes de salvar e envia o digest recebido', async () => {
  const send = vi.spyOn(api, 'send').mockResolvedValueOnce(result).mockResolvedValueOnce({ id: 's1' })
  const saved = form(); await fillShift()
  await userEvent.click(screen.getByRole('button', { name: 'Avaliar antes de salvar' }))
  expect(await screen.findByText(result.label)).toBeInTheDocument()
  expect(send).toHaveBeenCalledTimes(1)
  await userEvent.click(screen.getByRole('button', { name: 'Confirmar rascunho com estes alertas' }))
  await waitFor(() => expect(saved).toHaveBeenCalledOnce())
  expect(send.mock.calls[1][2]).toMatchObject({ preview_digest: result.digest, start_at: '2026-11-02T11:00:00.000Z' })
})
it('alteração de campo invalida a prévia anterior', async () => {
  vi.spyOn(api, 'send').mockResolvedValue(result)
  form(); await fillShift(); await userEvent.click(screen.getByRole('button', { name: 'Avaliar antes de salvar' }))
  await screen.findByText(result.label)
  await userEvent.type(screen.getByLabelText('Título do plantão'), ' alterado')
  expect(screen.queryByText(result.label)).not.toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Avaliar antes de salvar' })).toBeInTheDocument()
})
it('prévia expirada mantém formulário e exige reavaliar', async () => {
  vi.spyOn(api, 'send').mockResolvedValueOnce(result).mockRejectedValueOnce(new ApiError(409, 'PREVIEW_EXPIRED', 'Dados mudaram. Avalie novamente.'))
  const saved = form(); await fillShift(); await userEvent.click(screen.getByRole('button', { name: 'Avaliar antes de salvar' }))
  await screen.findByText(result.label); await userEvent.click(screen.getByRole('button', { name: 'Confirmar rascunho com estes alertas' }))
  expect(await screen.findByText('Dados mudaram. Avalie novamente.')).toBeInTheDocument()
  expect(saved).not.toHaveBeenCalled()
  expect(screen.getByLabelText('Título do plantão')).toHaveValue('Plantão')
})
it('intervalos dinâmicos podem ser adicionados e removidos pelo teclado', async () => {
  form(); await userEvent.click(screen.getByRole('button', { name: 'Adicionar intervalo' }))
  expect(screen.getByLabelText('Início da pausa 1')).toBeInTheDocument()
  expect(screen.getByLabelText('Pausa remunerada')).not.toBeChecked()
  await userEvent.click(screen.getByRole('button', { name: 'Remover pausa 1' }))
  expect(screen.queryByLabelText('Início da pausa 1')).not.toBeInTheDocument()
})
it('edição preserva pessoa e revisão e avalia sem contar o próprio plantão', async () => {
  const send = vi.spyOn(api, 'send').mockResolvedValueOnce(result).mockResolvedValueOnce({ id: 's1' })
  const existing: Shift = { id: 's1', employee_id: 'e1', unit_id: 'u1', department_id: 'd1', start_at: '2026-11-02T11:00:00Z', end_at: '2026-11-02T19:00:00Z', label: 'Plantão', breaks: [], state: 'draft', revision: 3, evaluation: result }
  render(<ShiftForm shift={existing} unit={unit} employees={[person]} departments={[dept]} onSaved={vi.fn()} onPending={vi.fn()} />)
  expect(screen.getByLabelText('Colaborador')).toBeDisabled()
  await userEvent.click(screen.getByRole('button', { name: 'Avaliar antes de salvar' }))
  await screen.findByText(result.label)
  expect(send.mock.calls[0][0]).toBe('/calendar/preview?shift_id=s1')
  await userEvent.click(screen.getByRole('button', { name: 'Confirmar rascunho com estes alertas' }))
  await waitFor(() => expect(send).toHaveBeenCalledTimes(2))
  expect(send.mock.calls[1][1]).toBe('PATCH')
  expect(send.mock.calls[1][2]).toMatchObject({ employee_id: 'e1', revision: 3, preview_digest: result.digest })
})
it('exige evidência quando o responsável declara regra validada', async () => {
  const send = vi.spyOn(api, 'send').mockResolvedValue({ id: 'r1' })
  render(<RuleForm units={[unit]} roles={[]} onSaved={vi.fn()} onPending={vi.fn()} />)
  await userEvent.type(screen.getByLabelText('Chave'), 'descanso')
  await userEvent.type(screen.getByLabelText('Fonte e condições de aplicabilidade'), 'Hipótese para teste de regra')
  fireEvent.change(screen.getByLabelText('Início da vigência (UTC)'), { target: { value: '2026-01-01T00:00' } })
  fireEvent.change(screen.getByLabelText('Fim exclusivo da vigência (UTC)'), { target: { value: '2027-01-01T00:00' } })
  await userEvent.selectOptions(screen.getByLabelText('Estado de revisão'), 'validated')
  await userEvent.click(screen.getByRole('button', { name: 'Registrar versão' }))
  expect(await screen.findByText(/Informe responsável, escopo analisado/)).toBeInTheDocument()
  expect(send).not.toHaveBeenCalled()
})
it('calendário vazio alterna semana e mês consultando janela no fuso da unidade', async () => {
  vi.spyOn(api, 'get').mockImplementation(async path => {
    const items = path.startsWith('/units') ? [unit] : path.startsWith('/departments') ? [dept] : path.startsWith('/employees') ? [person] : []
    return { items, total: items.length, page: 1, page_size: 100 }
  })
  const cache = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(<QueryClientProvider client={cache}><CalendarPage /></QueryClientProvider>)
  expect(await screen.findByText(/Nenhum plantão neste período/)).toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('Data de referência'), { target: { value: '2026-11-02' } })
  await userEvent.click(screen.getByRole('button', { name: /^Mês$/ }))
  await waitFor(() => expect(vi.mocked(api.get).mock.calls.some(([path]) => decodeURIComponent(path).includes('start=2026-11-01T03:00:00.000Z') && decodeURIComponent(path).includes('end=2026-12-01T03:00:00.000Z'))).toBe(true))
})
