import { useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import clsx from 'clsx'
import { AnimatePresence, motion } from 'framer-motion'
import { Bell, BookOpen, FileText, GitCompare, LayoutDashboard, LogOut, Menu, Moon, ScrollText, Settings, Shield, Sun, Upload, Users, X, FlaskConical } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useTheme } from '../contexts/ThemeContext'
import { useFetch } from '../hooks/useFetch'
import { api } from '../services/api'
import type { Page, Notification, Role } from '../types'

interface Item { to: string; label: string; icon: typeof Bell; roles: Role[]; primary?: boolean }
export const NAV: Item[] = [
  { to: '/app/dashboard', label: 'Dashboard', icon: LayoutDashboard, roles: ['admin', 'faculty', 'student'], primary: true },
  { to: '/app/assignments', label: 'Assignments', icon: BookOpen, roles: ['admin', 'faculty', 'student'], primary: true },
  { to: '/app/submit', label: 'Submit code', icon: Upload, roles: ['student'], primary: true },
  { to: '/app/analysis', label: 'Analysis', icon: FlaskConical, roles: ['admin', 'faculty'], primary: true },
  { to: '/app/reports', label: 'Reports', icon: FileText, roles: ['admin', 'faculty'] },
  { to: '/app/users', label: 'Users', icon: Users, roles: ['admin'] },
  { to: '/app/audit-logs', label: 'Audit logs', icon: ScrollText, roles: ['admin'] },
  { to: '/app/notifications', label: 'Notifications', icon: Bell, roles: ['admin', 'faculty', 'student'] },
  { to: '/app/profile', label: 'Profile & settings', icon: Settings, roles: ['admin', 'faculty', 'student'] },
]

