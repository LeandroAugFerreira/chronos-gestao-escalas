import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../services/client'
import type { Catalog, Department, Page, Unit } from '../types/domain'

export async function allPages<T>(path: string, signal?: AbortSignal) {
  const items: T[] = []
  let page = 1
  while (true) {
    const result = await api.get<Page<T>>(path + (path.includes('?') ? '&' : '?') + `page_number=${page}&page_size=100`, signal)
    items.push(...result.items)
    if (items.length >= result.total || result.items.length === 0) return items
    page++
  }
}
export function useReferenceData() {
  return useQuery({ queryKey: ['references'], queryFn: async ({ signal }) => {
    const [units, departments, roles] = await Promise.all([allPages<Unit>('/units', signal), allPages<Department>('/departments', signal), allPages<Catalog>('/catalogs/job-roles', signal)])
    return { units, departments, roles }
  }, staleTime: 30000 })
}
export function useDebounced(value: string, delay = 250) {
  const [result, setResult] = useState(value)
  useEffect(() => { const id = setTimeout(() => setResult(value), delay); return () => clearTimeout(id) }, [value, delay])
  return result
}
