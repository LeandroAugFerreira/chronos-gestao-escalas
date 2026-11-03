import { useCallback, useRef, useState, type ReactNode } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { api } from '../services/client'
import { allPages } from '../hooks/data'
import { useAuth } from '../hooks/auth'
import { permits, type Catalog, type Employee } from '../types/domain'
import { Empty, Failure, Field, Loading, Modal, Notice, Submit } from './ui'

type Actions = { employeeId: string; onSaved: () => void; onPending: (value: boolean) => void }
type Qualification = { id: string; qualification_id: string; valid_from: string; valid_until: string; verification_status: string; evidence: string }
type Skill = { id: string; skill_id: string }
type Contract = { id: string; work_pattern_id: string; weekly_minutes: number; base_salary_cents: number; currency: string; employment_type: string; valid_from: string; valid_until: string | null; validation_status: string; assumption_source: string }
type Kind = 'contracts' | 'qualifications' | 'skills'

export function recordStatus(value: string) {
  return ({ validated: 'Validado', pending_review: 'Revisão pendente', synthetic_only: 'Somente sintético', draft: 'Rascunho', rejected: 'Rejeitado' } as Record<string, string>)[value] || 'Status: ' + value
}

export function salaryCents(value: string) {
  if (value.length > 20 || !/^\d+(?:[.,]\d{1,2})?$/.test(value.trim())) throw new Error('Informe um valor sem separador de milhar, com até duas casas decimais.')
  const [whole, fraction = ''] = value.trim().split(/[.,]/)
  const total = BigInt(whole) * 100n + BigInt(fraction.padEnd(2, '0'))
  if (total > 2147483647n) throw new Error('Valor acima do limite permitido.')
  return Number(total)
}

function useCreate({ onSaved, onPending }: Actions) {
  const [pending, setPending] = useState(false); const [error, setError] = useState<Error | null>(null)
  const busy = useRef(false); const intent = useRef<{ body: string; key: string } | null>(null)
  async function create(path: string, body: unknown) {
    if (busy.current) return
    const signature = path + JSON.stringify(body)
    if (intent.current?.body !== signature) intent.current = { body: signature, key: crypto.randomUUID() }
    busy.current = true; setPending(true); onPending(true); setError(null)
    try { await api.send(path, 'POST', body, intent.current.key); onSaved() }
    catch (e) { setError(e instanceof Error ? e : new Error('Não foi possível salvar o vínculo.')) }
    finally { busy.current = false; setPending(false); onPending(false) }
  }
  return { create, pending, error }
}

const date = z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'Informe uma data válida.').refine(value => {
  const parsed = new Date(value + 'T00:00:00Z')
  return value >= '0001-01-01' && !isNaN(parsed.valueOf()) && parsed.toISOString().slice(0, 10) === value
}, 'Informe uma data existente.')
const chosen = z.string().min(1, 'Selecione uma opção.')
const salary = z.string().trim().min(1, 'Informe o salário-base.').refine(value => { try { salaryCents(value); return true } catch { return false } }, 'Use valor sem milhar, até duas casas e no limite permitido.')
const contractSchema = z.object({ work_pattern_id: chosen, weekly_minutes: z.number().int().min(1).max(10080), base_salary: salary,
  employment_type: z.string().trim().min(1, 'Informe o tipo de vínculo.').max(40), valid_from: date, valid_until: z.union([date, z.literal('')]),
  assumption_source: z.string().trim().min(1, 'Informe a fonte do contrato.').max(1000) }).refine(value => !value.valid_until || value.valid_until > value.valid_from,
    { path: ['valid_until'], message: 'O fim exclusivo deve ser posterior ao início.' })

export function ContractForm({ patterns, ...actions }: { patterns: Catalog[] } & Actions) {
  const { create, pending, error } = useCreate(actions)
  const { register, handleSubmit, formState: { errors } } = useForm<z.infer<typeof contractSchema>>({ resolver: zodResolver(contractSchema),
    defaultValues: { work_pattern_id: '', base_salary: '', employment_type: '', valid_from: '', valid_until: '', assumption_source: '' } })
  return <form onSubmit={handleSubmit(({ base_salary, valid_until, ...values }) => create('/employees/' + actions.employeeId + '/contracts', { ...values, base_salary_cents: salaryCents(base_salary), valid_until: valid_until || null }))}>
    {error && <Failure error={error} />}<fieldset disabled={pending}><Notice>O contrato é cadastrado com revisão pendente. Não pode sobrepor um vínculo existente; o registro anterior é preservado.</Notice>
      <div className="form-grid"><Field label="Jornada de referência" error={errors.work_pattern_id?.message}><select {...register('work_pattern_id')}><option value="">Selecione</option>{patterns.map(p => <option value={p.id} key={p.id}>{p.name} · {recordStatus(p.legal_status || 'pending_review')}</option>)}</select></Field>
        <Field label="Carga semanal (minutos)" error={errors.weekly_minutes?.message}><input type="number" min="1" max="10080" step="1" {...register('weekly_minutes', { valueAsNumber: true })} /></Field>
        <Field label="Salário-base (R$)" error={errors.base_salary?.message}><input inputMode="decimal" maxLength={20} placeholder="Ex.: 1500,01" {...register('base_salary')} /></Field>
        <Field label="Tipo de vínculo" error={errors.employment_type?.message}><input maxLength={40} {...register('employment_type')} /></Field>
        <Field label="Início da vigência" error={errors.valid_from?.message}><input type="date" {...register('valid_from')} /></Field>
        <Field label="Fim exclusivo (opcional)" error={errors.valid_until?.message}><input type="date" {...register('valid_until')} /></Field></div>
      <Field label="Fonte do contrato" error={errors.assumption_source?.message}><textarea maxLength={1000} {...register('assumption_source')} /></Field>
      <p className="form-note">40 horas correspondem a 2.400 minutos. A carga cadastrada depende das regras e do instrumento aplicável; o cadastro não valida a jornada.</p><Submit pending={pending}>Cadastrar contrato</Submit>
    </fieldset></form>
}

