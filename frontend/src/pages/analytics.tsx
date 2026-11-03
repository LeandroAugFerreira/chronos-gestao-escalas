import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Download } from 'lucide-react'
import { api, queryString } from '../services/client'
import { saveFile as saveReport, type DownloadFile as Export } from '../services/download'
export { saveFile as saveReport } from '../services/download'
import { allPages } from '../hooks/data'
import { useAuth } from '../hooks/auth'
import { permits, type Unit } from '../types/domain'
import { Empty, Failure, Loading, PageHeading } from '../components/ui'

type Cell = string | number | boolean | null
type History = { id: string; name: string; key: string; version: number; reference_month: string }
type Choice = { id: string; name: string; state?: string }
export type AnalyticsReport = {
  manifest: { extracted_at: string; data_sha256: string; timezone: string; period_start_utc: string; period_end_utc_exclusive: string; columns: Record<string, string[]>; grains: Record<string, string>; methodology: string[] }
  tables: Record<string, Record<string, Cell>[]>
  explanation: { paragraphs: string[]; limits: string }
}
export function ReportView({ report }: { report: AnalyticsReport }) {
  const [selected, setSelected] = useState('scenario')
  const table = selected in report.tables ? selected : 'scenario'
  const scenario = report.tables.scenario[0]
  const coverage = report.tables.coverage?.[0]
  const financial = report.tables.finance
  const metrics = [
    { label: 'Capacidade simulada', value: `${Number(scenario.effective_budget_minutes).toLocaleString('pt-BR')} min`, note: 'Orçamento agregado no mês do cenário' },
    { label: 'Cobertura calculada', value: coverage?.required_staff_minutes ? `${(Number(coverage.covered_staff_minutes) / Number(coverage.required_staff_minutes) * 100).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%` : '—', note: coverage ? `${coverage.covered_staff_minutes ?? '—'} / ${coverage.required_staff_minutes ?? '—'} postos-minuto` : 'Selecione uma otimização' },
    { label: 'Custo projetado', value: financial ? (financial.reduce((total, row) => total + Number(row.total_cents), 0) / 100).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }) : '—', note: financial ? 'Projeção selecionada de 12 meses' : 'Selecione uma projeção autorizada' },
    { label: 'Tentativas observadas', value: report.tables.executions ? String(report.tables.executions.length) : '—', note: 'Automações iniciadas no mês civil' },
  ]
  return <><div className="metrics">{metrics.map(m => <article className="metric" key={m.label}><span>{m.label}</span><strong>{m.value}</strong><small>{m.note}</small></article>)}</div>
    <section className="panel"><p className="eyebrow">EXPLICAÇÃO GRATUITA</p><h2>O que esta seleção mostra</h2>{report.explanation.paragraphs.map((p, i) => <p key={i}>{p}</p>)}<p className="form-note">{report.explanation.limits}</p></section>
    <section className="panel"><div className="panel-title"><h2>Dados do relatório</h2><label>Tabela<select aria-label="Tabela do relatório" value={table} onChange={e => setSelected(e.target.value)}>{Object.keys(report.tables).map(name => <option value={name} key={name}>{name}</option>)}</select></label></div><p className="muted">{report.manifest.grains[table]}</p>{report.tables[table].length ? <div className="table-scroll"><table><thead><tr>{report.manifest.columns[table].map(c => <th key={c}>{c}</th>)}</tr></thead><tbody>{report.tables[table].slice(0, 100).map((row, index) => <tr key={index}>{report.manifest.columns[table].map(c => <td key={c}>{row[c] === null ? '—' : String(row[c])}</td>)}</tr>)}</tbody></table></div> : <Empty>Sem registros nesta tabela.</Empty>}<p className="form-note">{report.tables[table].length} registros. A tela mostra até 100; o arquivo contém toda a seleção autorizada.</p></section>
    <section className="panel analytics-provenance"><h2>Período e método</h2><p>Mês civil em {report.manifest.timezone}: {report.manifest.period_start_utc} até {report.manifest.period_end_utc_exclusive} (fim exclusivo). A projeção financeira e o horizonte da otimização têm seus próprios períodos nas tabelas.</p><ul>{report.manifest.methodology.map(p => <li key={p}>{p}</li>)}</ul><p>Extração: {report.manifest.extracted_at}</p><p>SHA-256 dos dados: <code>{report.manifest.data_sha256}</code></p></section>
  </>
}

