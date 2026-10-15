import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { clsx } from 'clsx'
import { useEffect, useState } from 'react'
import { api } from '../services/api'
import type { AppSettings } from '../types'

const navItems = [
  { to: '/dashboard',   label: 'Dashboard',         icon: '◼' },
  { to: '/transactions',label: 'Transactions',       icon: '⇆' },
  { to: '/import',      label: 'Import & Batches',   icon: '↑' },
  { to: '/recovery',    label: 'Recovery Agent',     icon: '⚡' },
  { to: '/evaluation',  label: 'Evaluation',         icon: '📊' },
  { to: '/audit',       label: 'Audit Trail',        icon: '📋' },
  { to: '/policy',      label: 'Policy Config',      icon: '🛡' },
  { to: '/settings',    label: 'Settings',           icon: '⚙' },
]

export default function Layout() {
  const [settings, setSettings] = useState<AppSettings | null>(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)

  useEffect(() => {
    api.getSettings().then(setSettings).catch(() => null)
  }, [])

  return (
    <div className="flex h-full min-h-screen">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-20 bg-black/40 lg:hidden" onClick={() => setSidebarOpen(false)} />
      )}

      {/* Sidebar */}
      <aside className={clsx(
        'fixed inset-y-0 left-0 z-30 flex w-64 flex-col bg-gray-900 transition-transform lg:static lg:translate-x-0',
        sidebarOpen ? 'translate-x-0' : '-translate-x-full'
      )}>
        {/* Logo */}
        <div className="flex items-center gap-3 px-5 py-4 border-b border-gray-700">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-600 text-white font-bold text-lg">R</div>
          <div>
            <div className="text-white font-semibold text-sm">RecoverAI</div>
            <div className="text-gray-400 text-xs">Revenue Recovery</div>
          </div>
        </div>

        {/* Provider status */}
        {settings && (
          <div className="px-4 py-2 border-b border-gray-700">
            <div className="flex items-center gap-2 text-xs text-gray-400">
              <span className={clsx('h-2 w-2 rounded-full', settings.llm_configured ? 'bg-green-400' : 'bg-yellow-400')} />
              AI: {settings.ai_provider}
            </div>
            <div className="flex items-center gap-2 text-xs text-gray-400 mt-1">
              <span className="h-2 w-2 rounded-full bg-blue-400" />
              {settings.payment_provider} {settings.is_live_payment ? '🔴 LIVE' : '(simulated)'}
            </div>
          </div>
        )}

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
          {navItems.map(({ to, label, icon }) => (
            <NavLink
              key={to}
              to={to}
              onClick={() => setSidebarOpen(false)}
              className={({ isActive }) => clsx(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors',
                isActive
                  ? 'bg-brand-600 text-white font-medium'
                  : 'text-gray-300 hover:bg-gray-800 hover:text-white'
              )}
            >
              <span className="text-base">{icon}</span>
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-gray-700 text-xs text-gray-500">
          v{settings?.version ?? '1.0.0'} · {settings?.environment ?? 'development'}
        </div>
      </aside>

      {/* Main */}
      <div className="flex flex-1 flex-col min-w-0">
        {/* Top bar */}
        <header className="flex items-center gap-4 border-b border-gray-200 bg-white px-4 py-3 lg:px-6">
          <button
            className="lg:hidden text-gray-500 hover:text-gray-700"
            onClick={() => setSidebarOpen(true)}
          >
            ☰
          </button>
          <div className="flex-1" />
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <span className="hidden sm:block">Razorpay AI Buildathon</span>
            {settings && !settings.is_live_payment && (
              <span className="badge bg-blue-100 text-blue-700">Simulation Mode</span>
            )}
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-4 lg:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
