import { useRef, useState, type FormEventHandler, type ReactNode } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { api, ApiError } from '../services/client'
import { useAuth } from '../hooks/auth'
import { globalPermission, permits, type Catalog, type Department, type Employee, type Unit } from '../types/domain'
import { Field, Notice, Submit } from './ui'

const text = (name: string, max = 160) => z.string().trim().min(2, `${name}: informe pelo menos 2 caracteres.`).max(max, `Máximo de ${max} caracteres.`)
const chosen = z.string().min(1, 'Selecione uma opção.')
const employeeSchema = z.object({ name: text('Nome'), registration: z.string().trim().min(1, 'Informe a matrícula.').max(40), unit_id: chosen, department_id: chosen, job_role_id: chosen, status: z.enum(['active', 'inactive']) })
type PersonValues = z.infer<typeof employeeSchema>
type Actions = { onSaved: () => void; onPending?: (pending: boolean) => void }

function SaveForm({ pending, onSubmit, children }: { pending: boolean; onSubmit: FormEventHandler<HTMLFormElement>; children: ReactNode }) {
  return <form onSubmit={onSubmit} aria-busy={pending}><fieldset disabled={pending}>{children}</fieldset></form>
}

function useSave(onSaved: () => void, onPending?: (pending: boolean) => void) {
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const key = useRef(crypto.randomUUID())
  async function save(path: string, method: 'POST' | 'PATCH', data: unknown) {
    setError(''); setPending(true); onPending?.(true)
    try { await api.send(path, method, data, method === 'POST' ? key.current : undefined); onSaved() }
    catch (err) {
      const value = err as ApiError
      setError(value.code === 'STALE_VERSION' ? 'Este registro mudou enquanto você editava. Feche o formulário e recarregue os dados antes de tentar novamente.' : value.message)
      // Uma mudança de conteúdo após erro explícito usa uma nova intenção; erros de rede preservam a chave.
      if (value.status > 0) key.current = crypto.randomUUID()
    } finally { setPending(false); onPending?.(false) }
  }
  return { save, pending, error }
}

export function EmployeeForm({ employee, units, departments, roles, onSaved, onPending }: { employee?: Employee; units: Unit[]; departments: Department[]; roles: Catalog[] } & Actions) {
  const { user } = useAuth()
  const allowedUnits = units.filter(unit => permits(user, 'people:write', unit.id))
  const { register, handleSubmit, watch, setValue, formState: { errors } } = useForm<PersonValues>({ resolver: zodResolver(employeeSchema), defaultValues: employee ? { ...employee } : { name: '', registration: '', unit_id: allowedUnits.length === 1 ? allowedUnits[0].id : '', department_id: '', job_role_id: '', status: 'active' } })
  const { save, pending, error } = useSave(onSaved, onPending)
  const unit = watch('unit_id')
  const unitField = register('unit_id')
  return <SaveForm pending={pending} onSubmit={handleSubmit(values => save(employee ? '/employees/' + employee.id : '/employees', employee ? 'PATCH' : 'POST', employee ? { name: values.name, status: values.status, unit_id: values.unit_id, department_id: values.department_id, job_role_id: values.job_role_id, revision: employee.revision } : { ...values, status: undefined, synthetic: true }))}>
    {error && <Notice error>{error}</Notice>}
    <div className="form-grid"><Field label="Nome fictício" error={errors.name?.message}><input {...register('name')} aria-invalid={!!errors.name} autoComplete="off" /></Field><Field label="Matrícula" error={errors.registration?.message}><input {...register('registration')} readOnly={!!employee} aria-invalid={!!errors.registration} /></Field><Field label="Unidade" error={errors.unit_id?.message}><select {...unitField} onChange={event => { void unitField.onChange(event); setValue('department_id', '') }}>{<option value="">Selecione a unidade</option>}{allowedUnits.map(u => <option key={u.id} value={u.id}>{u.name}</option>)}</select></Field><Field label="Setor" error={errors.department_id?.message}><select {...register('department_id')}><option value="">Selecione o setor</option>{departments.filter(d => d.unit_id === unit).map(d => <option key={d.id} value={d.id}>{d.name}</option>)}</select></Field><Field label="Função" error={errors.job_role_id?.message}><select {...register('job_role_id')}><option value="">Selecione a função</option>{roles.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}</select></Field>{employee && <Field label="Situação"><select {...register('status')}><option value="active">Ativo</option><option value="inactive">Inativo</option></select></Field>}</div>
    <p className="form-note">Use apenas dados fictícios. Alterar a função ou lotação não comprova habilitação para uma atividade.</p><div className="form-actions"><Submit pending={pending}>{employee ? 'Salvar alterações' : 'Cadastrar colaborador'}</Submit></div>
  </SaveForm>
}

