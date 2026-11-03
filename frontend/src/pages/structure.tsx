import { useCallback, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Pencil, Plus, Search } from 'lucide-react'
import { api, queryString } from '../services/client'
import { useDebounced, useReferenceData } from '../hooks/data'
import { useAuth } from '../hooks/auth'
import { catalogLabels, globalPermission, permits, type Catalog, type Department, type Overview, type Page, type Unit } from '../types/domain'
import { CatalogForm, DepartmentForm, UnitForm } from '../components/forms'
import { Empty, Failure, Loading, Modal, Notice, PageHeading, Pagination } from '../components/ui'

export function StructurePage({ kind }: { kind: 'units' | 'departments' }) {
  const { user } = useAuth()
  const cache = useQueryClient()
  const refs = useReferenceData()
  const [search, setSearch] = useState('')
  const [unit, setUnit] = useState('')
  const debounced = useDebounced(search)
  const [page, setPage] = useState(1)
  const [editing, setEditing] = useState<Unit | Department | 'new' | null>(null)
  const [pending, setPending] = useState(false)
  const [notice, setNotice] = useState('')
  const close = useCallback(() => setEditing(null), [])
  const query = useQuery({ queryKey: [kind, debounced, unit, page], queryFn: ({ signal }) => api.get<Page<Unit | Department>>('/' + kind + queryString({ search: debounced, unit_id: kind === 'departments' ? unit : undefined, page_number: page, page_size: 12 }), signal) })
  const overview = useQuery({ queryKey: ['overview', ''], queryFn: ({ signal }) => api.get<Overview>('/analytics/overview', signal) })
  const isUnit = kind === 'units'
  const canCreate = isUnit ? globalPermission(user, 'org:write') : permits(user, 'org:write')
  const title = isUnit ? 'Unidades' : 'Setores'
  function saved() { close(); setNotice('Cadastro salvo. Estrutura atualizada.'); void cache.invalidateQueries() }
  return <><PageHeading eyebrow="ESTRUTURA ORGANIZACIONAL" title={title} description={isUnit ? 'Gerencie os locais e parâmetros de funcionamento da organização.' : 'Organize grupos, centros de custo e necessidades de cada área.'} action={canCreate && <button className="button primary" onClick={() => setEditing('new')}><Plus size={17} />{isUnit ? 'Nova unidade' : 'Novo setor'}</button>} />{notice && <Notice>{notice}</Notice>}<div className="toolbar"><label className="search-input"><Search size={17} /><input aria-label={'Buscar ' + title.toLowerCase()} placeholder={'Buscar ' + title.toLowerCase()} value={search} onChange={e => { setSearch(e.target.value); setPage(1) }} /></label>{!isUnit && <select aria-label="Filtrar unidade" value={unit} onChange={e => { setUnit(e.target.value); setPage(1) }}><option value="">Todas as unidades</option>{refs.data?.units.map(u => <option value={u.id} key={u.id}>{u.name}</option>)}</select>}</div>
    {refs.isError && <Failure error={refs.error} retry={() => void refs.refetch()} />}
    {query.isPending ? <Loading /> : query.isError ? <Failure error={query.error} retry={() => void query.refetch()} /> : <><div className="structure-grid">{query.data.items.map(row => {
      const department = 'unit_id' in row ? row : null
      const count = department ? overview.data?.departments.find(d => d.id === row.id)?.employee_count : overview.data?.departments.filter(d => d.unit_id === row.id).reduce((n, d) => n + d.employee_count, 0)
      const editable = permits(user, 'org:write', department ? department.unit_id : row.id)
      return <article className="panel structure-card" key={row.id}><div className="panel-title"><span className="category">{department ? department.group : 'UNIDADE'}</span>{editable && <button className="icon-button" onClick={() => setEditing(row)} aria-label={'Editar ' + row.name}><Pencil size={16} /></button>}</div><h2>{row.name}</h2><p className="muted">{department ? refs.data?.units.find(u => u.id === department.unit_id)?.name || 'Unidade cadastrada' : (row as Unit).timezone}</p><div className="structure-meta"><span>{row.operation === '24x7' ? 'Operação contínua' : row.operation === 'business' ? 'Horário administrativo' : row.operation === 'extended' ? 'Horário estendido' : row.operation === 'custom' ? 'Personalizado' : row.operation}</span><b>{count === undefined ? '—' : count}<small> pessoas</small></b></div>{department && <p className="cost-center">Centro de custo: {department.cost_center || 'Não informado'}</p>}</article>
    })}</div>{query.data.items.length === 0 && <Empty>Nenhum registro encontrado.</Empty>}<Pagination page={page} total={query.data.total} size={12} setPage={setPage} /></>}
    {editing && (isUnit || refs.data) && <Modal title={editing === 'new' ? (isUnit ? 'Nova unidade' : 'Novo setor') : 'Editar ' + (isUnit ? 'unidade' : 'setor')} onClose={close} pending={pending}>{isUnit ? <UnitForm unit={editing === 'new' ? undefined : editing as Unit} onSaved={saved} onPending={setPending} /> : <DepartmentForm department={editing === 'new' ? undefined : editing as Department} units={refs.data!.units} onSaved={saved} onPending={setPending} />}</Modal>}
  </>
}

