import { AlertTriangle, Info, Loader2 } from 'lucide-react'
import type { ReactNode } from 'react'
import { RISK_COLORS } from '../lib/format'
import type { Risk } from '../types/api'

export function Card({ title, subtitle, actions, children, className = '' }: {
  title?: ReactNode; subtitle?: ReactNode; actions?: ReactNode; children: ReactNode; className?: string
}) {
  return (
    <section className={`card p-5 ${className}`}>
      {(title || actions) && (
        <div className="mb-4 flex flex-wrap items-start justify-between gap-2">
          <div>
            {title && <h2 className="text-sm font-semibold text-gray-900">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-xs text-gray-500">{subtitle}</p>}
          </div>
          {actions}
        </div>
      )}
      {children}
    </section>
  )
}

export function StatCard({ icon, label, value, hint, tone = 'brand' }: {
  icon: ReactNode; label: string; value: ReactNode; hint?: ReactNode; tone?: 'brand' | 'danger' | 'blue' | 'amber'
}) {
  const tones = {
    brand: 'bg-emerald-50 text-emerald-700',
    danger: 'bg-red-50 text-red-600',
    blue: 'bg-blue-50 text-blue-600',
    amber: 'bg-amber-50 text-amber-600',
  }
  return (
    <div className="card flex items-start gap-3 p-4">
      <div className={`rounded-lg p-2 ${tones[tone]}`}>{icon}</div>
      <div className="min-w-0">
        <p className="text-xs font-medium text-gray-500">{label}</p>
        <p className="mt-1 text-2xl font-semibold text-gray-900">{value}</p>
        {hint && <p className="mt-0.5 text-xs text-gray-500">{hint}</p>}
      </div>
    </div>
  )
}

export function RiskBadge({ risk }: { risk: Risk | null | undefined }) {
  if (!risk) return <span className="text-xs text-gray-400">—</span>
  const color = RISK_COLORS[risk]
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-semibold"
      style={{ color, backgroundColor: `${color}1a` }}>
      <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: color }} />
      {risk}
    </span>
  )
}

export function Loading({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-10 text-sm text-gray-500">
      <Loader2 className="h-4 w-4 animate-spin" /> {label}
    </div>
  )
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-6 text-center">
      <AlertTriangle className="h-5 w-5 text-red-500" />
      <p className="text-sm text-red-700">{message}</p>
      {onRetry && <button className="btn-secondary" onClick={onRetry}>Try again</button>}
    </div>
  )
}

export function EmptyState({ message }: { message: string }) {
  return <p className="py-8 text-center text-sm text-gray-500">{message}</p>
}

export function Note({ children }: { children: ReactNode }) {
  return (
    <p className="flex items-start gap-2 rounded-lg bg-gray-50 px-3 py-2 text-xs text-gray-600">
      <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-gray-400" />
      <span>{children}</span>
    </p>
  )
}

export function Pagination({ page, pages, onChange, total, pageSize }: {
  page: number; pages: number; onChange: (p: number) => void; total: number; pageSize: number
}) {
  if (pages <= 1) return null
  const from = (page - 1) * pageSize + 1
  const to = Math.min(page * pageSize, total)
  return (
    <div className="mt-3 flex items-center justify-between text-xs text-gray-500">
      <span>Showing {from}–{to} of {total}</span>
      <div className="flex gap-1">
        {Array.from({ length: pages }, (_, i) => i + 1).map((p) => (
          <button key={p} onClick={() => onChange(p)}
            className={`h-7 w-7 rounded-md text-xs ${p === page ? 'bg-brand text-white' : 'border border-gray-200 hover:bg-gray-50'}`}>
            {p}
          </button>
        ))}
      </div>
    </div>
  )
}

export function PageHeader({ title, subtitle, children }: { title: string; subtitle?: string; children?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-xl font-semibold text-gray-900">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-gray-500">{subtitle}</p>}
      </div>
      {children}
    </div>
  )
}
