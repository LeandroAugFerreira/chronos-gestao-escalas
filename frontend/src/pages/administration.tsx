import { useCallback, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus } from 'lucide-react'
import { api, queryString } from '../services/client'
import { useReferenceData } from '../hooks/data'
import type { Account, Audit, Page } from '../types/domain'
import { UserForm } from '../components/forms'
import { Empty, Failure, Loading, Modal, Notice, PageHeading, Pagination, dateTime } from '../components/ui'

export function UsersPage() {
  const refs = useReferenceData()
  const cache = useQueryClient()
  const [page, setPage] = useState(1)
  const [open, setOpen] = useState(false)
  const [pending, setPending] = useState(false)
  const [notice, setNotice] = useState('')
  const close = useCallback(() => setOpen(false), [])
  const query = useQuery({ queryKey: ['users', page], queryFn: ({ signal }) => api.get<Page<Account>>('/users' + queryString({ page_number: page, page_size: 15 }), signal) })
  return <><PageHeading eyebrow="ADMINISTRAÇÃO" title="Acessos à plataforma" description="Crie contas com o perfil e o escopo adequados à responsabilidade de cada pessoa." action={<button className="button primary" onClick={() => setOpen(true)}><Plus size={17} />Novo acesso</button>} />{notice && <Notice>{notice}</Notice>}{refs.isError && <Failure error={refs.error} retry={() => void refs.refetch()} />}{query.isPending ? <Loading /> : query.isError ? <Failure error={query.error} retry={() => void query.refetch()} /> : <section className="panel table-panel"><div className="table-scroll"><table><thead><tr><th>Usuário</th><th>Situação</th></tr></thead><tbody>{query.data.items.map(account => <tr key={account.id}><td><b>{account.username}</b></td><td><span className={'status-badge ' + (account.active ? 'active' : 'inactive')}>{account.active ? 'Ativo' : 'Inativo'}</span></td></tr>)}</tbody></table></div><Pagination page={page} total={query.data.total} size={15} setPage={setPage} /></section>}{open && refs.data && <Modal title="Novo acesso" onClose={close} pending={pending}><UserForm units={refs.data.units} onPending={setPending} onSaved={() => { close(); setNotice('Acesso criado com o perfil e escopo selecionados.'); void cache.invalidateQueries({ queryKey: ['users'] }) }} /></Modal>}</>
}

const actions: Record<string, string> = { create: 'Cadastro criado', update: 'Cadastro atualizado', 'auth.login': 'Entrada na plataforma', 'auth.logout': 'Sessão encerrada', 'auth.refresh': 'Sessão renovada', 'auth.refresh_reuse': 'Sessão revogada por reutilização', 'demo.seed': 'Demonstração importada', 'demo.restore': 'Demonstração restaurada', 'auth.bootstrap': 'Acesso inicial criado' }
const entities: Record<string, string> = { employees: 'Colaboradores', units: 'Unidades', departments: 'Setores', users: 'Acessos', organizations: 'Organização', job_roles: 'Funções', skills: 'Competências', qualifications: 'Qualificações', contracts: 'Contratos' }
export function AuditPage() {
  const [page, setPage] = useState(1)
  const query = useQuery({ queryKey: ['audit', page], queryFn: ({ signal }) => api.get<Page<Audit>>('/audit' + queryString({ page_number: page, page_size: 20 }), signal) })
  return <><PageHeading eyebrow="GOVERNANÇA" title="Trilha de auditoria" description="Consulte o histórico das alterações e dos acessos da sua organização." />{query.isPending ? <Loading /> : query.isError ? <Failure error={query.error} retry={() => void query.refetch()} /> : <section className="panel table-panel"><div className="table-scroll"><table><thead><tr><th>Data e hora</th><th>Evento</th><th>Área</th><th>Referência da operação</th></tr></thead><tbody>{query.data.items.map(event => <tr key={event.id}><td className="nowrap">{dateTime(event.created_at)}</td><td>{actions[event.action] || event.action}</td><td>{entities[event.entity_type] || event.entity_type}</td><td className="mono">{event.correlation_id}</td></tr>)}</tbody></table></div>{query.data.items.length === 0 && <Empty>Nenhum evento registrado.</Empty>}<Pagination page={page} total={query.data.total} size={20} setPage={setPage} /></section>}</>
}
