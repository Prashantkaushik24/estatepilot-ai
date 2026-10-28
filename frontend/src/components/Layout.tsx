import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { LayoutDashboard, Mail, Users, Building2, Target, CalendarCheck, Zap, ScrollText, BarChart3, Settings, Bell, Sun, Moon, Menu, LogOut, Plane } from 'lucide-react'
import { useAuth } from '../lib/auth'
import { useTheme } from '../lib/theme'
import { api } from '../lib/api'
import { fmtDate } from '../lib/format'
import { useToast } from '../lib/toast'
import type { Notification } from '../types'

const nav = [
  { to: '/', label: 'Overview', icon: LayoutDashboard }, { to: '/inbox', label: 'Inbox', icon: Mail }, { to: '/leads', label: 'Leads', icon: Users },
  { to: '/properties', label: 'Properties', icon: Building2 }, { to: '/matching', label: 'Matching', icon: Target }, { to: '/followups', label: 'Follow-ups', icon: CalendarCheck },
  { to: '/automation', label: 'Automation', icon: Zap }, { to: '/activity', label: 'Activity', icon: ScrollText }, { to: '/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/settings', label: 'Settings', icon: Settings },
]

function Bell_() {
  const [open, setOpen] = useState(false)
  const qc = useQueryClient(); const toast = useToast()
  const q = useQuery({ queryKey: ['notifications'], queryFn: () => api.get<any>('/notifications'), refetchInterval: 60_000 })
  const items: Notification[] = Array.isArray(q.data) ? q.data : q.data?.items || []
  const unread = items.filter((n) => !n.is_read && !n.read).length
  const read = async (id: Notification['id']) => { try { await api.post(`/notifications/${id}/read`); qc.invalidateQueries({ queryKey: ['notifications'] }) } catch (e) { toast.error(e) } }
  return (
    <div className="relative">
      <button className="btn-ghost relative !p-2" aria-label={`Notifications (${unread} unread)`} aria-expanded={open} onClick={() => setOpen(!open)}>
        <Bell className="h-5 w-5" />
        {unread > 0 && <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-600 px-1 text-[10px] text-white">{unread}</span>}
      </button>
      {open && (
        <div className="absolute right-0 z-40 mt-2 max-h-96 w-80 overflow-auto rounded-xl border bg-white p-2 shadow-xl dark:border-slate-700 dark:bg-slate-900">
          {q.isError ? <p className="p-3 text-sm text-red-600">Could not load notifications</p> : items.length === 0 ? <p className="p-3 text-sm text-slate-500">No notifications</p> :
            items.map((n) => {
              const isRead = !!(n.is_read || n.read)
              return (
                <div key={String(n.id)} className={`rounded-lg p-2 text-sm ${isRead ? 'opacity-60' : 'bg-teal-50 dark:bg-teal-950/40'}`}>
                  <p className="font-medium">{String(n.title ?? n.message ?? 'Notification')}</p>
                  {n.title && n.message ? <p className="text-slate-500">{String(n.message)}</p> : null}
                  <div className="mt-1 flex items-center justify-between text-xs text-slate-500">
                    <span>{n.created_at ? fmtDate(String(n.created_at)) : ''}</span>
                    {!isRead && <button className="text-teal-600 underline" onClick={() => read(n.id)}>Mark read</button>}
                  </div>
                </div>
              )
            })}
        </div>
      )}
    </div>
  )
}

export default function Layout() {
  const { user, logout } = useAuth(); const { theme, toggle } = useTheme()
  const [menu, setMenu] = useState(false)
  return (
    <div className="flex min-h-screen">
      {menu && <div className="fixed inset-0 z-30 bg-black/40 lg:hidden" onClick={() => setMenu(false)} />}
      <aside className={`fixed inset-y-0 left-0 z-40 w-60 transform bg-navy-900 text-slate-300 transition lg:static lg:translate-x-0 ${menu ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="flex items-center gap-2 px-5 py-5 text-lg font-bold text-white"><Plane className="h-6 w-6 text-teal-400" aria-hidden />EstatePilot AI</div>
        <nav aria-label="Main" className="space-y-1 px-3">
          {nav.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} end={to === '/'} onClick={() => setMenu(false)}
              className={({ isActive }) => `flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition ${isActive ? 'bg-teal-600/20 text-teal-300' : 'hover:bg-white/10'}`}>
              <Icon className="h-4 w-4" aria-hidden />{label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex items-center justify-between border-b bg-white/90 px-4 py-2 backdrop-blur dark:border-slate-800 dark:bg-slate-900/90">
          <button className="btn-ghost lg:hidden" aria-label="Open menu" onClick={() => setMenu(true)}><Menu className="h-5 w-5" /></button>
          <div className="flex-1" />
          <div className="flex items-center gap-2">
            <button className="btn-ghost !p-2" onClick={toggle} aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}>{theme === 'dark' ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}</button>
            <Bell_ />
            <div className="hidden text-right text-xs sm:block"><div className="font-medium">{user?.full_name}</div><div className="text-slate-500">{user?.role}</div></div>
            <button className="btn-ghost !p-2" onClick={logout} aria-label="Log out" title="Log out"><LogOut className="h-5 w-5" /></button>
          </div>
        </header>
        <main className="flex-1 p-4 lg:p-6"><Outlet /></main>
      </div>
    </div>
  )
}