const qualificationSchema = z.object({ qualification_id: chosen, valid_from: date, valid_until: date, evidence: z.string().trim().max(1000) })
  .refine(value => value.valid_until > value.valid_from, { path: ['valid_until'], message: 'O fim exclusivo deve ser posterior ao início.' })
export function QualificationForm({ qualifications, ...actions }: { qualifications: Catalog[] } & Actions) {
  const { create, pending, error } = useCreate(actions)
  const { register, handleSubmit, formState: { errors } } = useForm<z.infer<typeof qualificationSchema>>({ resolver: zodResolver(qualificationSchema), defaultValues: { qualification_id: '', valid_from: '', valid_until: '', evidence: '' } })
  return <form onSubmit={handleSubmit(values => create('/employees/' + actions.employeeId + '/qualifications', values))}>{error && <Failure error={error} />}<fieldset disabled={pending}>
    <Notice>O cadastro não confirma habilitação. A qualificação permanece pendente de revisão e deve ter evidência apropriada.</Notice>
    <Field label="Qualificação" error={errors.qualification_id?.message}><select {...register('qualification_id')}><option value="">Selecione</option>{qualifications.map(q => <option value={q.id} key={q.id}>{q.name}</option>)}</select></Field>
    <div className="form-grid"><Field label="Início da validade" error={errors.valid_from?.message}><input type="date" {...register('valid_from')} /></Field><Field label="Fim exclusivo da validade" error={errors.valid_until?.message}><input type="date" {...register('valid_until')} /></Field></div>
    <Field label="Evidência da qualificação" error={errors.evidence?.message}><textarea maxLength={1000} {...register('evidence')} /></Field><p className="form-note">Use evidências fictícias na demonstração, sem documentos pessoais ou dados de saúde.</p><Submit pending={pending}>Cadastrar qualificação</Submit>
  </fieldset></form>
}

const skillSchema = z.object({ skill_id: chosen })
export function SkillForm({ skills, ...actions }: { skills: Catalog[] } & Actions) {
  const { create, pending, error } = useCreate(actions)
  const { register, handleSubmit, formState: { errors } } = useForm<z.infer<typeof skillSchema>>({ resolver: zodResolver(skillSchema), defaultValues: { skill_id: '' } })
  return <form onSubmit={handleSubmit(values => create('/employees/' + actions.employeeId + '/skills', values))}>{error && <Failure error={error} />}<fieldset disabled={pending}>
    <Field label="Competência" error={errors.skill_id?.message}><select {...register('skill_id')}><option value="">Selecione</option>{skills.map(s => <option value={s.id} key={s.id}>{s.name}</option>)}</select></Field>
    <p className="form-note">Este vínculo registra uma competência e não substitui habilitação profissional ou sua revisão.</p><Submit pending={pending}>Vincular competência</Submit>
  </fieldset></form>
}

