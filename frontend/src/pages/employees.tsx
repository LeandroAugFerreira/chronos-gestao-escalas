import { useCallback, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, ArrowUpRight, Pencil, Plus, Search } from 'lucide-react'
import { api, queryString } from '../services/client'
import { useDebounced, useReferenceData } from '../hooks/data'
import { useAuth } from '../hooks/auth'
import { permits, type Employee, type Page } from '../types/domain'
import { EmployeeForm } from '../components/forms'
import { EmployeeRecords } from '../components/employee-records'
import { PeopleExport } from '../components/people-export'
import { AvailabilityPanel } from '../components/availability'
import { Empty, Failure, Loading, Modal, Notice, PageHeading, Pagination } from '../components/ui'

export function EmployeesPage() {
  const { user } = useAuth()
  const cache = useQueryClient()
  const references = useReferenceData()
  const [search, setSearch] = useState('')
  const debounced = useDebounced(search)
  const [unit, setUnit] = useState('')
  const [department, setDepartment] = useState('')
  const [status, setStatus] = useState('')
  const [sort, setSort] = useState('name')
  const [page, setPage] = useState(1)
  const [editing, setEditing] = useState<Employee | 'new' | null>(null)
  const [pending, setPending] = useState(false)
  const [notice, setNotice] = useState('')
  const close = useCallback(() => setEditing(null), [])
  const query = useQuery({ queryKey: ['employees', debounced, unit, department, status, sort, page], queryFn: ({ signal }) => api.get<Page<Employee>>('/employees' + queryString({ search: debounced, unit_id: unit, department_id: department, status, sort, page_number: page, page_size: 15 }), signal) })
  const ref = references.data
  function saved() { close(); setNotice('Colaborador salvo. Os dados foram atualizados.'); void cache.invalidateQueries() }
  return <><PageHeading eyebrow="GESTÃO DE PESSOAS" title="Colaboradores" description="Organize pessoas, funções e lotações com rastreabilidade." action={permits(user, 'people:write') && <button className="button primary" onClick={() => setEditing('new')}><Plus size={17} />Novo colaborador</button>} />{notice && <Notice>{notice}</Notice>}
    <div className="toolbar"><label className="search-input"><Search size={17} /><input aria-label="Buscar colaboradores" placeholder="Buscar nome ou matrícula" value={search} onChange={e => { setSearch(e.target.value); setPage(1) }} /></label><select aria-label="Filtrar unidade" value={unit} onChange={e => { setUnit(e.target.value); setDepartment(''); setPage(1) }}><option value="">Todas as unidades</option>{ref?.units.map(u => <option key={u.id} value={u.id}>{u.name}</option>)}</select><select aria-label="Filtrar setor" value={department} onChange={e => { setDepartment(e.target.value); setPage(1) }}><option value="">Todos os setores</option>{ref?.departments.filter(d => !unit || d.unit_id === unit).map(d => <option key={d.id} value={d.id}>{d.name}</option>)}</select><select aria-label="Filtrar situação" value={status} onChange={e => { setStatus(e.target.value); setPage(1) }}><option value="">Todas as situações</option><option value="active">Ativos</option><option value="inactive">Inativos</option></select><select aria-label="Ordenar colaboradores" value={sort} onChange={e => { setSort(e.target.value); setPage(1) }}><option value="name">Nome</option><option value="registration">Matrícula</option><option value="status">Situação</option></select></div>
    {references.isError && <Failure error={references.error} retry={() => void references.refetch()} />}
    <PeopleExport selection={{ search, unit_id: unit, department_id: department, status, sort }} />
    {query.isPending ? <Loading /> : query.isError ? <Failure error={query.error} retry={() => void query.refetch()} /> : <section className="panel table-panel"><div className="table-scroll"><table><caption className="sr-only">Colaboradores cadastrados e suas lotações</caption><thead><tr><th>Colaborador</th><th>Setor</th><th>Função</th><th>Situação</th><th><span className="sr-only">Ações</span></th></tr></thead><tbody>{query.data.items.map(person => <tr key={person.id}><td><Link className="person-link" to={'/colaboradores/' + person.id}><span className="avatar">{person.name.slice(-3)}</span><span><b>{person.name}</b><small>{person.registration} · {ref?.units.find(u => u.id === person.unit_id)?.name || 'Unidade cadastrada'}</small></span></Link></td><td>{ref?.departments.find(d => d.id === person.department_id)?.name || '—'}</td><td>{ref?.roles.find(r => r.id === person.job_role_id)?.name || '—'}</td><td><span className={'status-badge ' + person.status}>{person.status === 'active' ? 'Ativo' : 'Inativo'}</span></td><td><div className="row-actions">{permits(user, 'people:write', person.unit_id) && <button className="icon-button" onClick={() => setEditing(person)} aria-label={'Editar ' + person.name}><Pencil size={16} /></button>}<Link className="icon-button" to={'/colaboradores/' + person.id} aria-label={'Ver ' + person.name}><ArrowUpRight size={17} /></Link></div></td></tr>)}</tbody></table></div>{query.data.items.length === 0 && <Empty>Nenhum colaborador encontrado. Ajuste os filtros ou cadastre uma pessoa fictícia.</Empty>}<Pagination page={page} total={query.data.total} size={15} setPage={setPage} /></section>}
    {editing && ref && <Modal title={editing === 'new' ? 'Novo colaborador' : 'Editar colaborador'} onClose={close} pending={pending}><EmployeeForm employee={editing === 'new' ? undefined : editing} {...ref} onSaved={saved} onPending={setPending} /></Modal>}
    {editing && !ref && <Notice error>Carregue unidades, setores e funções antes de abrir o formulário.</Notice>}
  </>
}

export function EmployeeDetailPage() {
  const { id } = useParams()
  const refs = useReferenceData()
  const person = useQuery({ queryKey: ['employee', id], queryFn: ({ signal }) => api.get<Employee>('/employees/' + id, signal) })
  if (person.isPending) return <Loading />
  if (person.isError) return <Failure error={person.error} retry={() => void person.refetch()} />
  const data = person.data
  const unit = refs.data?.units.find(u => u.id === data.unit_id)
  return <><Link className="back-link" to="/colaboradores"><ArrowLeft size={16} />Voltar aos colaboradores</Link>
    <PageHeading eyebrow={data.registration} title={data.name} description="Cadastro sintético · lotação e registros profissionais" />
    <section className="panel detail-overview"><div><span>Unidade</span><b>{unit?.name || '—'}</b></div><div><span>Setor</span><b>{refs.data?.departments.find(d => d.id === data.department_id)?.name || '—'}</b></div><div><span>Função</span><b>{refs.data?.roles.find(r => r.id === data.job_role_id)?.name || '—'}</b></div><div><span>Situação</span><b>{data.status === 'active' ? 'Ativo' : 'Inativo'}</b></div></section>
    {refs.isError && <Failure error={refs.error} retry={() => void refs.refetch()} />}
    <EmployeeRecords employee={data} />
    {unit ? <AvailabilityPanel employee={data} unit={unit} /> : refs.isPending ? <Loading /> : <Notice>Confira a unidade e seu fuso antes de registrar indisponibilidades.</Notice>}
  </>
}
