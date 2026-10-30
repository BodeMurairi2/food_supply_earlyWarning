import { BarChart3, Bot, FlaskConical, Gauge, History, LayoutDashboard, LineChart, Menu, Sprout, X } from 'lucide-react'
import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { useAppData } from '../hooks/AppData'
import { ErrorState } from './ui'

const NAV: { to: string; label: string; icon: typeof Bot; end?: boolean; soon?: boolean }[] = [
  { to: '/', label: 'Overview', icon: LayoutDashboard, end: true },
  { to: '/historical', label: 'Historical Analysis', icon: History },
  { to: '/forecasts', label: 'Forecasts (2025–2026)', icon: LineChart },
  { to: '/visualizations', label: 'Visualizations', icon: BarChart3 },
  { to: '/prediction-lab', label: 'Prediction Lab', icon: FlaskConical },
  { to: '/ai-analyst', label: 'AI Analyst', icon: Bot },
  { to: '/model-performance', label: 'Model Performance', icon: Gauge },
]

function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <nav className="flex h-full flex-col bg-sidebar px-3 py-5 text-emerald-50">
      <div className="mb-8 flex items-center gap-2 px-2">
        <Sprout className="h-6 w-6 text-emerald-400" />
        <span className="text-lg font-semibold tracking-tight">HarvestWatch</span>
      </div>
      <ul className="space-y-1">
        {NAV.map(({ to, label, icon: Icon, end, soon }) => (
          <li key={to}>
            <NavLink to={to} end={end} onClick={onNavigate}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
                  isActive ? 'bg-sidebar-active font-medium text-white' : 'text-emerald-100/80 hover:bg-white/5 hover:text-white'}`}>
              <Icon className="h-4 w-4" />
              <span className="flex-1">{label}</span>
              {soon && <span className="rounded bg-white/10 px-1.5 py-0.5 text-[10px] uppercase tracking-wide">Next</span>}
            </NavLink>
          </li>
        ))}
      </ul>
      <p className="mt-auto px-2 text-[11px] leading-relaxed text-emerald-100/50">
        NISR 2026 Big Data Hackathon · Track 1<br />Data: NISR CFSVA & SAS, WFP, CHIRPS, ERA5-Land
      </p>
    </nav>
  )
}

export default function Layout() {
  const [open, setOpen] = useState(false)
  const { error } = useAppData()
  return (
    <div className="flex h-full">
      <aside className="hidden w-60 shrink-0 lg:block"><Sidebar /></aside>
      {open && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-black/40" onClick={() => setOpen(false)} />
          <aside className="absolute inset-y-0 left-0 w-64"><Sidebar onNavigate={() => setOpen(false)} /></aside>
        </div>
      )}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center gap-3 border-b border-gray-200 bg-white px-4 py-3 lg:hidden">
          <button onClick={() => setOpen(!open)} aria-label="Open menu">{open ? <X /> : <Menu />}</button>
          <Sprout className="h-5 w-5 text-brand" />
          <span className="font-semibold">HarvestWatch</span>
        </header>
        <main className="flex-1 overflow-y-auto px-4 py-6 md:px-8">
          {error ? <ErrorState message={error} /> : <Outlet />}
        </main>
      </div>
    </div>
  )
}
