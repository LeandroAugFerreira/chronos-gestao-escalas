import { lazy } from 'react'
import { Link, Navigate, Outlet, Route, Routes } from 'react-router-dom'
import { ShieldCheck } from 'lucide-react'
import { useAuth } from './hooks/auth'
import { globalPermission, permits } from './types/domain'
import { Loading } from './components/ui'
import { ChronosMark } from './components/identity'
import { Layout } from './layouts/app-shell'
import { LoginPage } from './pages/login'
import { EmployeesPage, EmployeeDetailPage } from './pages/employees'
import { CatalogsPage, StructurePage } from './pages/structure'
import { AuditPage, UsersPage } from './pages/administration'

const OverviewPage = lazy(() => import('./pages/overview').then(module => ({ default: module.OverviewPage })))
const CalendarPage = lazy(() => import('./pages/scheduling').then(module => ({ default: module.CalendarPage })))
const ScenariosPage = lazy(() => import('./pages/simulation').then(module => ({ default: module.ScenariosPage })))
const FinancialPage = lazy(() => import('./pages/simulation').then(module => ({ default: module.FinancialPage })))
const AutomationPage = lazy(() => import('./pages/automation').then(module => ({ default: module.AutomationPage })))
const AnalyticsPage = lazy(() => import('./pages/analytics').then(module => ({ default: module.AnalyticsPage })))
const OptimizationPage = lazy(() => import('./pages/optimization').then(module => ({ default: module.OptimizationPage })))
const RulesPage = lazy(() => import('./pages/scheduling').then(module => ({ default: module.RulesPage })))

function RequirePermission({ permission, global = false }: { permission: string; global?: boolean }) {
  const { user } = useAuth()
  const allowed = global ? globalPermission(user, permission) : permits(user, permission)
  return allowed ? <Outlet /> : <section className="panel forbidden"><ShieldCheck size={34} /><h1>Acesso restrito</h1><p>Seu perfil não possui permissão para esta área.</p><Link className="button secondary" to="/">Voltar à visão geral</Link></section>
}

export function App() {
  const { user, loading } = useAuth()
  if (loading) return <div className="initial-loading"><ChronosMark /><Loading /></div>
  if (!user) return <Routes><Route path="/login" element={<LoginPage />} /><Route path="*" element={<Navigate to="/login" replace />} /></Routes>
  return <Routes><Route path="/login" element={<Navigate to="/" replace />} /><Route element={<Layout />}><Route element={<RequirePermission permission="org:read" />}><Route index element={<OverviewPage />} /><Route path="/setores" element={<StructurePage key="departments" kind="departments" />} /><Route path="/unidades" element={<StructurePage key="units" kind="units" />} /></Route><Route element={<RequirePermission permission="people:read" />}><Route path="/colaboradores" element={<EmployeesPage />} /><Route path="/colaboradores/:id" element={<EmployeeDetailPage />} /></Route><Route element={<RequirePermission permission="scenario:read" />}><Route path="/cenarios" element={<ScenariosPage />} /><Route path="/analytics" element={<AnalyticsPage />} /></Route><Route element={<RequirePermission permission="automation:read" />}><Route path="/automacoes" element={<AutomationPage />} /></Route><Route element={<RequirePermission permission="optimization:read" />}><Route path="/otimizacao" element={<OptimizationPage />} /></Route><Route element={<RequirePermission permission="finance:read" />}><Route path="/financeiro" element={<FinancialPage />} /></Route><Route element={<RequirePermission permission="schedule:read" />}><Route path="/calendario" element={<CalendarPage />} /></Route><Route element={<RequirePermission permission="rules:read" />}><Route path="/regras" element={<RulesPage />} /></Route><Route element={<RequirePermission permission="catalog:read" />}><Route path="/catalogos" element={<CatalogsPage />} /></Route><Route element={<RequirePermission permission="users:write" global />}><Route path="/acessos" element={<UsersPage />} /></Route><Route element={<RequirePermission permission="audit:read" global />}><Route path="/auditoria" element={<AuditPage />} /></Route><Route path="*" element={<section className="panel forbidden"><h1>Página não encontrada</h1><Link to="/" className="button secondary">Voltar ao início</Link></section>} /></Route></Routes>
}


