import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { App } from '../app'
import { api, ApiError } from '../services/client'
import type { Overview, User } from '../types/domain'

const state = vi.hoisted(() => ({ user: null as User | null, message: '', login: vi.fn(), logout: vi.fn() }))
vi.mock('../hooks/auth', () => ({ useAuth: () => ({ ...state, loading: false }) }))
vi.mock('recharts', () => ({ ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>, BarChart: () => <div />, Bar: () => null, XAxis: () => null, YAxis: () => null, Tooltip: () => null, CartesianGrid: () => null }))
const organization = { id: 'org-1', name: 'Serviços Horizonte', segment: 'services', timezone: 'America/Sao_Paulo', operation: '24x7', is_demo: true }
const unit = { id: 'u1', name: 'Unidade 1', timezone: 'America/Sao_Paulo', operation: '24x7', revision: 1 }
const department = { id: 'd1', name: 'Atendimento', unit_id: 'u1', group: 'Operações', operation: '24x7', cost_center: '', revision: 1 }
const person = { id: 'e1', organization_id: 'org-1', name: 'Pessoa Teste', registration: 'HH001', unit_id: 'u1', department_id: 'd1', job_role_id: 'r1', status: 'active', synthetic: true, revision: 1 }
const overview: Overview = { organization, source: 'database', as_of: '2026-10-24T18:00:00Z', unit_id: null, employee_count: 13, active_count: 12, inactive_count: 1, department_count: 1, unit_count: 1, weekly_average_hours: 37.5, departments: [{ ...department, employee_count: 13 }], regimes: [{ name: '5x2', employee_count: 12 }], notices: [] }
function page<T>(items: T[], total = items.length) { return { items, total, page: 1, page_size: 15 } }
function mount(path = '/') {
  const cache = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return render(<QueryClientProvider client={cache}><MemoryRouter initialEntries={[path]}><App /></MemoryRouter></QueryClientProvider>)
}
beforeEach(() => {
  state.user = { id: 'user-1', organization_id: 'org-1', username: 'admin', permissions: { 'org:read': null, 'org:write': null, 'people:read': null, 'people:write': null, 'catalog:read': null, 'catalog:write': null, 'users:write': null, 'audit:read': null } }
  state.message = ''; state.login.mockReset(); state.logout.mockReset()
  vi.spyOn(api, 'get').mockImplementation(async path => {
    if (path === '/organizations') return { items: [organization], total: 1 }
    if (path.startsWith('/analytics/overview')) return overview
    if (path.startsWith('/units')) return page([unit])
    if (path.startsWith('/departments')) return page([department])
    if (path.startsWith('/catalogs')) return page([{ id: 'r1', name: 'Analista', revision: 1 }])
    if (path.startsWith('/employees')) return page([person], 16)
    if (path.startsWith('/users')) return page([])
    throw new Error('Rota inesperada: ' + path)
  })
})

