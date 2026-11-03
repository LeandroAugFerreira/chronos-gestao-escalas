export function civilToISO(value: string, timezone: string) {
  const [date, clock = '00:00'] = value.split('T')
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || !/^\d{2}:\d{2}$/.test(clock)) throw new Error('Informe data e hora válidas.')
  const [year, month, day] = date.split('-').map(Number)
  const [hour, minute] = clock.split(':').map(Number)
  const wall = Date.UTC(year, month - 1, day, hour, minute)
  const format = new Intl.DateTimeFormat('sv-SE', { timeZone: timezone, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' })
  const local = (instant: number) => { const p = Object.fromEntries(format.formatToParts(instant).map(x => [x.type, x.value])); return `${p.year}-${p.month}-${p.day}T${p.hour}:${p.minute}` }
  const offsets = new Set<number>()
  for (const delta of [-86400000, 0, 86400000]) {
    const instant = wall + delta
    offsets.add(Date.parse(local(instant) + 'Z') - instant)
  }
  const matches = [...offsets].map(offset => wall - offset).filter(instant => local(instant) === `${date}T${clock}`)
  if (matches.length !== 1) throw new Error('Horário inexistente ou ambíguo neste fuso. Escolha outro horário.')
  return new Date(matches[0]).toISOString()
}
export function civilFromISO(value: string, timezone: string) {
  const parts = Object.fromEntries(new Intl.DateTimeFormat('sv-SE', { timeZone: timezone, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).formatToParts(new Date(value)).map(p => [p.type, p.value]))
  return `${parts.year}-${parts.month}-${parts.day}T${parts.hour}:${parts.minute}`
}
export function addDays(date: string, count: number) { const d = new Date(date + 'T12:00:00Z'); d.setUTCDate(d.getUTCDate() + count); return d.toISOString().slice(0, 10) }
export function calendarDays(anchor: string, mode: 'week' | 'month') {
  const first = mode === 'month' ? anchor.slice(0, 7) + '-01' : addDays(anchor, -((new Date(anchor + 'T12:00:00Z').getUTCDay() + 6) % 7))
  const count = mode === 'week' ? 7 : new Date(Date.UTC(Number(anchor.slice(0, 4)), Number(anchor.slice(5, 7)), 0)).getUTCDate()
  return Array.from({ length: count }, (_, i) => addDays(first, i))
}
