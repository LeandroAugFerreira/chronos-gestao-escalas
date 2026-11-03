import type { User } from '../types/domain'

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string, public correlationId?: string) { super(message) }
}
type Session = { access_token: string; csrf_token: string; user: User; expires_in: number }
let token: string | null = null
let csrf: string | null = null
let identity: string | null = null
let generation = 0
let renewing: Promise<User> | null = null
let channel: BroadcastChannel | null = null
const listeners = new Set<(user: User | null, message?: string) => void>()

export function subscribeSession(listener: (user: User | null, message?: string) => void) {
  listeners.add(listener)
  return () => { listeners.delete(listener) }
}
function emit(user: User | null, message?: string) { for (const listener of listeners) listener(user, message) }
export function clearSession(message?: string) { token = null; csrf = null; identity = null; generation++; emit(null, message) }
export function watchOtherTabs() {
  if (typeof BroadcastChannel === 'undefined') return () => {}
  channel = new BroadcastChannel('chronos-session')
  channel.onmessage = () => clearSession('A sessão mudou em outra aba. Entre novamente.')
  return () => { channel?.close(); channel = null }
}

async function transport<T>(path: string, options: RequestInit = {}): Promise<T> {
  const timeout = AbortSignal.timeout(15000)
  const signal = options.signal ? AbortSignal.any([timeout, options.signal]) : timeout
  let response: Response
  try { response = await fetch('/api/v1' + path, { ...options, signal, credentials: 'same-origin', headers: { Accept: 'application/json', ...options.headers } }) }
  catch (error) {
    if (options.signal?.aborted) throw error
    throw new ApiError(0, 'NETWORK_ERROR', 'Não foi possível conectar ao Chronos. Verifique sua conexão e tente novamente.')
  }
  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new ApiError(response.status, data.code || 'HTTP_ERROR', data.message || 'Não foi possível concluir a operação.', data.correlation_id)
  }
  return response.status === 204 ? undefined as T : response.json() as Promise<T>
}
async function csrfToken() {
  if (!csrf) csrf = (await transport<{ csrf_token: string }>('/session/csrf')).csrf_token
  return csrf
}
async function browserPost<T>(path: string, body?: unknown, retry = true): Promise<T> {
  const value = await csrfToken()
  try { return await transport<T>(path, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': value }, body: body === undefined ? undefined : JSON.stringify(body) }) }
  catch (error) {
    if (retry && error instanceof ApiError && error.code === 'CSRF_REJECTED') { csrf = null; return browserPost(path, body, false) }
    throw error
  }
}
function adopt(data: Session, expected?: string | null) {
  const nextIdentity = data.user.organization_id + ':' + data.user.id
  if (expected && expected !== nextIdentity) {
    clearSession('A sessão mudou em outra aba. Entre novamente.')
    throw new ApiError(401, 'SESSION_CHANGED', 'A sessão foi alterada. Entre novamente.')
  }
  token = data.access_token; csrf = data.csrf_token; identity = nextIdentity
  emit(data.user)
  return data.user
}
export async function signIn(organization: string, username: string, password: string) {
  const data = await browserPost<Session>('/session/login', { organization, username, password })
  generation++
  const user = adopt(data)
  channel?.postMessage('changed')
  return user
}
export function restoreSession(): Promise<User> {
  if (renewing) return renewing
  const expected = identity
  const started = generation
  const operation = async () => {
    const data = await browserPost<Session>('/session/refresh')
    if (generation !== started) throw new ApiError(401, 'SESSION_CHANGED', 'A sessão foi alterada.')
    return adopt(data, expected)
  }
  const result: Promise<User> = (async () => typeof navigator !== 'undefined' && navigator.locks ? await navigator.locks.request('chronos-refresh', operation) : await operation())()
    .catch(error => {
      if (error instanceof ApiError && error.status === 401 && generation === started) clearSession()
      throw error
    }).finally(() => { renewing = null })
  renewing = result
  return result
}
export async function signOut() {
  // Só confirmar saída após revogação no servidor. Em falha, a sessão permanece visível.
  await browserPost('/session/logout')
  clearSession()
  channel?.postMessage('changed')
}
async function authorized<T>(path: string, options: RequestInit = {}, retry = true): Promise<T> {
  const started = generation
  const current = token
  try { return await transport<T>(path, { ...options, headers: { ...options.headers, ...(current ? { Authorization: 'Bearer ' + current } : {}) } }) }
  catch (error) {
    if (retry && error instanceof ApiError && error.status === 401 && started === generation) {
      await restoreSession()
      if (started !== generation) throw new ApiError(401, 'SESSION_CHANGED', 'A sessão foi alterada.')
      return authorized(path, options, false)
    }
    if (error instanceof ApiError && error.status === 401 && started === generation) clearSession('Sua sessão expirou. Entre novamente.')
    throw error
  }
}
export const api = {
  get: <T,>(path: string, signal?: AbortSignal) => authorized<T>(path, { signal }),
  send: <T,>(path: string, method: 'POST' | 'PATCH', body: unknown, key?: string) => authorized<T>(path, {
    method, headers: { 'Content-Type': 'application/json', ...(key ? { 'Idempotency-Key': key } : {}) }, body: JSON.stringify(body),
  }),
}
export function queryString(values: Record<string, string | number | boolean | undefined>) {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(values)) if (value !== undefined && value !== '') search.set(key, String(value))
  return '?' + search.toString()
}