it('redireciona acesso anônimo para login e valida campos', async () => {
  state.user = null
  mount('/colaboradores')
  await userEvent.click(screen.getByRole('button', { name: 'Entrar na plataforma' }))
  expect(await screen.findByText('Informe seu usuário.')).toBeInTheDocument()
  expect(state.login).not.toHaveBeenCalled()
  expect(api.get).not.toHaveBeenCalled()
})
it('apresenta erro de credencial sem confirmar entrada', async () => {
  state.user = null
  state.login.mockRejectedValue(new ApiError(401, 'INVALID_CREDENTIALS', 'Credenciais inválidas.'))
  mount('/login')
  await userEvent.type(screen.getByLabelText('Usuário'), 'admin')
  await userEvent.type(screen.getByLabelText('Senha'), 'wrong-password')
  await userEvent.click(screen.getByRole('button', { name: 'Mostrar senha' }))
  expect(screen.getByLabelText('Senha')).toHaveAttribute('type', 'text')
  expect(screen.getByRole('button', { name: 'Ocultar senha' })).toHaveAttribute('aria-pressed', 'true')
  expect(state.login).not.toHaveBeenCalled()
  await userEvent.click(screen.getByRole('button', { name: 'Entrar na plataforma' }))
  expect(await screen.findByText('Credenciais inválidas.')).toBeInTheDocument()
  expect(screen.getByLabelText('Senha')).toHaveValue('')
  expect(screen.getByLabelText('Senha')).toHaveAttribute('type', 'password')
})
it('dashboard usa valores retornados pelo banco e orienta a consulta dos módulos', async () => {
  mount()
  expect(await screen.findByText('37,5h')).toBeInTheDocument()
  expect(screen.getByText('1 inativos · 13 cadastrados')).toBeInTheDocument()
  expect(screen.getByText('Consulte regras')).toBeInTheDocument()
  expect(screen.getAllByText('Serviços Horizonte')).toHaveLength(2)
  expect(vi.mocked(api.get).mock.calls.some(([path]) => path.includes('/demo/summary'))).toBe(false)
})
it('filtros e paginação consultam a API com os parâmetros escolhidos', async () => {
  mount('/colaboradores')
  expect(await screen.findByText('Pessoa Teste')).toBeInTheDocument()
  await userEvent.type(screen.getByLabelText('Buscar colaboradores'), 'HH001')
  await waitFor(() => expect(vi.mocked(api.get).mock.calls.some(([path]) => path.includes('search=HH001'))).toBe(true))
  await userEvent.selectOptions(screen.getByLabelText('Filtrar situação'), 'inactive')
  await waitFor(() => expect(vi.mocked(api.get).mock.calls.some(([path]) => path.includes('status=inactive'))).toBe(true))
  await userEvent.click(screen.getByRole('button', { name: 'Próxima página' }))
  await waitFor(() => expect(vi.mocked(api.get).mock.calls.some(([path]) => path.includes('page_number=2'))).toBe(true))
})
it('impede rota de administração para perfil sem permissão', async () => {
  state.user!.permissions = { 'org:read': null, 'people:read': ['u1'], 'catalog:read': null }
  mount('/acessos')
  expect(await screen.findByText('Acesso restrito')).toBeInTheDocument()
  expect(screen.queryByRole('link', { name: 'Acessos' })).not.toBeInTheDocument()
  expect(vi.mocked(api.get).mock.calls.some(([path]) => path.startsWith('/users'))).toBe(false)
})
it('esconde edição de colaborador fora da unidade autorizada', async () => {
  state.user!.permissions = { 'org:read': null, 'people:read': null, 'people:write': ['another-unit'], 'catalog:read': null }
  mount('/colaboradores')
  expect(await screen.findByText('Pessoa Teste')).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Editar Pessoa Teste' })).not.toBeInTheDocument()
})
it('expõe erro de rede e mantém tentativa manual disponível', async () => {
  vi.mocked(api.get).mockImplementation(async path => { if (path === '/organizations') return { items: [organization] }; throw new ApiError(0, 'NETWORK_ERROR', 'Sem conexão com a API') })
  mount()
  expect(await screen.findByText('Sem conexão com a API')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Tentar novamente' })).toBeInTheDocument()
})
it('persiste apenas a preferência de tema e permite navegar pelo menu', async () => {
  const storage = vi.spyOn(Storage.prototype, 'setItem')
  mount()
  await screen.findByText('37,5h')
  await userEvent.click(screen.getByRole('button', { name: 'Ativar tema claro' }))
  expect(storage).toHaveBeenCalledWith('chronos-theme', 'light')
  await userEvent.click(screen.getByRole('link', { name: 'Colaboradores' }))
  expect(await screen.findByText('Pessoa Teste')).toBeInTheDocument()
})


it('protege a rota de analytics e mostra o menu apenas com leitura de cenários', async () => {
  state.user!.permissions['scenario:read'] = null
  mount('/analytics')
  expect(await screen.findByRole('heading', { name: 'Resultados com origem e contexto.' })).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Analytics e exportações' })).toHaveAttribute('href', '/analytics')
})

it('nega analytics para perfil sem leitura de cenários', async () => {
  mount('/analytics')
  expect(await screen.findByRole('heading', { name: 'Acesso restrito' })).toBeInTheDocument()
  expect(screen.queryByRole('link', { name: 'Analytics e exportações' })).not.toBeInTheDocument()
})
