import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, it, vi } from 'vitest'
import { EmployeeForm, UnitForm, UserForm } from '../components/forms'
import { Modal } from '../components/ui'
import { api, ApiError } from '../services/client'

vi.mock('../hooks/auth', () => ({ useAuth: () => ({ user: { id: 'admin', organization_id: 'org', username: 'admin', permissions: { 'people:write': null, 'org:write': null, 'users:write': null } } }) }))
const references = { units: [{ id: 'u1', name: 'Unidade 1', operation: '24x7', timezone: 'America/Sao_Paulo', revision: 1 }], departments: [{ id: 'd1', unit_id: 'u1', name: 'Setor 1', group: 'Serviços', operation: '24x7', cost_center: '', revision: 1 }], roles: [{ id: 'r1', name: 'Analista' }] }
beforeEach(() => { vi.spyOn(api, 'send').mockResolvedValue({}) })

it('aceita e normaliza e-mail como identificador de acesso sem mudar o perfil escolhido', async () => {
  const saved = vi.fn()
  render(<UserForm units={references.units} onSaved={saved} />)
  await userEvent.type(screen.getByLabelText('Nome de usuário'), ' Operador+Chronos@Example.Test ')
  await userEvent.type(screen.getByLabelText('Senha inicial'), 'test-only-password-1042')
  await userEvent.selectOptions(screen.getByLabelText('Perfil'), 'admin')
  await userEvent.click(screen.getByRole('button', { name: 'Criar acesso' }))
  await waitFor(() => expect(saved).toHaveBeenCalledOnce())
  expect(api.send).toHaveBeenCalledWith('/users', 'POST', expect.objectContaining({ username: 'operador+chronos@example.test', role: 'admin', unit_id: null }), expect.any(String))
})

it('valida campos obrigatórios antes de criar colaborador', async () => {
  render(<EmployeeForm {...references} onSaved={vi.fn()} />)
  await userEvent.click(screen.getByRole('button', { name: 'Cadastrar colaborador' }))
  expect(await screen.findByText('Informe a matrícula.')).toBeInTheDocument()
  expect(api.send).not.toHaveBeenCalled()
})
it('cria colaborador com referências e chave idempotente', async () => {
  const saved = vi.fn()
  render(<EmployeeForm {...references} onSaved={saved} />)
  await userEvent.type(screen.getByLabelText('Nome fictício'), 'Pessoa de teste')
  await userEvent.type(screen.getByLabelText('Matrícula'), 'HH901')
  await userEvent.selectOptions(screen.getByLabelText('Setor'), 'd1')
  await userEvent.selectOptions(screen.getByLabelText('Função'), 'r1')
  await userEvent.click(screen.getByRole('button', { name: 'Cadastrar colaborador' }))
  await waitFor(() => expect(saved).toHaveBeenCalledOnce())
  expect(api.send).toHaveBeenCalledWith('/employees', 'POST', expect.objectContaining({ name: 'Pessoa de teste', unit_id: 'u1', department_id: 'd1', job_role_id: 'r1', synthetic: true }), expect.any(String))
})
it('edita sem perder matrícula e exibe conflito de revisão', async () => {
  vi.mocked(api.send).mockRejectedValue(new ApiError(409, 'STALE_VERSION', 'Conflict'))
  const employee = { id: 'e1', organization_id: 'org', name: 'Pessoa existente', registration: 'HH001', unit_id: 'u1', department_id: 'd1', job_role_id: 'r1', status: 'active' as const, synthetic: true, revision: 7 }
  render(<EmployeeForm employee={employee} {...references} onSaved={vi.fn()} />)
  expect(screen.getByLabelText('Matrícula')).toHaveAttribute('readonly')
  await userEvent.click(screen.getByRole('button', { name: 'Salvar alterações' }))
  expect(await screen.findByText(/Este registro mudou enquanto você editava/)).toBeInTheDocument()
  expect(api.send).toHaveBeenCalledWith('/employees/e1', 'PATCH', expect.objectContaining({ revision: 7 }), undefined)
})
it('não confirma cadastro quando a rede falha', async () => {
  vi.mocked(api.send).mockRejectedValue(new ApiError(0, 'NETWORK_ERROR', 'Sem conexão'))
  const saved = vi.fn()
  render(<UnitForm onSaved={saved} />)
  await userEvent.type(screen.getByLabelText('Nome da unidade'), 'Nova unidade')
  await userEvent.click(screen.getByRole('button', { name: 'Cadastrar unidade' }))
  expect(await screen.findByText('Sem conexão')).toBeInTheDocument()
  expect(saved).not.toHaveBeenCalled()
})
it('fecha diálogo por Escape e devolve o foco', async () => {
  const close = vi.fn()
  const opener = document.createElement('button')
  document.body.appendChild(opener)
  opener.focus()
  const { unmount } = render(<Modal title="Editar item" onClose={close}><input aria-label="Nome" /></Modal>)
  expect(screen.getByRole('dialog', { name: 'Editar item' })).toBeInTheDocument()
  await userEvent.tab({ shift: true })
  expect(screen.getByLabelText('Nome')).toHaveFocus()
  fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' })
  expect(close).toHaveBeenCalledOnce()
  unmount()
  expect(opener).toHaveFocus()
  opener.remove()
})

it('bloqueia alterações no formulário enquanto o salvamento está em andamento', async () => {
  let finish: (value: unknown) => void = () => {}
  vi.mocked(api.send).mockImplementation(() => new Promise(resolve => { finish = resolve }))
  render(<UnitForm onSaved={vi.fn()} />)
  await userEvent.type(screen.getByLabelText('Nome da unidade'), 'Nova unidade')
  await userEvent.click(screen.getByRole('button', { name: 'Cadastrar unidade' }))
  await waitFor(() => expect(screen.getByLabelText('Nome da unidade')).toBeDisabled())
  finish({})
  await waitFor(() => expect(screen.getByLabelText('Nome da unidade')).not.toBeDisabled())
})
