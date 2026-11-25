import '../styles/labor-transition.css'
import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { FileClock } from 'lucide-react'
import { api } from '../services/client'
import { Failure, Field, Loading, PageHeading } from '../components/ui'

type Source = { id: string; title: string; url: string; articles: string }
type Phase = { id: string; name: string; from: string; until: string | null; weekly_minutes: number; rest_days: number; monthly_divisor_hours: number }
type References = { policy_version: string; reviewed_on: string; phases: Phase[]; sources: Source[]; scope: string }
export type TransitionResult = {
  phase: Phase; effective_weekly_minutes: number; monthly_divisor_hours: string; monthly_salary_cents: number;
  baseline_hourly_cents: number; hourly_cents: number; hourly_change_percent: string; status: string; digest: string;
  findings: { code: string; status: 'within' | 'exceeds' | 'review'; message: string; source_ids: string[] }[];
  sources: Source[]; policy_version: string; reviewed_on: string
}
const reais = (cents: number) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(cents / 100)
const hours = (minutes: number) => `${Math.floor(minutes / 60)}h${minutes % 60 ? String(minutes % 60).padStart(2, '0') : ''}`
const dates = (value: string) => value.split('-').reverse().join('/')

export function LaborTransitionPage() {
  const refs = useQuery({ queryKey: ['labor-transition'], queryFn: ({ signal }) => api.get<References>('/labor-transition', signal) })
  const [referenceDate, setReferenceDate] = useState('2026-12-16')
  const [salary, setSalary] = useState('3300')
  const [weekly, setWeekly] = useState('44')
  const [planned, setPlanned] = useState('40')
  const [daily, setDaily] = useState('480')
  const [rests, setRests] = useState('2')
  const [regime, setRegime] = useState('regular')
  const [collective, setCollective] = useState('not_reviewed')
  const [compensation, setCompensation] = useState(false)
  const [interim, setInterim] = useState(false)
  const [divisor, setDivisor] = useState('')
  const [formError, setFormError] = useState('')
  const calculation = useMutation({ mutationFn: (body: Record<string, unknown>) => api.send<TransitionResult>('/labor-transition/compare', 'POST', body) })
  const result = calculation.data
  function change() { calculation.reset(); setFormError('') }
  function exportResult() {
    if (!result) return
    const url = URL.createObjectURL(new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' }))
    const link = document.createElement('a'); link.href = url; link.download = `chronos-2.0-transicao-${referenceDate}.json`; link.click(); URL.revokeObjectURL(url)
  }
  return <>
    <PageHeading eyebrow="EVOLUÇÃO DO CHRONOS · VERSÃO 2.0" title="Transição de jornadas" description="Compare a referência da versão 1.0 com as etapas da nova legislação. Veja os limites, o valor da hora e os pontos que precisam de revisão." />
    <section className="panel"><h2><FileClock size={22} aria-hidden="true" /> Uma evolução, com histórico</h2><p>A base de planejamento do Chronos 1.0 continua disponível. Esta área acrescenta uma comparação por data, com premissas explícitas e referências verificadas em 25/11/2026.</p><p><a href="https://leandroaugferreira.github.io/chronos-1.0.html" target="_blank" rel="noopener noreferrer">Conhecer a versão 1.0</a></p></section>
    {refs.isPending && <Loading />}{refs.isError && <Failure error={refs.error} retry={() => void refs.refetch()} />}
    {refs.data && <section className="panel"><h2>Etapas da transição</h2><div className="transition-phases">{refs.data.phases.map(phase => <article key={phase.id}><h3>{phase.name}</h3><strong>{hours(phase.weekly_minutes)} por semana</strong><p>{phase.rest_days} repouso(s) de 24 horas</p><small>{phase.id === 'historical_44' ? 'Até 15/12/2026' : `A partir de ${dates(phase.from)}`}</small></article>)}</div><p>Jornadas contratuais mais curtas são preservadas. As referências gerais não substituem a análise dos regimes especiais e das normas coletivas.</p></section>}
    <form className="panel" aria-label="Premissas da transição" onChange={change} onSubmit={event => {
      event.preventDefault()
      const monetary = Number(salary)
      if (!Number.isFinite(monetary) || monetary <= 0) { setFormError('Informe um salário mensal válido.'); return }
      calculation.mutate({ reference_date: referenceDate, monthly_salary_cents: Math.round(monetary * 100), contract_weekly_minutes: Math.round(Number(weekly) * 60), planned_weekly_minutes: Math.round(Number(planned) * 60), planned_daily_minutes: Number(daily), rest_days_24h: Number(rests), regime, collective_status: collective, collective_rest_compensation: compensation, use_interim_daily_exception: interim, more_favorable_divisor_hours: divisor || null })
    }}>
      <h2>Compare suas premissas</h2><div className="transition-fields">
        <Field label="Data de referência"><input type="date" value={referenceDate} min="2000-01-01" max="2098-12-31" required onChange={e => setReferenceDate(e.target.value)} /></Field>
        <Field label="Salário mensal preservado (R$)"><input type="number" value={salary} min="0.01" max="10000000" step="0.01" required onChange={e => setSalary(e.target.value)} /></Field>
        <Field label="Carga contratada anterior (horas/semana)"><input type="number" value={weekly} min="0.1" max="168" step="0.1" required onChange={e => setWeekly(e.target.value)} /></Field>
        <Field label="Carga semanal planejada (horas)"><input type="number" value={planned} min="0" max="168" step="0.1" required onChange={e => setPlanned(e.target.value)} /></Field>
        <Field label="Maior jornada diária líquida (minutos)"><input type="number" value={daily} min="0" max="1440" step="1" required onChange={e => setDaily(e.target.value)} /></Field>
        <Field label="Repousos semanais de 24 horas"><input type="number" value={rests} min="0" max="7" step="1" required onChange={e => setRests(e.target.value)} /></Field>
        <Field label="Regime em análise"><select value={regime} onChange={e => setRegime(e.target.value)}><option value="regular">Jornada comum</option><option value="12x36">12x36</option><option value="rotating">Turnos ininterruptos de revezamento</option><option value="custom">Outro regime especial</option></select></Field>
        <Field label="Situação da negociação coletiva"><select value={collective} onChange={e => setCollective(e.target.value)}><option value="not_reviewed">Ainda não verificada</option><option value="present">Há instrumento coletivo aplicável</option><option value="absent_at_cutoff">Ausência de ACT/CCT até 15/12/2026, a confirmar</option></select></Field>
        <Field label="Divisor mensal mais favorável, se aplicável (horas)"><input type="number" value={divisor} min="0.01" max="1000" step="0.01" placeholder="Usar a referência da etapa" onChange={e => setDivisor(e.target.value)} /></Field>
      </div><p><label className="transition-choice"><input type="checkbox" checked={compensation} onChange={e => setCompensation(e.target.checked)} /> Há compensação dos repousos por instrumento coletivo</label></p><p><label className="transition-choice"><input type="checkbox" checked={interim} onChange={e => setInterim(e.target.checked)} /> Analisar a hipótese transitória de até 8h24 prevista na cautelar do STF</label></p>
      {formError && <p role="alert">{formError}</p>}<button className="button primary" type="submit" disabled={calculation.isPending}>{calculation.isPending ? 'Calculando…' : 'Comparar etapas'}</button>
    </form>
    {calculation.isError && <Failure error={calculation.error} />}
    {result && <section className="panel" aria-label="Comparação da transição" aria-live="polite"><h2>{result.phase.name}</h2><p><strong>{result.status === 'adjustment_required' ? 'Há premissas que precisam de ajuste' : 'Comparação pronta para revisão'}</strong></p><div className="transition-phases"><article><h3>Carga semanal de referência</h3><strong>{hours(result.effective_weekly_minutes)}</strong></article><article><h3>Salário mensal</h3><strong>{reais(result.monthly_salary_cents)}</strong><p>Preservado na comparação</p></article><article><h3>Valor da hora</h3><strong>{reais(result.hourly_cents)}</strong><p>Referência anterior: {reais(result.baseline_hourly_cents)}</p><p>Divisor: {result.monthly_divisor_hours} horas</p></article></div><h3>Pontos de atenção</h3><ul className="transition-findings">{result.findings.map(item => <li key={item.code}><b>{item.status === 'exceeds' ? 'Ajuste necessário' : item.status === 'review' ? 'Revisar' : 'Dentro da referência'}.</b> {item.message}</li>)}</ul><p><small>Perfil {result.policy_version}. O resultado compara premissas e não certifica uma escala.</small></p><button className="button secondary" type="button" onClick={exportResult}>Exportar comparação e fontes</button></section>}
    {refs.data && <section className="panel"><h2>Fontes e condições de aplicação</h2><ul>{refs.data.sources.map(source => <li key={source.id}><a href={source.url} target="_blank" rel="noopener noreferrer">{source.title}</a><p>{source.articles}</p></li>)}</ul><p>{refs.data.scope}</p></section>}
  </>
}
