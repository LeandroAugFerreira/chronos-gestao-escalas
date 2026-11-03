import { Suspense, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import { Activity, Building2, CalendarDays, ChartNoAxesCombined, CircleDollarSign, FileClock, FolderKanban, Layers3, LayoutDashboard, LogOut, Menu, Moon, Network, ShieldCheck, SlidersHorizontal, Sun, Users, Workflow, X } from 'lucide-react'
import { useAuth } from '../hooks/auth'
import { api } from '../services/client'
import { globalPermission, permits, type Organization } from '../types/domain'
import { Failure, Loading } from '../components/ui'
import { AuthorSignature, Brand } from '../components/identity'

const navigation = [
  { label: 'Planejamento', links: [
    { to: '/', label: 'Visão geral', icon: LayoutDashboard, permission: 'org:read' },
    { to: '/colaboradores', label: 'Colaboradores', icon: Users, permission: 'people:read' },
    { to: '/calendario', label: 'Calendário', icon: CalendarDays, permission: 'schedule:read' },
    { to: '/cenarios', label: 'Cenários', icon: FolderKanban, permission: 'scenario:read' },
    { to: '/otimizacao', label: 'Otimização de escalas', icon: Activity, permission: 'optimization:read' },
    { to: '/financeiro', label: 'Simulador financeiro', icon: CircleDollarSign, permission: 'finance:read' },
    { to: '/analytics', label: 'Analytics e exportações', icon: ChartNoAxesCombined, permission: 'scenario:read' },
  ] },
  { label: 'Estrutura & operação', links: [
    { to: '/setores', label: 'Setores', icon: Network, permission: 'org:read' },
    { to: '/unidades', label: 'Unidades', icon: Building2, permission: 'org:read' },
    { to: '/catalogos', label: 'Catálogos', icon: Layers3, permission: 'catalog:read' },
    { to: '/regras', label: 'Jornadas e regras', icon: SlidersHorizontal, permission: 'rules:read' },
    { to: '/automacoes', label: 'Central de automações', icon: Workflow, permission: 'automation:read' },
  ] },
  { label: 'Administração', links: [
    { to: '/acessos', label: 'Acessos', icon: ShieldCheck, permission: 'users:write', global: true },
    { to: '/auditoria', label: 'Auditoria', icon: FileClock, permission: 'audit:read', global: true },
  ] },
]

function initialTheme() {
  try { return localStorage.getItem('chronos-theme') === 'light' ? 'light' : 'dark' }
  catch { return 'dark' }
}

export function Layout() {
  const { user, logout } = useAuth()
  const location = useLocation()
  const [open, setOpen] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  const [leaving, setLeaving] = useState(false)
  const [theme, setTheme] = useState(initialTheme)
  const organization = useQuery({ queryKey: ['organization'], queryFn: ({ signal }) => api.get<{ items: Organization[] }>('/organizations', signal) })
  const groups = navigation.map(group => ({ ...group, links: group.links.filter(link => 'global' in link && link.global ? globalPermission(user, link.permission) : permits(user, link.permission)) })).filter(group => group.links.length)
  const title = navigation.flatMap(group => group.links).find(link => link.to === location.pathname)?.label || 'Detalhe do colaborador'
  const org = organization.data?.items[0]
  function toggleTheme() {
    const next = theme === 'dark' ? 'light' : 'dark'
    setTheme(next)
    try { localStorage.setItem('chronos-theme', next) } catch { /* Preferência apenas em memória. */ }
  }

  return <div className="app" data-theme={theme}>
    <a className="skip-link" href="#conteudo">Ir para o conteúdo</a>
    {open && <button className="sidebar-scrim" aria-label="Fechar navegação" onClick={() => setOpen(false)} />}
    <aside className={'sidebar ' + (open ? 'is-open' : '')}>
      <Link className="brand" to="/" onClick={() => setOpen(false)} aria-label="Chronos 1.0, início"><Brand compact /></Link>
      <button className="mobile-close icon-button" onClick={() => setOpen(false)} aria-label="Fechar menu"><X size={20} /></button>
      <div className="workspace-label">SEU ESPAÇO</div>
      <div className="workspace"><span>{org?.name.split(' ').slice(0, 2).map(word => word[0]).join('') || '…'}</span><div><b>{org?.name || 'Carregando organização…'}</b><small>{org?.is_demo ? 'Ambiente de demonstração' : 'Organização'}</small></div></div>
      <nav className="main-navigation" id="navegacao-principal" aria-label="Navegação principal">{groups.map(group => <div className="nav-group" key={group.label}><p className="nav-label">{group.label}</p>{group.links.map(link => <NavLink key={link.to} to={link.to} end={link.to === '/'} onClick={() => setOpen(false)}><link.icon size={18} /><span>{link.label}</span></NavLink>)}</div>)}</nav>
      <div className="sidebar-bottom"><div className="sidebar-edition"><span>CHRONOS 1.0</span><span>Planejar com clareza.</span></div><div className="account"><span className="avatar">{user?.username.slice(0, 2).toUpperCase()}</span><div><b>{user?.username}</b><small>Conta autenticada</small></div><button className="icon-button" aria-label="Sair da plataforma" disabled={leaving} onClick={async () => { setLeaving(true); setError(null); try { await logout() } catch { setError(new Error('Não foi possível encerrar a sessão no servidor. Tente novamente.')) } finally { setLeaving(false) } }}><LogOut size={17} /></button></div></div>
    </aside>
    <div className="content">
      <header className="topbar"><div><button className="icon-button menu-toggle" aria-label="Abrir menu" aria-controls="navegacao-principal" aria-expanded={open} onClick={() => setOpen(!open)}><Menu size={21} /></button><span className="topbar-breadcrumb">Seu espaço <span className="header-divider">/</span> <b>{title}</b></span></div><div>{org?.is_demo && <span className="header-demo"><span className="status-dot" /> Demonstração</span>}<button className="icon-button theme-toggle" aria-label={theme === 'dark' ? 'Ativar tema claro' : 'Ativar tema escuro'} onClick={toggleTheme}>{theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}</button></div></header>
      <main id="conteudo" tabIndex={-1}>{error && <Failure error={error} />}{organization.isError && <Failure error={organization.error} retry={() => void organization.refetch()} />}<Suspense fallback={<Loading />}><Outlet /></Suspense><footer className="app-footer"><AuthorSignature /><div><span>Chronos 1.0 — Gestão Inteligente de Jornadas e Escalas</span><small>Pessoas e tempo, em equilíbrio.</small></div></footer></main>
    </div>
  </div>
}
