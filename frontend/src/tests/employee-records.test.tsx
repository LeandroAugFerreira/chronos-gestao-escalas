import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, it, vi } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ContractForm, EmployeeRecords, QualificationForm, SkillForm, salaryCents } from '../components/employee-records'
import { api, ApiError } from '../services/client'
import type { Employee } from '../types/domain'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { EmployeeDetailPage } from '../pages/employees'

const auth = vi.hoisted(() => ({ user: { permissions: {} as Record<string, string[] | null> } }))
vi.mock('../hooks/auth', () => ({ useAuth: () => auth }))
const employee: Employee = { id: 'e1', organization_id: 'org', name: 'Pessoa fictícia', registration: 'HM001', unit_id: 'u1', department_id: 'd1', job_role_id: 'r1', status: 'active', synthetic: true, revision: 1 }
const patterns = [{ id: 'p1', name: 'Jornada sintética', legal_status: 'pending_review' }]
const actions = () => ({ employeeId: 'e1', onSaved: vi.fn(), onPending: vi.fn() })
function mountRecords() { const cache = new QueryClient({ defaultOptions: { queries: { retry: false } } }); return render(<QueryClientProvider client={cache}><EmployeeRecords employee={employee} /></QueryClientProvider>) }
beforeEach(() => {
  vi.restoreAllMocks()
  auth.user.permissions = { 'people:read': null, 'people:write': ['u1'], 'catalog:read': null, 'finance:read': ['u1'] }
  vi.spyOn(api, 'send').mockResolvedValue({ id: 'new' })
  vi.spyOn(api, 'get').mockImplementation(async path => {
    if (path.startsWith('/catalogs/work-patterns')) return { items: patterns, total: 1 } as never
    if (path.startsWith('/catalogs/qualifications')) return { items: [{ id: 'q1', name: 'Habilitação sintética' }], total: 1 } as never
    if (path.startsWith('/catalogs/skills')) return { items: [{ id: 's1', name: 'Existente' }, { id: 's2', name: 'Nova competência' }], total: 2 } as never
    if (path.endsWith('/skills')) return { items: [{ id: 'sk1', skill_id: 's1' }] } as never
    if (path.endsWith('/qualifications')) return { items: [{ id: 'qual1', qualification_id: 'q1', valid_from: '2026-01-01', valid_until: '2027-01-01', evidence: 'Evidência fictícia', verification_status: 'validated' }] } as never
    if (path.endsWith('/contracts')) return { items: [{ id: 'c1', work_pattern_id: 'p1', weekly_minutes: 2400, base_salary_cents: 150001, currency: 'BRL', employment_type: 'teste', valid_from: '2026-01-01', valid_until: null, validation_status: 'validated', assumption_source: 'Contrato sintético' }] } as never
    throw new Error('Rota inesperada')
  })
})

async function fillContract() {
  await userEvent.selectOptions(screen.getByLabelText('Jornada de referência'), 'p1')
  fireEvent.change(screen.getByLabelText('Carga semanal (minutos)'), { target: { value: '2400' } })
  await userEvent.type(screen.getByLabelText('Salário-base (R$)'), '1500,01')
  await userEvent.type(screen.getByLabelText('Tipo de vínculo'), 'teste')
  fireEvent.change(screen.getByLabelText('Início da vigência'), { target: { value: '2026-11-01' } })
  await userEvent.type(screen.getByLabelText('Fonte do contrato'), 'Hipótese sintética documentada')
}

it.each([['0', 0], ['0,29', 29], ['1500,01', 150001], ['1500.01', 150001], ['21474836,47', 2147483647]] as const)('converte %s sem arredondamento binário', (input, cents) => { expect(salaryCents(input)).toBe(cents) })
it.each(['1.234,56', '-1', '1,001', '21474836,48', 'NaN'])('recusa salário inválido %s', value => { expect(() => salaryCents(value)).toThrow() })

