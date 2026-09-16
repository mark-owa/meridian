import { NavLink, Outlet } from 'react-router-dom'
import { BookOpen, FileSearch, LayoutDashboard, LogOut, Target } from 'lucide-react'
import clsx from 'clsx'
import { useAuth } from '../context/AuthContext'
import { MeridianMark } from './MeridianMark'

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/knowledge', label: 'Knowledge Base', icon: BookOpen },
  { to: '/extraction', label: 'Document Intelligence', icon: FileSearch },
  { to: '/leads', label: 'Leads', icon: Target },
]

export function Layout() {
  const { user, logout } = useAuth()

  return (
    <div className="flex min-h-screen bg-paper">
      <aside className="flex w-64 shrink-0 flex-col border-r border-ink-100 bg-paper-raised">
        <div className="flex items-center gap-2 px-5 py-5">
          <MeridianMark className="size-6" />
          <span className="font-display text-lg font-medium text-ink-900">Meridian</span>
        </div>

        <nav className="flex-1 space-y-1 px-3">
          {navItems.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-ink-900 text-white'
                    : 'text-ink-600 hover:bg-ink-50 hover:text-ink-900',
                )
              }
            >
              <Icon className="size-4" />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-ink-100 p-3">
          <div className="flex items-center justify-between rounded-md px-3 py-2">
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-ink-800">{user?.full_name}</p>
              <p className="truncate text-xs text-ink-400">{user?.company ?? user?.email}</p>
            </div>
            <button
              onClick={logout}
              aria-label="Log out"
              className="shrink-0 rounded-md p-1.5 text-ink-400 hover:bg-ink-50 hover:text-ink-700"
            >
              <LogOut className="size-4" />
            </button>
          </div>
        </div>
      </aside>

      <main className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-6xl px-8 py-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
