import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { ArrowUpRight, Building2, Clock3, Layers3, Users } from 'lucide-react'
import { api, queryString } from '../services/client'
import { allPages } from '../hooks/data'
import { useAuth } from '../hooks/auth'
import { permits, type Overview, type Unit } from '../types/domain'
import { Empty, Failure, Loading, PageHeading, dateTime } from '../components/ui'
import { RhythmMotif } from '../components/identity'

export function OverviewPage() {
  const { user } = useAuth()
  const [unit, setUnit] = useState('')
  const units = useQuery({ queryKey: ['units-options'], queryFn: ({ signal }) => allPages<Unit>('/units', signal) })
  const query = useQuery({ queryKey: ['overview', unit], queryFn: ({ signal }) => api.get<Overview>('/analytics/overview' + queryString({ unit_id: unit }), signal) })
  return <><section className="overview-intro"><div><PageHeading eyebrow="01 / VISÃO GERAL" title="O ritmo da sua operação." description="Pessoas, jornadas e possibilidades. Tudo começa com uma visão clara." action={permits(user, 'people:read') && <Link className="button secondary" to="/colaboradores">Ver colaboradores<ArrowUpRight size={16} /></Link>} /></div><RhythmMotif /></section>
    <div className="dashboard-filter"><label>Unidade<select value={unit} onChange={event => setUnit(event.target.value)} aria-label="Filtrar dashboard por unidade"><option value="">Todas as unidades permitidas</option>{units.data?.map(u => <option value={u.id} key={u.id}>{u.name}</option>)}</select></label><span className="source-tag"><span className="status-dot" />Dados do banco de demonstração</span></div>
    {query.isPending ? <Loading /> : query.isError ? <Failure error={query.error} retry={() => void query.refetch()} /> : (() => {
      const data = query.data
      const metrics = [
        { label: 'Colaboradores ativos', value: data.active_count.toLocaleString('pt-BR'), note: `${data.inactive_count} inativos · ${data.employee_count} cadastrados`, icon: Users },
        { label: 'Setores configurados', value: String(data.department_count), note: 'Estrutura no escopo selecionado', icon: Layers3 },
        { label: 'Unidades', value: String(data.unit_count), note: 'Acesso conforme seu perfil', icon: Building2 },
        { label: 'Jornada contratual média', value: data.weekly_average_hours === null ? '—' : data.weekly_average_hours.toLocaleString('pt-BR') + 'h', note: 'Por semana · pendente de revisão', icon: Clock3 },
      ]
      const groups = [...new Set(data.departments.map(d => d.group))].map(group => ({ group, people: data.departments.filter(d => d.group === group).reduce((n, d) => n + d.employee_count, 0) }))
      return <><div className="metrics">{metrics.map(metric => <article className="metric" key={metric.label}><div className="metric-top"><span>{metric.label}</span><metric.icon size={17} /></div><strong>{metric.value}</strong><small>{metric.note}</small></article>)}</div>
        <div className="dashboard-grid"><section className="panel"><div className="panel-title"><div><h2>Pessoas por setor</h2><p className="muted">Composição da equipe cadastrada</p></div><span className="badge">{data.department_count} setores</span></div>{data.departments.length ? <><div className="chart" aria-hidden="true"><ResponsiveContainer width="100%" height="100%"><BarChart data={[...data.departments].sort((a, b) => b.employee_count - a.employee_count).slice(0, 8)} layout="vertical" margin={{ left: 8, right: 22 }}><CartesianGrid horizontal={false} stroke="var(--line)" /><XAxis type="number" allowDecimals={false} tick={{ fill: 'var(--muted)', fontSize: 10 }} axisLine={false} tickLine={false} /><YAxis type="category" dataKey="name" width={132} tick={{ fill: 'var(--muted)', fontSize: 10 }} axisLine={false} tickLine={false} /><Tooltip cursor={{ fill: 'var(--soft)' }} contentStyle={{ background: 'var(--panel)', color: 'var(--text)', border: '1px solid var(--line)', borderRadius: 8 }} /><Bar dataKey="employee_count" name="Pessoas" fill="var(--accent)" radius={[0, 4, 4, 0]} barSize={14} /></BarChart></ResponsiveContainer></div><p className="chart-caption">Até oito maiores setores. Consulte todos na estrutura organizacional.</p><ul className="sr-only">{data.departments.map(d => <li key={d.id}>{d.name}: {d.employee_count} pessoas</li>)}</ul></> : <Empty>Cadastre setores para acompanhar a distribuição.</Empty>}</section>
        <section className="panel"><div className="panel-title"><div><h2>Distribuição por grupo</h2><p className="muted">Necessidades diferentes, uma visão integrada</p></div></div><div className="groups">{groups.length ? groups.map((group, index) => <div className="group-row" key={group.group}><div><span className={'legend-color color-' + index % 4} /><b>{group.group}</b><span>{group.people} pessoas</span></div><div className="track"><span style={{ width: `${data.employee_count ? group.people / data.employee_count * 100 : 0}%` }} /></div></div>) : <Empty>Nenhum grupo cadastrado.</Empty>}</div><div className="compact-note"><Building2 size={18} /><div><b>{data.organization.name}</b><small>{data.organization.operation === '24x7' ? 'Operação contínua, 24 horas por dia' : 'Funcionamento configurável por unidade'}</small></div></div></section></div>
        <div className="dashboard-bottom"><section className="panel"><div className="panel-title"><div><h2>Jornadas contratuais</h2><p className="muted">Vínculos vigentes dos colaboradores ativos</p></div><Clock3 size={19} /></div><div className="regime-list">{data.regimes.length ? data.regimes.map(r => <div key={r.name}><span>{r.name}</span><b>{r.employee_count}<small> vínculos</small></b></div>) : <Empty>Nenhum contrato vigente encontrado.</Empty>}</div><p className="form-note">O cadastro de uma jornada não confirma sua validade jurídica.</p></section><section className="panel planning-panel"><p className="eyebrow">DO PLANEJAMENTO À DECISÃO</p><h2>Clareza para o próximo passo.</h2><p>Calendário, regras, cenários, financeiro e otimização estão disponíveis no menu, conforme seu perfil. A central de automações também está disponível. Analytics e exportações permitem consultar as versões calculadas e preparar dados para Power BI.</p><div className="pending-metrics"><span>Cobertura <b>Consulte analytics</b></span><span>Custos projetados <b>Consulte analytics</b></span><span>Conformidade <b>Consulte regras</b></span></div></section></div>
        <div className="data-caption"><span>Atualizado em {dateTime(data.as_of, data.organization.timezone)}</span><span>Quantitativos fictícios. Sem comprovação de dimensionamento ou cobertura.</span></div>
      </>
    })()}
  </>
}