it('envia contrato em centavos, vigência aberta e sem validação implícita', async () => {
  const callbacks = actions(); render(<ContractForm patterns={patterns} {...callbacks} />)
  await fillContract(); await userEvent.click(screen.getByRole('button', { name: 'Cadastrar contrato' }))
  await waitFor(() => expect(callbacks.onSaved).toHaveBeenCalledOnce())
  expect(api.send).toHaveBeenCalledWith('/employees/e1/contracts', 'POST', { work_pattern_id: 'p1', weekly_minutes: 2400, base_salary_cents: 150001, employment_type: 'teste', valid_from: '2026-11-01', valid_until: null, assumption_source: 'Hipótese sintética documentada' }, expect.any(String))
})

it('mantém formulário no conflito de vigência e exige fim exclusivo posterior', async () => {
  const callbacks = actions(); vi.mocked(api.send).mockRejectedValue(new ApiError(409, 'OVERLAPPING_CONTRACT', 'Existe contrato sobreposto.'))
  render(<ContractForm patterns={patterns} {...callbacks} />); await fillContract()
  fireEvent.change(screen.getByLabelText('Fim exclusivo (opcional)'), { target: { value: '2026-11-01' } })
  await userEvent.click(screen.getByRole('button', { name: 'Cadastrar contrato' }))
  expect(await screen.findByText('O fim exclusivo deve ser posterior ao início.')).toBeInTheDocument(); expect(api.send).not.toHaveBeenCalled()
  fireEvent.change(screen.getByLabelText('Fim exclusivo (opcional)'), { target: { value: '2026-12-01' } })
  await userEvent.click(screen.getByRole('button', { name: 'Cadastrar contrato' }))
  expect(await screen.findByText('Existe contrato sobreposto.')).toBeInTheDocument(); expect(callbacks.onSaved).not.toHaveBeenCalled()
  expect(screen.getByLabelText('Salário-base (R$)')).toHaveValue('1500,01')
})

it('preserva chave ao repetir pedido após falha de rede e troca ao editar conteúdo', async () => {
  vi.mocked(api.send).mockRejectedValue(new ApiError(0, 'NETWORK_ERROR', 'Sem conexão'))
  render(<ContractForm patterns={patterns} {...actions()} />); await fillContract()
  await userEvent.click(screen.getByRole('button', { name: 'Cadastrar contrato' })); await screen.findByText('Sem conexão')
  const key = vi.mocked(api.send).mock.calls[0][3]
  await userEvent.click(screen.getByRole('button', { name: 'Cadastrar contrato' })); await waitFor(() => expect(api.send).toHaveBeenCalledTimes(2))
  expect(vi.mocked(api.send).mock.calls[1][3]).toBe(key)
  await userEvent.clear(screen.getByLabelText('Salário-base (R$)')); await userEvent.type(screen.getByLabelText('Salário-base (R$)'), '1600,02')
  await userEvent.click(screen.getByRole('button', { name: 'Cadastrar contrato' })); await waitFor(() => expect(api.send).toHaveBeenCalledTimes(3))
  expect(vi.mocked(api.send).mock.calls[2][3]).not.toBe(key)
})

it('registra qualificação sem promover a validação', async () => {
  const callbacks = actions(); render(<QualificationForm qualifications={[{ id: 'q1', name: 'Habilitação sintética' }]} {...callbacks} />)
  await userEvent.selectOptions(screen.getByLabelText('Qualificação'), 'q1')
  fireEvent.change(screen.getByLabelText('Início da validade'), { target: { value: '2026-11-01' } })
  fireEvent.change(screen.getByLabelText('Fim exclusivo da validade'), { target: { value: '2027-11-01' } })
  await userEvent.type(screen.getByLabelText('Evidência da qualificação'), 'Documento fictício de teste')
  await userEvent.click(screen.getByRole('button', { name: 'Cadastrar qualificação' }))
  await waitFor(() => expect(callbacks.onSaved).toHaveBeenCalledOnce())
  expect(api.send).toHaveBeenCalledWith('/employees/e1/qualifications', 'POST', { qualification_id: 'q1', valid_from: '2026-11-01', valid_until: '2027-11-01', evidence: 'Documento fictício de teste' }, expect.any(String))
})