function RecordsSection({ title, action, children }: { title: string; action?: ReactNode; children: ReactNode }) {
  return <section className="panel"><div className="panel-title"><h2>{title}</h2>{action}</div>{children}</section>
}
const labels = { contracts: 'contrato', qualifications: 'qualificação', skills: 'competência' }
export function EmployeeRecords({ employee }: { employee: Employee }) {
  const { user } = useAuth(); const cache = useQueryClient()
  const [kind, setKind] = useState<Kind | null>(null); const [pending, setPending] = useState(false); const [notice, setNotice] = useState('')
  const close = useCallback(() => setKind(null), [])
  const write = permits(user, 'people:write', employee.unit_id) && permits(user, 'catalog:read')
  const finance = permits(user, 'finance:read', employee.unit_id)
  const qualifications = useQuery({ queryKey: ['qualifications', employee.id], queryFn: ({ signal }) => api.get<{ items: Qualification[] }>('/employees/' + employee.id + '/qualifications', signal) })
  const skills = useQuery({ queryKey: ['employee-skills', employee.id], queryFn: ({ signal }) => api.get<{ items: Skill[] }>('/employees/' + employee.id + '/skills', signal) })
  const contracts = useQuery({ queryKey: ['contracts', employee.id], enabled: finance, queryFn: ({ signal }) => api.get<{ items: Contract[] }>('/employees/' + employee.id + '/contracts', signal) })
  const catalogs = useQuery({ queryKey: ['employee-record-catalogs'], enabled: permits(user, 'catalog:read'), queryFn: async ({ signal }) => {
    const [patterns, qualifications, skills] = await Promise.all([allPages<Catalog>('/catalogs/work-patterns', signal), allPages<Catalog>('/catalogs/qualifications', signal), allPages<Catalog>('/catalogs/skills', signal)])
    return { patterns, qualifications, skills }
  }, staleTime: 30000 })
  function saved() { close(); setNotice('Vínculo cadastrado. Confira os registros e as pendências de revisão.'); void cache.invalidateQueries({ queryKey: ['qualifications', employee.id] }); void cache.invalidateQueries({ queryKey: ['employee-skills', employee.id] }); void cache.invalidateQueries({ queryKey: ['contracts', employee.id] }); void cache.invalidateQueries({ queryKey: ['overview'] }) }
  const allowed = kind !== null && write && (kind !== 'contracts' || finance)
  const add = (target: Kind) => write && (target !== 'contracts' || finance) ? <button className="button secondary" onClick={() => { setKind(target); setNotice('') }}>Adicionar {labels[target]}</button> : undefined
  const title = (id: string, values?: Catalog[]) => values?.find(v => v.id === id)?.name || 'Referência ' + id
  return <>{notice && <Notice>{notice}</Notice>}{catalogs.isError && <Failure error={catalogs.error} retry={() => void catalogs.refetch()} />}
    <RecordsSection title="Competências" action={add('skills')}>{skills.isPending ? <Loading /> : skills.isError ? <Failure error={skills.error} /> : skills.data.items.length ? skills.data.items.map(s => <div className="detail-row" key={s.id}><b>{title(s.skill_id, catalogs.data?.skills)}</b></div>) : <Empty>Nenhuma competência registrada.</Empty>}</RecordsSection>
    <RecordsSection title="Qualificações" action={add('qualifications')}><p className="muted">Registros fictícios não substituem verificação de habilitação.</p>{qualifications.isPending ? <Loading /> : qualifications.isError ? <Failure error={qualifications.error} /> : qualifications.data.items.length ? qualifications.data.items.map(q => <div className="detail-row" key={q.id}><div><b>{title(q.qualification_id, catalogs.data?.qualifications)}</b><small>{q.valid_from} até {q.valid_until} (fim exclusivo)</small><small>{q.evidence}</small></div><span className="badge">{recordStatus(q.verification_status)}</span></div>) : <Empty>Nenhuma qualificação registrada.</Empty>}</RecordsSection>
    {finance && <RecordsSection title="Contratos" action={add('contracts')}><p className="muted">Valores-base cadastrados. Jornadas e fontes exigem revisão.</p>{contracts.isPending ? <Loading /> : contracts.isError ? <Failure error={contracts.error} /> : contracts.data?.items.length ? contracts.data.items.map(c => <div className="detail-row" key={c.id}><div><b>{title(c.work_pattern_id, catalogs.data?.patterns)} · {c.weekly_minutes / 60} horas/semana</b><small>{c.valid_from} até {c.valid_until || 'sem fim informado'}{c.valid_until && ' (fim exclusivo)'}</small><small>Salário-base: {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: c.currency }).format(c.base_salary_cents / 100)} · {c.employment_type}</small><small>{c.assumption_source}</small></div><span className="badge">{recordStatus(c.validation_status)}</span></div>) : <Empty>Nenhum contrato cadastrado.</Empty>}</RecordsSection>}
    {allowed && <Modal title={'Adicionar ' + labels[kind]} onClose={close} pending={pending}>{catalogs.isPending ? <Loading /> : catalogs.isError ? <Failure error={catalogs.error} retry={() => void catalogs.refetch()} /> : catalogs.data && (kind === 'contracts' ? <ContractForm patterns={catalogs.data.patterns} employeeId={employee.id} onSaved={saved} onPending={setPending} /> : kind === 'qualifications' ? <QualificationForm qualifications={catalogs.data.qualifications} employeeId={employee.id} onSaved={saved} onPending={setPending} /> : <SkillForm skills={catalogs.data.skills.filter(s => !skills.data?.items.some(own => own.skill_id === s.id))} employeeId={employee.id} onSaved={saved} onPending={setPending} />)}</Modal>}
  </>
}