export function AnalyticsPage() {
  const { user } = useAuth()
  const [unit, setUnit] = useState(''); const [month, setMonth] = useState('')
  const [scenario, setScenario] = useState(''); const [optimization, setOptimization] = useState(''); const [financial, setFinancial] = useState('')
  const [people, setPeople] = useState(false); const [exporting, setExporting] = useState(false); const [error, setError] = useState<Error | null>(null)
  const [download, setDownload] = useState('')
  const reset = () => { setScenario(''); setOptimization(''); setFinancial(''); setPeople(false); setDownload(''); setError(null) }
  const units = useQuery({ queryKey: ['units-options'], queryFn: ({ signal }) => allPages<Unit>('/units', signal) })
  const history = useQuery({ queryKey: ['analytics-history', unit, month], enabled: !!unit, queryFn: ({ signal }) => allPages<History>('/analytics/history' + queryString({ unit_id: unit, reference_month: month ? month + '-01' : undefined }), signal) })
  const options = useQuery({ queryKey: ['analytics-options', scenario], enabled: !!scenario, queryFn: ({ signal }) => api.get<{ optimization: Choice[]; financial: Choice[] }>('/analytics/options/' + scenario, signal) })
  const selection = { scenario_id: scenario, optimization_id: optimization || null, financial_id: financial || null, include_people: people && !!optimization }
  const report = useQuery({ queryKey: ['analytics-report', selection], enabled: !!scenario, queryFn: () => api.send<AnalyticsReport>('/analytics/report', 'POST', selection) })
  async function exportReport(format: 'csv' | 'xlsx') {
    setExporting(true); setError(null); setDownload('')
    try { const file = await api.send<Export>('/analytics/export', 'POST', { ...selection, format }); await saveReport(file); setDownload(`Arquivo verificado e preparado: ${file.filename}. A extração reflete o instante do download.`) }
    catch (e) { setError(e instanceof Error ? e : new Error('Não foi possível exportar.')) }
    finally { setExporting(false) }
  }
  return <><PageHeading eyebrow="ANALYTICS" title="Resultados com origem e contexto." description="Consulte versões e exporte uma seleção para análise." />
    <section className="panel"><div className="form-grid"><label>Unidade<select aria-label="Unidade do relatório" value={unit} onChange={e => { setUnit(e.target.value); reset() }}><option value="">Selecione</option>{units.data?.map(u => <option key={u.id} value={u.id}>{u.name}</option>)}</select></label><label>Mês de referência<input aria-label="Mês de referência" type="month" value={month} onChange={e => { setMonth(e.target.value); reset() }} /></label></div>
      {units.isError && <Failure error={units.error} />}{unit && (history.isPending ? <Loading /> : history.isError ? <Failure error={history.error} /> : <label>Cenário e versão<select aria-label="Cenário e versão" value={scenario} onChange={e => { reset(); setScenario(e.target.value) }}><option value="">Selecione uma versão</option>{history.data?.map(s => <option key={s.id} value={s.id}>{s.name} · {s.key} v{s.version} · {s.reference_month.slice(0, 7)}</option>)}</select></label>)}
      {scenario && (options.isPending ? <Loading /> : options.isError ? <Failure error={options.error} /> : <div className="form-grid"><label>Otimização<select aria-label="Otimização do relatório" value={optimization} onChange={e => { setOptimization(e.target.value); setPeople(false); setDownload('') }}><option value="">Sem otimização</option>{options.data?.optimization.map(o => <option value={o.id} key={o.id}>{o.name} · {o.state} · {o.id.slice(0, 8)}</option>)}</select></label>{permits(user, 'finance:read', unit) && <label>Projeção financeira<select aria-label="Projeção do relatório" value={financial} onChange={e => { setFinancial(e.target.value); setDownload('') }}><option value="">Sem projeção</option>{options.data?.financial.map(f => <option key={f.id} value={f.id}>{f.name} · {f.id.slice(0, 8)}</option>)}</select></label>}</div>)}
      {optimization && permits(user, 'people:read', unit) && <label><input type="checkbox" checked={people} onChange={e => setPeople(e.target.checked)} /> Incluir atribuições individuais (IDs dos profissionais)</label>}
      <p className="form-note">Cada versão é uma alternativa separada. Até 100 execuções recentes por tipo. O pacote CSV inclui consultas Power Query e medidas para Power BI.</p>
      <div className="toolbar"><button className="button secondary" disabled={!scenario || !report.data || report.isFetching || exporting} onClick={() => void exportReport('csv')}><Download size={16} />CSV e Power BI</button><button className="button secondary" disabled={!scenario || !report.data || report.isFetching || exporting} onClick={() => void exportReport('xlsx')}><Download size={16} />{exporting ? 'Preparando…' : 'Exportar XLSX'}</button></div>
      {download && <p role="status">{download}</p>}{error && <Failure error={error} />}
    </section>
    {!scenario ? <Empty>Selecione uma unidade e uma versão de cenário para consultar os resultados.</Empty> : report.isPending ? <Loading /> : report.isError ? <Failure error={report.error} retry={() => void report.refetch()} /> : <ReportView key={scenario} report={report.data} />}
  </>
}
