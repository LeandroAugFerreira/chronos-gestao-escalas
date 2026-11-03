import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { api } from '../services/client'
import { civilToISO } from '../services/calendar'
import { useAuth } from '../hooks/auth'
import { permits, type Employee, type Unit } from '../types/domain'
import { dateTime, Empty, Failure, Field, Loading, Notice, Submit } from './ui'

const schema = z.object({ start_at: z.string().min(1), end_at: z.string().min(1), reason: z.string().trim().max(200) })
export function AvailabilityPanel({ employee, unit }: { employee: Employee; unit: Unit }) {
  const { user } = useAuth(); const cache = useQueryClient()
  const [pending, setPending] = useState(false); const [error, setError] = useState<Error | null>(null)
  const [key, setKey] = useState(() => crypto.randomUUID())
  const { register, handleSubmit, reset } = useForm<z.infer<typeof schema>>({ resolver: zodResolver(schema), defaultValues: { start_at: '', end_at: '', reason: '' } })
  const query = useQuery({ queryKey: ['availability', employee.id], queryFn: ({ signal }) => api.get<{ items: { id: string; start_at: string; end_at: string; type: string }[] }>('/employees/' + employee.id + '/availability', signal) })
  async function submit(values: z.infer<typeof schema>) {
    setPending(true); setError(null)
    try { await api.send('/employees/' + employee.id + '/availability', 'POST', { ...values, start_at: civilToISO(values.start_at, unit.timezone), end_at: civilToISO(values.end_at, unit.timezone), type: 'unavailable' }, key); reset(); setKey(crypto.randomUUID()); void cache.invalidateQueries({ queryKey: ['availability', employee.id] }); void cache.invalidateQueries({ queryKey: ['calendar'] }) }
    catch (e) { setError(e as Error) } finally { setPending(false) }
  }
  return <details className="panel"><summary>Indisponibilidades · {employee.name}</summary><p className="form-note">Fuso {unit.timezone}. Informe somente motivo operacional, sem dados de saúde. Alterações futuras exigem reavaliar plantões já gravados.</p>{query.isPending ? <Loading /> : query.isError ? <Failure error={query.error} /> : query.data.items.length === 0 ? <Empty>Nenhuma indisponibilidade registrada.</Empty> : query.data.items.map(r => <p key={r.id}>{r.type === 'unavailable' ? 'Indisponível' : 'Disponibilidade informada'} · {dateTime(r.start_at, unit.timezone)} → {dateTime(r.end_at, unit.timezone)}</p>)}{error && <Failure error={error} />}{permits(user, 'people:write', employee.unit_id) && <form onSubmit={handleSubmit(submit)}><fieldset disabled={pending}><div className="form-grid"><Field label="Início da indisponibilidade"><input type="datetime-local" required {...register('start_at')} /></Field><Field label="Fim da indisponibilidade"><input type="datetime-local" required {...register('end_at')} /></Field><Field label="Motivo operacional (opcional)"><input maxLength={200} {...register('reason')} /></Field></div><Notice>O registro passa a ser considerado nas próximas avaliações de plantões.</Notice><Submit pending={pending}>Registrar indisponibilidade</Submit></fieldset></form>}</details>
}
