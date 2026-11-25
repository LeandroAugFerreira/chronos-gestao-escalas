import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { beforeEach, expect, it, vi } from 'vitest'
import { LaborTransitionPage, type TransitionResult } from '../pages/labor-transition'
import { api } from '../services/client'

const phase = { id: 'transition_42', name: 'Etapa de 42 horas', from: '2026-12-16', until: '2027-12-16', weekly_minutes: 2520, rest_days: 2, monthly_divisor_hours: 210 }
const fixture: TransitionResult = { phase, effective_weekly_minutes: 2520, monthly_divisor_hours: '210', monthly_salary_cents: 330000, baseline_hourly_cents: 1500, hourly_cents: 1571, hourly_change_percent: '4.76', status: 'review_required', digest: 'test-digest', findings: [{ code: 'SCOPE_REVIEW', status: 'review', message: 'Exige revisão humana do enquadramento.', source_ids: ['ec141'] }], sources: [], policy_version: 'br-ec141-2026.11.25', reviewed_on: '2026-11-25' }
function mount() {
  return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })}><LaborTransitionPage /></QueryClientProvider>)
}
beforeEach(() => {
  vi.spyOn(api, 'get').mockResolvedValue({ phases: [phase], sources: [], policy_version: fixture.policy_version, reviewed_on: fixture.reviewed_on, scope: 'Premissas declaradas.' })
  vi.spyOn(api, 'send').mockResolvedValue(fixture)
})

it('submits declared assumptions and renders the server result with review status', async () => {
  const user = userEvent.setup(); mount()
  await screen.findByRole('heading', { name: 'Etapas da transição' })
  expect(screen.getByRole('link', { name: 'Conhecer a versão 1.0' })).toHaveAttribute('href', 'https://leandroaugferreira.github.io/chronos-1.0.html')
  await user.click(screen.getByRole('button', { name: 'Comparar etapas' }))
  await screen.findByText('Comparação pronta para revisão')
  expect(api.send).toHaveBeenCalledWith('/labor-transition/compare', 'POST', expect.objectContaining({ reference_date: '2026-12-16', monthly_salary_cents: 330000, contract_weekly_minutes: 2640, regime: 'regular', use_interim_daily_exception: false }))
  expect(screen.getByText(/Exige revisão humana/)).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Exportar comparação e fontes' })).toBeEnabled()
})

it('clears a completed comparison when assumptions change, avoiding stale results', async () => {
  const user = userEvent.setup(); mount()
  await user.click(screen.getByRole('button', { name: 'Comparar etapas' }))
  await screen.findByText('Comparação pronta para revisão')
  await user.selectOptions(screen.getByLabelText('Regime em análise'), '12x36')
  await waitFor(() => expect(screen.queryByText('Comparação pronta para revisão')).not.toBeInTheDocument())
  await user.click(screen.getByRole('button', { name: 'Comparar etapas' }))
  await waitFor(() => expect(api.send).toHaveBeenLastCalledWith('/labor-transition/compare', 'POST', expect.objectContaining({ regime: '12x36' })))
})

it('shows a failed request without presenting a successful comparison', async () => {
  vi.mocked(api.send).mockRejectedValue(new Error('Serviço indisponível'))
  const user = userEvent.setup(); mount()
  await user.click(screen.getByRole('button', { name: 'Comparar etapas' }))
  expect(await screen.findByText('Serviço indisponível')).toBeInTheDocument()
  expect(screen.queryByText('Comparação pronta para revisão')).not.toBeInTheDocument()
})