export default function AppLayout() {
  const { user, logout } = useAuth()
  const { dark, setTheme } = useTheme()
  const [drawer, setDrawer] = useState(false)
  const nav = useNavigate()
  const loc = useLocation()
  const unread = useFetch(() => api.get<Page<Notification>>('/notifications', { params: { unread_only: true, page_size: 1 } }).then((r) => r.data.unread ?? 0), [loc.pathname], { intervalMs: 30000 })
  if (!user) return null
  const items = NAV.filter((i) => i.roles.includes(user.role_name))
  const bottom = items.filter((i) => i.primary).slice(0, 4)

  const link = (i: Item, onClick?: () => void) => (
    <NavLink key={i.to} to={i.to} onClick={onClick}
      className={({ isActive }) => clsx('flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition',
        isActive ? 'bg-white/15 text-white' : 'text-navy-200 hover:bg-white/10 hover:text-white')}>
      <i.icon className="h-[18px] w-[18px]" />{i.label}
      {i.to === '/app/notifications' && !!unread.data && <span className="ml-auto rounded-full bg-amber-500 px-2 text-xs font-semibold text-navy-950">{unread.data}</span>}
    </NavLink>
  )

  const brand = (
    <div className="flex items-center gap-2.5 px-2 text-white">
      <div className="rounded-xl bg-gradient-to-br from-brand-400 to-brand-600 p-2"><GitCompare className="h-5 w-5" /></div>
      <div className="leading-tight"><div className="text-sm font-bold">CodeIntegrity</div><div className="text-[11px] text-navy-300">Plagiarism detection</div></div>
    </div>
  )

  return (
    <div className="min-h-screen lg:pl-64">
      {/* desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col bg-gradient-to-b from-navy-900 to-brand-900 p-4 lg:flex">
        {brand}
        <nav className="mt-8 flex-1 space-y-1" aria-label="Main">{items.map((i) => link(i))}</nav>
        <div className="rounded-xl bg-white/10 p-3 text-xs text-navy-100">
          <div className="truncate font-semibold text-white">{user.full_name}</div>
          <div className="mb-2 flex items-center gap-1 capitalize"><Shield className="h-3 w-3" />{user.role_name}</div>
          <button onClick={() => { logout(); nav('/login') }} className="flex items-center gap-1.5 text-navy-200 hover:text-white"><LogOut className="h-3.5 w-3.5" />Sign out</button>
        </div>
      </aside>

      {/* top bar */}
      <header className="sticky top-0 z-20 flex h-14 items-center justify-between border-b border-slate-200 bg-white/85 px-4 backdrop-blur dark:border-navy-800 dark:bg-navy-950/85 lg:px-8">
        <button className="rounded-lg p-2 lg:hidden" onClick={() => setDrawer(true)} aria-label="Open menu"><Menu className="h-5 w-5" /></button>
        <span className="font-semibold text-slate-900 lg:hidden dark:text-white">CodeIntegrity</span>
        <span className="hidden text-sm text-slate-500 lg:block">Welcome back, {user.full_name.split(' ')[0]}</span>
        <div className="flex items-center gap-1">
          <button onClick={() => setTheme(dark ? 'light' : 'dark')} className="rounded-lg p-2 hover:bg-slate-100 dark:hover:bg-navy-800" aria-label="Toggle dark mode">{dark ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}</button>
          <button onClick={() => nav('/app/notifications')} className="relative rounded-lg p-2 hover:bg-slate-100 dark:hover:bg-navy-800" aria-label={`Notifications${unread.data ? ` (${unread.data} unread)` : ''}`}>
            <Bell className="h-5 w-5" />{!!unread.data && <span className="absolute right-1 top-1 h-2.5 w-2.5 rounded-full bg-amber-500" />}
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-6 pb-28 lg:px-8 lg:pb-10"><Outlet /></main>

      {/* mobile bottom navigation */}
      <nav className="pb-safe fixed inset-x-0 bottom-0 z-30 grid border-t border-slate-200 bg-white/95 backdrop-blur lg:hidden dark:border-navy-800 dark:bg-navy-950/95"
        style={{ gridTemplateColumns: `repeat(${bottom.length + 1}, 1fr)` }} aria-label="Primary">
        {bottom.map((i) => (
          <NavLink key={i.to} to={i.to} className={({ isActive }) => clsx('flex flex-col items-center gap-0.5 py-2 text-[11px] font-medium', isActive ? 'text-brand-600 dark:text-brand-300' : 'text-slate-500')}>
            <i.icon className="h-5 w-5" />{i.label.split(' ')[0]}
          </NavLink>
        ))}
        <button onClick={() => setDrawer(true)} className="flex flex-col items-center gap-0.5 py-2 text-[11px] font-medium text-slate-500"><Menu className="h-5 w-5" />More</button>
      </nav>

      {/* mobile drawer */}
      <AnimatePresence>
        {drawer && (
          <div className="fixed inset-0 z-50 lg:hidden">
            <motion.div className="absolute inset-0 bg-navy-950/60" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setDrawer(false)} />
            <motion.aside initial={{ x: '-100%' }} animate={{ x: 0 }} exit={{ x: '-100%' }} transition={{ type: 'tween', duration: 0.2 }}
              className="absolute inset-y-0 left-0 flex w-72 max-w-[85vw] flex-col bg-gradient-to-b from-navy-900 to-brand-900 p-4">
              <div className="flex items-center justify-between">{brand}<button onClick={() => setDrawer(false)} className="p-2 text-white" aria-label="Close menu"><X className="h-5 w-5" /></button></div>
              <nav className="mt-6 flex-1 space-y-1 overflow-y-auto">{items.map((i) => link(i, () => setDrawer(false)))}</nav>
              <button onClick={() => { logout(); nav('/login') }} className="flex items-center gap-2 rounded-xl bg-white/10 px-3 py-3 text-sm text-white"><LogOut className="h-4 w-4" />Sign out ({user.full_name})</button>
            </motion.aside>
          </div>
        )}
      </AnimatePresence>
    </div>
  )
}