export function CatalogsPage() {
  const { user } = useAuth()
  const cache = useQueryClient()
  const [kind, setKind] = useState('job-roles')
  const [page, setPage] = useState(1)
  const [editing, setEditing] = useState<Catalog | 'new' | null>(null)
  const [pending, setPending] = useState(false)
  const [notice, setNotice] = useState('')
  const close = useCallback(() => setEditing(null), [])
  const query = useQuery({ queryKey: ['catalog', kind, page], queryFn: ({ signal }) => api.get<Page<Catalog>>('/catalogs/' + kind + queryString({ page_number: page, page_size: 15 }), signal) })
  const editable = kind !== 'work-patterns' && globalPermission(user, 'catalog:write')
  function saved() { close(); setNotice('Catálogo atualizado.'); void cache.invalidateQueries() }
  return <><PageHeading eyebrow="CONFIGURAÇÕES DA OPERAÇÃO" title="Catálogos" description="Funções, competências e qualificações configuráveis para diferentes segmentos." action={editable && <button className="button primary" onClick={() => setEditing('new')}><Plus size={17} />Novo item</button>} />{notice && <Notice>{notice}</Notice>}<div className="tabs" aria-label="Selecionar catálogo">{Object.entries(catalogLabels).map(([key, label]) => <button aria-pressed={kind === key} className={kind === key ? 'selected' : ''} key={key} onClick={() => { setKind(key); setPage(1); setNotice('') }}>{label}</button>)}</div>{kind === 'work-patterns' && <Notice>Jornadas de referência, pendentes de revisão. Configure as condições e consulte as avaliações em Jornadas e regras e Calendário.</Notice>}
    {query.isPending ? <Loading /> : query.isError ? <Failure error={query.error} retry={() => void query.refetch()} /> : <section className="panel table-panel"><div className="table-scroll"><table><caption className="sr-only">{catalogLabels[kind]}</caption><thead><tr><th>Nome</th><th>{kind === 'work-patterns' ? 'Descrição' : 'Revisão'}</th><th><span className="sr-only">Ações</span></th></tr></thead><tbody>{query.data.items.map(item => <tr key={item.id}><td><b>{item.name}</b></td><td>{kind === 'work-patterns' ? item.description : item.revision}</td><td>{editable ? <button className="icon-button" onClick={() => setEditing(item)} aria-label={'Editar ' + item.name}><Pencil size={16} /></button> : kind === 'work-patterns' ? <span className="badge">Revisão pendente</span> : '—'}</td></tr>)}</tbody></table></div>{query.data.items.length === 0 && <Empty>Nenhum item cadastrado neste catálogo.</Empty>}<Pagination page={page} total={query.data.total} size={15} setPage={setPage} /></section>}
    {editing && <Modal title={editing === 'new' ? 'Novo item · ' + catalogLabels[kind] : 'Editar item'} onClose={close} pending={pending}><CatalogForm kind={kind} item={editing === 'new' ? undefined : editing} onSaved={saved} onPending={setPending} /></Modal>}
  </>
}