const unitSchema = z.object({ name: text('Nome'), operation: z.string().trim().min(1, 'Informe o funcionamento.').max(32), timezone: z.string().min(1, 'Informe o fuso horário.') })
export function UnitForm({ unit, onSaved, onPending }: { unit?: Unit } & Actions) {
  const { register, handleSubmit, formState: { errors } } = useForm<z.infer<typeof unitSchema>>({ resolver: zodResolver(unitSchema), defaultValues: unit || { name: '', operation: 'business', timezone: 'America/Sao_Paulo' } })
  const { save, pending, error } = useSave(onSaved, onPending)
  return <SaveForm pending={pending} onSubmit={handleSubmit(values => save(unit ? '/units/' + unit.id : '/units', unit ? 'PATCH' : 'POST', { ...values, ...(unit ? { revision: unit.revision } : {}) }))}>{error && <Notice error>{error}</Notice>}<div className="form-grid"><Field label="Nome da unidade" error={errors.name?.message}><input {...register('name')} aria-invalid={!!errors.name} /></Field><Field label="Funcionamento" error={errors.operation?.message}><select {...register('operation')}><option value="business">Horário administrativo</option><option value="24x7">Operação contínua · 24 horas</option><option value="extended">Horário estendido</option><option value="custom">Personalizado</option>{unit && !["business", "24x7", "extended", "custom"].includes(unit.operation) && <option value={unit.operation}>{unit.operation}</option>}</select></Field><Field label="Fuso horário" error={errors.timezone?.message}><input {...register('timezone')} placeholder="America/Sao_Paulo" /></Field></div><div className="form-actions"><Submit pending={pending}>{unit ? 'Salvar alterações' : 'Cadastrar unidade'}</Submit></div></SaveForm>
}

const departmentSchema = z.object({ unit_id: chosen, name: text('Nome'), group: text('Grupo', 80), operation: z.string().trim().min(1).max(32), cost_center: z.string().trim().max(80) })
export function DepartmentForm({ department, units, onSaved, onPending }: { department?: Department; units: Unit[] } & Actions) {
  const { user } = useAuth()
  const allowed = units.filter(u => permits(user, 'org:write', u.id))
  const { register, handleSubmit, formState: { errors } } = useForm<z.infer<typeof departmentSchema>>({ resolver: zodResolver(departmentSchema), defaultValues: department || { name: '', group: '', operation: 'business', cost_center: '', unit_id: allowed.length === 1 ? allowed[0].id : '' } })
  const { save, pending, error } = useSave(onSaved, onPending)
  return <SaveForm pending={pending} onSubmit={handleSubmit(values => save(department ? '/departments/' + department.id : '/departments', department ? 'PATCH' : 'POST', { ...values, ...(department ? { revision: department.revision } : {}) }))}>{error && <Notice error>{error}</Notice>}<div className="form-grid"><Field label="Nome do setor" error={errors.name?.message}><input {...register('name')} aria-invalid={!!errors.name} /></Field><Field label="Unidade" error={errors.unit_id?.message}><select {...register('unit_id')}><option value="">Selecione a unidade</option>{allowed.map(u => <option key={u.id} value={u.id}>{u.name}</option>)}</select></Field><Field label="Grupo" error={errors.group?.message}><input {...register('group')} placeholder="Ex.: Administrativo" /></Field><Field label="Funcionamento" error={errors.operation?.message}><select {...register('operation')}><option value="business">Horário administrativo</option><option value="24x7">Operação contínua · 24 horas</option><option value="extended">Horário estendido</option><option value="custom">Personalizado</option>{department && !["business", "24x7", "extended", "custom"].includes(department.operation) && <option value={department.operation}>{department.operation}</option>}</select></Field><Field label="Centro de custo" error={errors.cost_center?.message}><input {...register('cost_center')} /></Field></div><p className="form-note">Um setor com colaboradores precisa ter sua equipe transferida antes de mudar de unidade.</p><div className="form-actions"><Submit pending={pending}>{department ? 'Salvar alterações' : 'Cadastrar setor'}</Submit></div></SaveForm>
}