it('bloqueia envios simultâneos e campos enquanto salva a competência', async () => {
  let resolve!: (value: unknown) => void; vi.mocked(api.send).mockReturnValue(new Promise(value => { resolve = value }))
  const callbacks = actions(); const { container } = render(<SkillForm skills={[{ id: 's2', name: 'Nova competência' }]} {...callbacks} />)
  await userEvent.selectOptions(screen.getByLabelText('Competência'), 's2')
  fireEvent.submit(container.querySelector('form')!); fireEvent.submit(container.querySelector('form')!)
  await waitFor(() => expect(api.send).toHaveBeenCalledOnce())
  expect(screen.getByLabelText('Competência')).toBeDisabled(); expect(callbacks.onPending).toHaveBeenCalledWith(true)
  resolve({ id: 'new' }); await waitFor(() => expect(callbacks.onSaved).toHaveBeenCalledOnce())
})

it('não consulta salários quando a permissão financeira pertence a outra unidade', async () => {
  auth.user.permissions['finance:read'] = ['u2']; mountRecords()
  expect(await screen.findByText('Habilitação sintética')).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Adicionar contrato' })).not.toBeInTheDocument()
  expect(screen.queryByRole('heading', { name: 'Contratos' })).not.toBeInTheDocument()
  expect(vi.mocked(api.get).mock.calls.some(([path]) => path.endsWith('/contracts'))).toBe(false)
})

it('apresenta os estados revisados reais e oculta escrita sem permissão', async () => {
  delete auth.user.permissions['people:write']; mountRecords()
  await screen.findByText('Contrato sintético')
  expect(screen.getAllByText('Validado')).toHaveLength(2)
  expect(screen.queryByText('Revisão pendente')).not.toBeInTheDocument()
  expect(screen.queryByRole('button', { name: /Adicionar/ })).not.toBeInTheDocument()
})

it('lista competências por nome e exclui vínculos já existentes das opções', async () => {
  mountRecords(); await screen.findByText('Existente')
  await userEvent.click(screen.getByRole('button', { name: 'Adicionar competência' }))
  expect(await screen.findByRole('dialog', { name: 'Adicionar competência' })).toBeInTheDocument()
  expect(screen.queryByRole('option', { name: 'Existente' })).not.toBeInTheDocument()
  expect(screen.getByRole('option', { name: 'Nova competência' })).toBeInTheDocument()
})

it('integra os vínculos no detalhe e registra indisponibilidade no fuso da unidade', async () => {
  const original = vi.mocked(api.get).getMockImplementation()!
  vi.mocked(api.get).mockImplementation(async (path, signal) => {
    if (path === '/employees/e1') return employee as never
    if (path.startsWith('/units')) return { items: [{ id: 'u1', name: 'Unidade fictícia', timezone: 'America/Manaus' }], total: 1 } as never
    if (path.startsWith('/departments') || path.startsWith('/catalogs/job-roles')) return { items: [], total: 0 } as never
    if (path.endsWith('/availability')) return { items: [] } as never
    return original(path, signal)
  })
  const cache = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(<QueryClientProvider client={cache}><MemoryRouter initialEntries={['/colaboradores/e1']}><Routes><Route path="/colaboradores/:id" element={<EmployeeDetailPage />} /></Routes></MemoryRouter></QueryClientProvider>)
  expect(await screen.findByRole('button', { name: 'Adicionar contrato' })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Adicionar qualificação' })).toBeInTheDocument()
  await userEvent.click(await screen.findByText('Indisponibilidades · Pessoa fictícia'))
  expect(screen.getByText(/Fuso America\/Manaus/)).toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('Início da indisponibilidade'), { target: { value: '2026-11-02T08:00' } })
  fireEvent.change(screen.getByLabelText('Fim da indisponibilidade'), { target: { value: '2026-11-02T09:00' } })
  await userEvent.click(screen.getByRole('button', { name: 'Registrar indisponibilidade' }))
  await waitFor(() => expect(api.send).toHaveBeenCalledWith('/employees/e1/availability', 'POST', expect.objectContaining({ start_at: '2026-11-02T12:00:00.000Z', end_at: '2026-11-02T13:00:00.000Z', type: 'unavailable' }), expect.any(String)))
})
