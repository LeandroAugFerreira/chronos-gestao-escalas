import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { ApiError, restoreSession, signIn, signOut, subscribeSession, watchOtherTabs } from '../services/client'
import type { User } from '../types/domain'

type Auth = { user: User | null; loading: boolean; message: string; login: typeof signIn; logout: () => Promise<void> }
const Context = createContext<Auth | null>(null)
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [message, setMessage] = useState('')
  const previous = useRef<string | null>(null)
  const cache = useQueryClient()
  useEffect(() => {
    const unsubscribe = subscribeSession((next, notice) => {
      const nextId = next ? next.organization_id + next.id : null
      if (previous.current !== nextId) { void cache.cancelQueries(); cache.clear(); previous.current = nextId }
      setUser(next); setMessage(notice || '')
    })
    const stop = watchOtherTabs()
    let alive = true
    restoreSession().catch(error => { if (alive && (!(error instanceof ApiError) || error.status !== 401)) setMessage(error.message) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false; unsubscribe(); stop() }
  }, [cache])
  return <Context.Provider value={{ user, loading, message, login: signIn, logout: signOut }}>{children}</Context.Provider>
}
export function useAuth() { const value = useContext(Context); if (!value) throw new Error('AuthProvider ausente'); return value }
