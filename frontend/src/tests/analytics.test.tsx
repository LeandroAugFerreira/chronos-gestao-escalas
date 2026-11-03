import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, it, vi } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { AnalyticsPage, ReportView, saveReport, type AnalyticsReport } from '../pages/analytics'
import { api, ApiError } from '../services/client'

const state = vi.hoisted(() => ({ user: { permissions: {} as Record<string, string[] | null> } }))
vi.mock('../hooks/auth', () => ({ useAuth: () => state }))
const data: AnalyticsReport = {
  manifest: { extracted_at: '2026-10-25T12:00:00Z', data_sha256: 'abc', timezone: 'America/Sao_Paulo', period_start_utc: '2026-11-01T03:00:00Z', period_end_utc_exclusive: '2026-12-01T03:00:00Z',
    columns: { scenario: ['scenario_id', 'effective_budget_minutes'], executions: ['execution_id'] }, grains: { scenario: 'Uma versão de cenário', executions: 'Uma tentativa' }, methodology: ['Custos projetados; sem economia comprovada.'] },
  tables: { scenario: [{ scenario_id: 's1', effective_budget_minutes: 480 }], executions: [] },
  explanation: { paragraphs: ['Capacidade agregada não garante cobertura.'], limits: 'Sem envio a serviço externo.' },
}
function mount() { const cache = new QueryClient({ defaultOptions: { queries: { retry: false } } }); return render(<QueryClientProvider client={cache}><MemoryRouter><AnalyticsPage /></MemoryRouter></QueryClientProvider>) }
beforeEach(() => {
  vi.restoreAllMocks(); vi.unstubAllGlobals()
  state.user.permissions = { 'scenario:read': null, 'optimization:read': null }
  vi.spyOn(api, 'get').mockImplementation(async path => {
    if (path.startsWith('/units')) return { items: [{ id: 'u1', name: 'Unidade sintética' }], total: 1 } as never
    if (path.startsWith('/analytics/history')) return { items: [{ id: 's1', name: 'Hipótese', key: 'base', version: 2, reference_month: '2026-11-01' }], total: 1 } as never
    if (path.startsWith('/analytics/options')) return { optimization: [{ id: 'o1', name: 'Cálculo', state: 'queued' }], financial: [] } as never
    throw new Error('Rota inesperada')
  })
  vi.spyOn(api, 'send').mockResolvedValue(data)
})

it('exige seleção explícita e limpa cenário ao mudar o período', async () => {
  mount()
  expect(screen.getByRole('button', { name: 'Exportar XLSX' })).toBeDisabled()
  expect(api.send).not.toHaveBeenCalled()
  await screen.findByRole('option', { name: 'Unidade sintética' })
  await userEvent.selectOptions(screen.getByLabelText('Unidade do relatório'), 'u1')
  await screen.findByRole('option', { name: /Hipótese/ })
  await userEvent.selectOptions(screen.getByLabelText('Cenário e versão'), 's1')
  expect(await screen.findByText('O que esta seleção mostra')).toBeInTheDocument()
  expect(api.send).toHaveBeenCalledWith('/analytics/report', 'POST', { scenario_id: 's1', optimization_id: null, financial_id: null, include_people: false })
  expect(screen.queryByLabelText('Projeção do relatório')).not.toBeInTheDocument()
  expect(screen.queryByRole('checkbox')).not.toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('Mês de referência'), { target: { value: '2026-12' } })
  await waitFor(() => expect(screen.queryByText('O que esta seleção mostra')).not.toBeInTheDocument())
  expect(screen.getByRole('button', { name: 'Exportar XLSX' })).toBeDisabled()
})

it('mantém informação indisponível separada de zero e mostra tabela vazia', async () => {
  render(<ReportView report={data} />)
  expect(screen.getAllByText('—')).toHaveLength(2)
  expect(screen.getByText('0')).toBeInTheDocument()
  expect(screen.getByText('Sem envio a serviço externo.')).toBeInTheDocument()
  await userEvent.selectOptions(screen.getByLabelText('Tabela do relatório'), 'executions')
  expect(screen.getByText('Sem registros nesta tabela.')).toBeInTheDocument()
})

