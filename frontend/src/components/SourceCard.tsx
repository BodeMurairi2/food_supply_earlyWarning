import { ExternalLink } from 'lucide-react'
import type { AISource } from '../types/api'

/** A clickable web source used by the AI. */
export default function SourceCard({ s }: { s: AISource }) {
  let host = s.url
  try { host = new URL(s.url).hostname.replace(/^www\./, '') } catch { /* keep raw url */ }
  return (
    <a id={`source-${s.id}`} href={s.url} target="_blank" rel="noopener noreferrer"
      className={`card block scroll-mt-6 p-4 transition hover:border-blue-300 ${s.cited ? '' : 'opacity-70'}`}>
      <div className="mb-1 flex items-center gap-2 text-[11px] text-gray-500">
        <span className="rounded bg-blue-50 px-1.5 py-0.5 font-semibold text-blue-700">{s.id}</span>
        <span className="truncate">{host}</span>
        <span>·</span>
        <span>{s.published_date ? s.published_date.slice(0, 10) : 'date not given'}</span>
        <ExternalLink className="ml-auto h-3.5 w-3.5 shrink-0" />
      </div>
      <p className="text-sm font-medium text-gray-900">{s.title}</p>
      <p className="mt-1 line-clamp-3 text-xs text-gray-600">{s.snippet}</p>
      <p className="mt-2 text-[11px] text-gray-400">{s.cited ? 'Cited in the analysis' : 'Retrieved, not cited'} · search: “{s.query}”</p>
    </a>
  )
}
