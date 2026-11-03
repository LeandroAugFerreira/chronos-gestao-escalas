import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, it, vi } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { PeopleExport } from '../components/people-export'
import { EmployeesPage } from '../pages/employees'
import { api, ApiError } from '../services/client'
import { saveFile } from '../services/download'

const state = vi.hoisted(() => ({ user: { permissions: {} as Record<string, string[] | null> } }))
vi.mock('../hooks/auth', () => ({ useAuth: () => state }))
vi.mock('../services/download', () => ({ saveFile: vi.fn() }))
const selection = { search: 'Pessoa', unit_id: 'u1', department_id: 'd1', status: 'active', sort: 'registration' }
const file = { filename: 'chronos-1.0-colaboradores-abc.csv', row_count: 31, content: 'YWJj', content_type: 'text/csv;charset=utf-8', byte_length: 3, sha256: 'abc' }
function mountPage() {
  const cache = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={cache}><MemoryRouter><EmployeesPage /></MemoryRouter></QueryClientProvider>)
}
beforeEach(() => {
  state.user.permissions = { 'people:read': ['u1'], 'org:read': null, 'catalog:read': null }
  vi.mocked(saveFile).mockReset().mockResolvedValue(undefined)
  vi.spyOn(api, 'send').mockResolvedValue(file)
  vi.spyOn(api, 'get').mockImplementation(async path => {
    const items = path.startsWith('/units') ? [{ id: 'u1', name: 'Unidade sintética', timezone: 'America/Manaus' }] :
      path.startsWith('/departments') ? [{ id: 'd1', unit_id: 'u1', name: 'Setor sintético' }] :
      path.startsWith('/catalogs') ? [{ id: 'r1', name: 'Função sintética' }] :
      [{ id: 'e1', name: 'Pessoa fictícia', registration: 'HH001', unit_id: 'u1', department_id: 'd1', job_role_id: 'r1', status: 'active', revision: 1 }]
    return { items, total: path.startsWith('/employees') ? 31 : items.length, page: 1, page_size: 15 }
  })
})

it('exports the selected filters across all pages and saves only the verified file', async () => {
  render(<PeopleExport selection={selection} />)
  await userEvent.click(screen.getByRole('button', { name: 'Exportar CSV' }))
  expect(api.send).toHaveBeenCalledExactlyOnceWith('/employees/export', 'POST', selection)
  expect(saveFile).toHaveBeenCalledExactlyOnceWith(file)
  expect(await screen.findByRole('status')).toHaveTextContent('31 colaboradores no arquivo verificado')
  expect(screen.getByText(/sem salários, contratos, evidências ou ausências/)).toBeInTheDocument()
})

it('hides export without people access or outside its own unit scope', () => {
  state.user.permissions = { 'org:read': null, 'finance:read': null }
  const view = render(<PeopleExport selection={selection} />)
  expect(screen.queryByRole('button')).not.toBeInTheDocument()
  state.user.permissions['people:read'] = ['u2']
  view.rerender(<PeopleExport selection={selection} />)
  expect(screen.queryByRole('button')).not.toBeInTheDocument()
  view.rerender(<PeopleExport selection={{ ...selection, unit_id: '' }} />)
  expect(screen.getByRole('button', { name: 'Exportar CSV' })).toBeInTheDocument()
  expect(api.send).not.toHaveBeenCalled()
})

it('sends null for optional filters and preserves an empty result', async () => {
  vi.mocked(api.send).mockResolvedValue({ ...file, row_count: 0 })
  render(<PeopleExport selection={{ search: '', unit_id: '', department_id: '', status: '', sort: 'name' }} />)
  await userEvent.click(screen.getByRole('button', { name: 'Exportar CSV' }))
  expect(api.send).toHaveBeenCalledWith('/employees/export', 'POST', { search: '', unit_id: null, department_id: null, status: null, sort: 'name' })
  expect(await screen.findByRole('status')).toHaveTextContent('0 colaboradores')
})

it('prevents duplicate preparation and identifies the original request if filters change', async () => {
  let resolve!: (value: typeof file) => void
  vi.mocked(api.send).mockReturnValue(new Promise(done => { resolve = done }))
  const view = render(<PeopleExport selection={selection} />)
  const button = screen.getByRole('button', { name: 'Exportar CSV' })
  fireEvent.click(button); fireEvent.click(button)
  expect(api.send).toHaveBeenCalledOnce()
  expect(screen.getByRole('button', { name: 'Preparando CSV…' })).toBeDisabled()
  view.rerender(<PeopleExport selection={{ ...selection, search: 'Outra seleção' }} />)
  resolve(file)
  expect(await screen.findByRole('status')).toHaveTextContent('filtros no momento da solicitação')
  expect(api.send).toHaveBeenCalledWith('/employees/export', 'POST', selection)
})

it('reports preparation or integrity errors without claiming successful download and allows retry', async () => {
  vi.mocked(api.send).mockRejectedValueOnce(new ApiError(422, 'PEOPLE_EXPORT_LIMIT', 'Refine os filtros.'))
  render(<PeopleExport selection={selection} />)
  await userEvent.click(screen.getByRole('button', { name: 'Exportar CSV' }))
  expect(await screen.findByText('Refine os filtros.')).toBeInTheDocument()
  expect(saveFile).not.toHaveBeenCalled(); expect(screen.queryByRole('status')).not.toBeInTheDocument()
  vi.mocked(saveFile).mockRejectedValueOnce(new Error('Falha de integridade.'))
  await userEvent.click(screen.getByRole('button', { name: 'Exportar CSV' }))
  expect(await screen.findByText('Falha de integridade.')).toBeInTheDocument()
  expect(screen.queryByRole('status')).not.toBeInTheDocument()
  await userEvent.click(screen.getByRole('button', { name: 'Exportar CSV' }))
  expect(await screen.findByRole('status')).toHaveTextContent('31 colaboradores')
})

it('wires directory filters and ordering to export without the displayed page limit', async () => {
  mountPage()
  await screen.findByText('31 registros · página 1 de 3')
  await userEvent.click(screen.getByRole('button', { name: 'Próxima página' }))
  expect(await screen.findByText('31 registros · página 2 de 3')).toBeInTheDocument()
  await userEvent.selectOptions(screen.getByLabelText('Filtrar unidade'), 'u1')
  await userEvent.selectOptions(screen.getByLabelText('Filtrar setor'), 'd1')
  await userEvent.selectOptions(screen.getByLabelText('Filtrar situação'), 'active')
  await userEvent.selectOptions(screen.getByLabelText('Ordenar colaboradores'), 'registration')
  fireEvent.change(screen.getByLabelText('Buscar colaboradores'), { target: { value: 'Pessoa' } })
  await userEvent.click(screen.getByRole('button', { name: 'Exportar CSV' }))
  await waitFor(() => expect(api.send).toHaveBeenCalledExactlyOnceWith('/employees/export', 'POST', selection))
  expect(await screen.findByRole('status')).toHaveTextContent('31 colaboradores')
})
