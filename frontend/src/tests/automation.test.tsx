import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, it, vi } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { AutomationForm, AutomationPage } from '../pages/automation'
import { api, ApiError } from '../services/client'
import { executionSummary, type AutomationDefinition, type AutomationExecution } from '../types/automation'

const state = vi.hoisted(() => ({ user: { id: 'actor', permissions: {} as Record<string, string[] | null> } }))
vi.mock('../hooks/auth', () => ({ useAuth: () => state }))
const definition: AutomationDefinition = { id: 'def', unit_id: 'unit', code: 'A04', name: 'Relatório de indicadores', enabled: false, owner_id: null, interval_minutes: null, next_run_at: null, last_run_at: null, revision: 1, parameters: { lookahead_days: 30, monitor_limit: 100, deliver_n8n: false } }
function mount(node: React.ReactNode) { const cache = new QueryClient({ defaultOptions: { queries: { retry: false } } }); return render(<QueryClientProvider client={cache}><MemoryRouter>{node}</MemoryRouter></QueryClientProvider>) }
beforeEach(() => { vi.restoreAllMocks(); state.user.permissions = { 'automation:read': null, 'automation:manage': null, 'automation:run': null, 'org:read': null }; vi.spyOn(api, 'get').mockImplementation(async path => {
  if (path.startsWith('/automations?') || path === '/automations') return { items: [definition], total: 1, integration_configured: false } as never
  if (path.startsWith('/units')) return { items: [{ id: 'unit', name: 'Unidade sintética' }], total: 1 } as never
  return { items: [], total: 0 } as never
}) })

it('salva a rotina desativada sem atribuir validação ou habilitação implícita', async () => {
  const send = vi.spyOn(api, 'send').mockResolvedValue({}); const saved = vi.fn()
  render(<AutomationForm definition={definition} integrationConfigured={false} onSaved={saved} />)
  expect(screen.getByLabelText('Rotina habilitada')).not.toBeChecked()
  await userEvent.click(screen.getByRole('button', { name: 'Salvar configuração' }))
  await waitFor(() => expect(saved).toHaveBeenCalledOnce())
  expect(send.mock.calls[0][2]).toMatchObject({ revision: 1, enabled: false, owner_id: 'actor', interval_minutes: null, parameters: { deliver_n8n: false } })
})
it('habilita somente após ação explícita e envia a agenda em minutos', async () => {
  const send = vi.spyOn(api, 'send').mockResolvedValue({})
  render(<AutomationForm definition={definition} integrationConfigured={true} onSaved={vi.fn()} />)
  await userEvent.click(screen.getByLabelText('Rotina habilitada'))
  fireEvent.change(screen.getByLabelText('Repetir a cada (minutos; vazio para somente eventos/manual)'), { target: { value: '60' } })
  await userEvent.click(screen.getByRole('button', { name: 'Salvar configuração' }))
  await waitFor(() => expect(send).toHaveBeenCalledOnce())
  expect(send.mock.calls[0][2]).toMatchObject({ enabled: true, interval_minutes: 60 })
})
it('desabilita o encaminhamento quando não há n8n configurado', () => {
  render(<AutomationForm definition={definition} integrationConfigured={false} onSaved={vi.fn()} />)
  expect(screen.getByLabelText('Encaminhar também ao n8n local configurado')).toBeDisabled()
})
it('mantém a configuração quando recebe conflito de revisão', async () => {
  vi.spyOn(api, 'send').mockRejectedValue(new ApiError(409, 'REVISION_CONFLICT', 'A automação mudou. Atualize a configuração.'))
  render(<AutomationForm definition={definition} integrationConfigured={false} onSaved={vi.fn()} />)
  await userEvent.click(screen.getByLabelText('Rotina habilitada'))
  await userEvent.click(screen.getByRole('button', { name: 'Salvar configuração' }))
  expect(await screen.findByText('A automação mudou. Atualize a configuração.')).toBeInTheDocument()
  expect(screen.getByLabelText('Rotina habilitada')).toBeChecked()
})
it('não executa rotinas ao abrir a central e identifica estados vazios', async () => {
  const send = vi.spyOn(api, 'send'); mount(<AutomationPage />)
  expect(await screen.findByRole('button', { name: 'Executar A04' })).toBeDisabled()
  expect(screen.getByText('Nenhum aviso registrado. Isso não comprova cobertura ou conformidade.')).toBeInTheDocument()
  expect(send).not.toHaveBeenCalled()
})
it('oculta configuração e credenciais para leitor agregado', async () => {
  state.user.permissions = { 'automation:read': ['unit'], 'org:read': ['unit'] }; mount(<AutomationPage />)
  await screen.findByRole('table', { name: 'Rotinas A01–A07' })
  expect(screen.queryByRole('button', { name: 'Configurar A04' })).not.toBeInTheDocument()
  expect(screen.queryByText('Credenciais de integração por unidade')).not.toBeInTheDocument()
  expect(vi.mocked(api.get).mock.calls.some(([path]) => path.startsWith('/integration-credentials'))).toBe(false)
})
it('não transforma ausência de cálculo em cobertura completa e mostra consulta parcial', () => {
  const row = { code: 'A02', state: 'succeeded', result: { no_result: true, truncated: true } } as unknown as AutomationExecution
  expect(executionSummary(row)).toContain('Sem cálculo de cobertura disponível.')
  expect(executionSummary(row)).toContain('resultado parcial')
})
it('executa rotina habilitada com revisão e chave de idempotência', async () => {
  vi.mocked(api.get).mockImplementation(async path => path.startsWith('/automations') ? { items: [{ ...definition, enabled: true, revision: 2 }], total: 1, integration_configured: false } as never : { items: [], total: 0 } as never)
  const send = vi.spyOn(api, 'send').mockResolvedValue({ id: 'event' }); mount(<AutomationPage />)
  await userEvent.click(await screen.findByRole('button', { name: 'Executar A04' }))
  await waitFor(() => expect(send).toHaveBeenCalledOnce())
  expect(send.mock.calls[0].slice(0, 3)).toEqual(['/automations/def/run', 'POST', { revision: 2 }])
  expect(typeof send.mock.calls[0][3]).toBe('string')
})
