import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { api, ApiError, clearSession, restoreSession, signIn, signOut } from '../services/client'

const user = { id: 'user-1', organization_id: 'org-1', username: 'admin', permissions: { 'org:read': null } }
function response(data: unknown, status = 200) { return new Response(status === 204 ? null : JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } }) }
let fetchMock: ReturnType<typeof vi.fn>
beforeEach(() => { clearSession(); fetchMock = vi.fn(); vi.stubGlobal('fetch', fetchMock) })
afterEach(() => clearSession())
function session(token = 'access-only-in-memory', who = user) { return { access_token: token, csrf_token: 'bound-csrf', user: who, expires_in: 900 } }
async function login() {
  fetchMock.mockResolvedValueOnce(response({ csrf_token: 'preauth-csrf' })).mockResolvedValueOnce(response(session()))
  await signIn('horizonte', 'admin', 'test-password')
}

describe('sessão e transporte', () => {
  it('envia CSRF e mantém token fora de armazenamentos persistentes', async () => {
    const persistent = vi.spyOn(Storage.prototype, 'setItem')
    await login()
    const options = fetchMock.mock.calls[1][1] as RequestInit
    expect(options.credentials).toBe('same-origin')
    expect(options.headers).toMatchObject({ 'X-CSRF-Token': 'preauth-csrf' })
    expect(persistent).not.toHaveBeenCalled()
    fetchMock.mockResolvedValueOnce(response({ ok: true }))
    await api.get('/employees')
    expect(fetchMock.mock.calls[2][1].headers.Authorization).toBe('Bearer access-only-in-memory')
  })
  it('renova uma única vez para consultas concorrentes após 401', async () => {
    await login()
    let renewals = 0
    fetchMock.mockImplementation(async (path: string, options: RequestInit) => {
      if (path.endsWith('/session/refresh')) { renewals++; return response(session('new-access')) }
      return (options.headers as Record<string, string>).Authorization === 'Bearer new-access' ? response({ ok: true }) : response({ code: 'INVALID_TOKEN', message: 'Expired' }, 401)
    })
    const results = await Promise.all([api.get('/employees'), api.get('/units')])
    expect(renewals).toBe(1)
    expect(results).toEqual([{ ok: true }, { ok: true }])
  })
  it('não repete uma operação com a identidade de outra conta', async () => {
    await login()
    fetchMock.mockResolvedValueOnce(response({ code: 'INVALID_TOKEN' }, 401))
      .mockResolvedValueOnce(response(session('other-token', { ...user, id: 'user-2' })))
    await expect(api.send('/employees', 'POST', { name: 'Pessoa' })).rejects.toMatchObject({ code: 'SESSION_CHANGED' })
    expect(fetchMock.mock.calls.filter(call => call[0] === '/api/v1/employees')).toHaveLength(1)
  })
  it('mantém acesso em memória quando a revogação de logout falha', async () => {
    await login()
    fetchMock.mockRejectedValueOnce(new TypeError('offline'))
    await expect(signOut()).rejects.toMatchObject({ code: 'NETWORK_ERROR' })
    fetchMock.mockResolvedValueOnce(response({ ok: true }))
    await api.get('/units')
    expect(fetchMock.mock.calls.at(-1)?.[1].headers.Authorization).toBe('Bearer access-only-in-memory')
  })
  it('limpa acesso após confirmação do logout', async () => {
    await login()
    fetchMock.mockResolvedValueOnce(response(null, 204))
    await signOut()
    fetchMock.mockResolvedValueOnce(response({ ok: true }))
    await api.get('/units')
    expect(fetchMock.mock.calls.at(-1)?.[1].headers.Authorization).toBeUndefined()
  })
  it('renova CSRF expirado sem duplicar a operação de negócio', async () => {
    fetchMock.mockResolvedValueOnce(response({ csrf_token: 'old' }))
      .mockResolvedValueOnce(response({ code: 'CSRF_REJECTED', message: 'Expired' }, 403))
      .mockResolvedValueOnce(response({ csrf_token: 'new' })).mockResolvedValueOnce(response(session()))
    await expect(restoreSession()).resolves.toMatchObject({ id: 'user-1' })
    expect(fetchMock.mock.calls[3][1].headers['X-CSRF-Token']).toBe('new')
  })
  it('retorna mensagem útil de erro de rede', async () => {
    fetchMock.mockRejectedValueOnce(new TypeError('offline'))
    await expect(api.get('/units')).rejects.toBeInstanceOf(ApiError)
  })
})