it('mostra custo somente quando a projeção está presente no relatório', () => {
  render(<ReportView report={{ ...data, tables: { ...data.tables, finance: [{ total_cents: 101 }, { total_cents: 199 }] } }} />)
  expect(screen.getByText(/R\$\s*3,00/)).toBeInTheDocument()
})

it('exibe falha da API e impede exportação de relatório recusado', async () => {
  vi.mocked(api.send).mockRejectedValue(new ApiError(403, 'FORBIDDEN', 'Permissão insuficiente para esta unidade.'))
  mount()
  await screen.findByRole('option', { name: 'Unidade sintética' })
  await userEvent.selectOptions(screen.getByLabelText('Unidade do relatório'), 'u1')
  await screen.findByRole('option', { name: /Hipótese/ })
  await userEvent.selectOptions(screen.getByLabelText('Cenário e versão'), 's1')
  expect(await screen.findByText('Permissão insuficiente para esta unidade.')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'CSV e Power BI' })).toBeDisabled()
})

it('verifica bytes e SHA-256 antes de oferecer o arquivo', async () => {
  const moduleName = 'node:crypto'
  const { webcrypto } = await import(/* @vite-ignore */ moduleName)
  vi.stubGlobal('crypto', webcrypto)
  const create = vi.fn(() => 'blob:report'); const revoke = vi.fn()
  vi.stubGlobal('URL', class extends URL { static createObjectURL = create; static revokeObjectURL = revoke })
  const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
  const file = { filename: 'chronos-1.0.xlsx', content_type: 'application/octet-stream', content: 'YWJj', byte_length: 3, sha256: 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad' }
  await saveReport(file)
  expect(create).toHaveBeenCalledOnce(); expect(click).toHaveBeenCalledOnce()
  await expect(saveReport({ ...file, sha256: 'invalid' })).rejects.toThrow('integridade')
  await expect(saveReport({ ...file, byte_length: 9 })).rejects.toThrow('integridade')
  expect(click).toHaveBeenCalledOnce()
})

it('inclui pessoas somente por opção explícita e limpa a opção ao trocar a execução', async () => {
  state.user.permissions['people:read'] = null
  mount()
  await screen.findByRole('option', { name: 'Unidade sintética' })
  await userEvent.selectOptions(screen.getByLabelText('Unidade do relatório'), 'u1')
  await screen.findByRole('option', { name: /Hipótese/ })
  await userEvent.selectOptions(screen.getByLabelText('Cenário e versão'), 's1')
  await screen.findByRole('option', { name: /Cálculo/ })
  await userEvent.selectOptions(screen.getByLabelText('Otimização do relatório'), 'o1')
  const checkbox = await screen.findByRole('checkbox')
  expect(checkbox).not.toBeChecked()
  await userEvent.click(checkbox)
  await waitFor(() => expect(api.send).toHaveBeenLastCalledWith('/analytics/report', 'POST', expect.objectContaining({ include_people: true, optimization_id: 'o1' })))
  await userEvent.selectOptions(screen.getByLabelText('Otimização do relatório'), '')
  await waitFor(() => expect(api.send).toHaveBeenLastCalledWith('/analytics/report', 'POST', expect.objectContaining({ include_people: false, optimization_id: null })))
  expect(screen.queryByRole('checkbox')).not.toBeInTheDocument()
})

it('informa falha de exportação sem confirmar download', async () => {
  vi.mocked(api.send).mockImplementation(async path => {
    if (path === '/analytics/export') throw new ApiError(422, 'REPORT_LIMIT', 'O relatório excede o limite.')
    return data as never
  })
  mount()
  await screen.findByRole('option', { name: 'Unidade sintética' })
  await userEvent.selectOptions(screen.getByLabelText('Unidade do relatório'), 'u1')
  await screen.findByRole('option', { name: /Hipótese/ })
  await userEvent.selectOptions(screen.getByLabelText('Cenário e versão'), 's1')
  await waitFor(() => expect(screen.getByRole('button', { name: 'CSV e Power BI' })).toBeEnabled())
  await userEvent.click(screen.getByRole('button', { name: 'CSV e Power BI' }))
  expect(await screen.findByText('O relatório excede o limite.')).toBeInTheDocument()
  expect(screen.queryByText(/Arquivo verificado/)).not.toBeInTheDocument()
})