const catalogSchema = z.object({ name: text('Nome') })
export function CatalogForm({ kind, item, onSaved, onPending }: { kind: string; item?: Catalog } & Actions) {
  const { register, handleSubmit, formState: { errors } } = useForm<z.infer<typeof catalogSchema>>({ resolver: zodResolver(catalogSchema), defaultValues: { name: item?.name || '' } })
  const { save, pending, error } = useSave(onSaved, onPending)
  return <SaveForm pending={pending} onSubmit={handleSubmit(values => save('/catalogs/' + kind + (item ? '/' + item.id : ''), item ? 'PATCH' : 'POST', { ...values, ...(item ? { revision: item.revision } : {}) }))}>{error && <Notice error>{error}</Notice>}<Field label="Nome" error={errors.name?.message}><input {...register('name')} aria-invalid={!!errors.name} /></Field><div className="form-actions"><Submit pending={pending}>{item ? 'Salvar alterações' : 'Cadastrar item'}</Submit></div></SaveForm>
}

const userSchema = z.object({ username: z.string().trim().toLowerCase().regex(/^[a-z0-9][a-z0-9._@+-]{2,79}$/, 'Use 3–80 caracteres: letras, números, ponto, hífen, sublinhado, @ ou +.'), password: z.string().min(12, 'Use pelo menos 12 caracteres.').max(128), role: z.enum(['admin', 'hr', 'manager', 'finance', 'analyst', 'demo']), unit_id: z.string() })
export const roleLabels: Record<string, string> = { admin: 'Administrador', hr: 'Recursos Humanos', manager: 'Gestor', finance: 'Financeiro', analyst: 'Analista', demo: 'Demonstração' }
export function UserForm({ units, onSaved, onPending }: { units: Unit[] } & Actions) {
  const { user } = useAuth()
  const { register, handleSubmit, formState: { errors } } = useForm<z.infer<typeof userSchema>>({ resolver: zodResolver(userSchema), defaultValues: { username: '', password: '', role: 'demo', unit_id: '' } })
  const { save, pending, error } = useSave(onSaved, onPending)
  if (!globalPermission(user, 'users:write')) return null
  return <SaveForm pending={pending} onSubmit={handleSubmit(values => save('/users', 'POST', { ...values, unit_id: values.unit_id || null }))}>{error && <Notice error>{error}</Notice>}<div className="form-grid"><Field label="Nome de usuário" error={errors.username?.message}><input {...register('username')} autoComplete="off" /></Field><Field label="Senha inicial" error={errors.password?.message}><input {...register('password')} type="password" autoComplete="new-password" /></Field><Field label="Perfil" error={errors.role?.message}><select {...register('role')}>{Object.entries(roleLabels).map(([key, label]) => <option value={key} key={key}>{label}</option>)}</select></Field><Field label="Escopo de unidade"><select {...register('unit_id')}><option value="">Toda a organização</option>{units.map(u => <option key={u.id} value={u.id}>{u.name}</option>)}</select></Field></div><p className="form-note">O perfil define as ações permitidas. O escopo limita onde elas podem ser realizadas.</p><div className="form-actions"><Submit pending={pending}>Criar acesso</Submit></div></SaveForm>
}
