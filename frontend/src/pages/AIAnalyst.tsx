import { AlertTriangle, Bot, Loader2, Search, Sparkles } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import SourceCard from '../components/SourceCard'
import { LocationFilters, YearSelect, type LocationValue } from '../components/LocationFilters'
import { Card, ErrorState, Loading, Note, PageHeader, RiskBadge } from '../components/ui'
import { useAppData } from '../hooks/AppData'
import { useApi } from '../hooks/useApi'
import { pct, signed } from '../lib/format'
import { api } from '../services/api'
import type { AIResult } from '../types/api'

const YEARS = [2026, 2025, 2024, 2023, 2022, 2021]
const SUGGESTIONS = [
  'What is the rainfall outlook for the next Season A?',
  'Are bean and maize prices rising in Rwanda?',
  'Recent crop production or harvest problems in this province',
  'Floods, landslides or drought affecting this area',
]

// The three kinds of content are always labelled, so readers can tell model numbers from web facts and AI reasoning.
const KINDS = {
  model: { label: 'Model output', cls: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  web: { label: 'Web evidence', cls: 'bg-blue-50 text-blue-700 border-blue-200' },
  ai: { label: 'AI interpretation', cls: 'bg-violet-50 text-violet-700 border-violet-200' },
  scenario: { label: 'Conditional scenarios, not a forecast', cls: 'bg-amber-50 text-amber-700 border-amber-200' },
}

function Kind({ kind }: { kind: keyof typeof KINDS }) {
  return <span className={`rounded-full border px-2 py-0.5 text-[11px] font-medium ${KINDS[kind].cls}`}>{KINDS[kind].label}</span>
}

function SourceChips({ ids }: { ids: string[] }) {
  return (
    <>
      {ids.map((id) => (
        <a key={id} href={`#source-${id}`} className="ml-1 rounded bg-blue-50 px-1.5 py-0.5 text-[11px] font-medium text-blue-700 hover:underline">{id}</a>
      ))}
    </>
  )
}

function Section({ title, kinds, children }: { title: string; kinds: (keyof typeof KINDS)[]; children: React.ReactNode }) {
  return (
    <Card title={<span className="flex flex-wrap items-center gap-2">{title} {kinds.map((k) => <Kind key={k} kind={k} />)}</span>}>
      {children}
    </Card>
  )
}

export default function AIAnalyst() {
  const { provinceOf } = useAppData()
  const [params] = useSearchParams()
  const initial = params.get('district') || 'Rutsiro'
  const [loc, setLoc] = useState<LocationValue>({ province: '', district: initial })
  const [year, setYear] = useState(Number(params.get('year')) || 2026)
  const [question, setQuestion] = useState('')
  const [result, setResult] = useState<AIResult | null>(null)
  const [running, setRunning] = useState(false)
  const [runError, setRunError] = useState<string | null>(null)
  const [elapsed, setElapsed] = useState(0)
  const timer = useRef<number | undefined>(undefined)

  useEffect(() => {
    const p = provinceOf(loc.district)
    if (p && !loc.province) setLoc((l) => ({ ...l, province: p }))
  }, [provinceOf, loc.district, loc.province])

  const status = useApi(api.aiStatus, [])
  // The model numbers are cheap and shown at once; the web research runs only when the user clicks.
  const ctx = useApi(() => api.aiContext(loc.district, year), [loc.district, year], !!loc.district)
  const ready = status.data?.llm && status.data?.search

  useEffect(() => { setResult(null); setRunError(null) }, [loc.district, year])
  useEffect(() => () => window.clearInterval(timer.current), [])

  const run = async () => {
    if (!loc.district) return
    setRunning(true); setRunError(null); setResult(null); setElapsed(0)
    const start = Date.now()
    timer.current = window.setInterval(() => setElapsed(Math.round((Date.now() - start) / 1000)), 1000)
    try {
      setResult(await api.aiAnalyze({ district: loc.district, year, question: question.trim() || undefined }))
    } catch (e) {
      setRunError((e as Error).message)
    } finally {
      window.clearInterval(timer.current)
      setRunning(false)
    }
  }

  const a = result?.analysis
  const c = ctx.data
  return (
    <>
      <PageHeader title="AI Analyst" subtitle="Model results explained with web research, sources and practical recommendations" />

      <div className="space-y-6">
        {status.data && !ready && (
          <div className="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>
              AI research is not configured.{' '}
              {!status.data.llm && <>Add <code>OPENROUTER_API_KEY</code> </>}
              {!status.data.llm && !status.data.search && 'and '}
              {!status.data.search && <>add <code>TAVILY_API_KEY</code> </>}
              to <code>.env</code> in the project root (see <code>.env.example</code>) and restart the API. Model results below still work.
            </span>
          </div>
        )}

        <Card>
          <div className="flex flex-wrap items-end gap-3">
            <LocationFilters value={loc} onChange={setLoc} allowAll={false} />
            <YearSelect value={year} onChange={(y) => setYear(Number(y))} years={YEARS} />
          </div>
          <label className="mt-4 block">
            <span className="mb-1 block text-xs font-medium text-gray-500">Research question (optional)</span>
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
              <input className="select pl-9" maxLength={300} value={question} placeholder="e.g. Is the next rainy season expected to be below normal?"
                onChange={(e) => setQuestion(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter' && ready && !running) run() }} />
            </div>
          </label>
          <div className="mt-3 flex flex-wrap gap-2">
            {SUGGESTIONS.map((s) => (
              <button key={s} onClick={() => setQuestion(s)}
                className="rounded-full border border-gray-200 px-3 py-1 text-xs text-gray-600 hover:border-brand hover:text-brand">{s}</button>
            ))}
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button className="btn-primary" onClick={run} disabled={!ready || running || !loc.district}>
              {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
              {running ? `Researching… ${elapsed}s` : 'Run analysis'}
            </button>
            <span className="text-xs text-gray-500">
              Runs up to 4 web searches and one AI model call. {status.data && <>Model: <code>{status.data.model}</code></>}
            </span>
          </div>
        </Card>

        <Section title={`Model result: ${loc.district || '…'}, ${year}`} kinds={['model']}>
          {ctx.loading && <Loading />}
          {ctx.error && <ErrorState message={ctx.error} onRetry={ctx.reload} />}
          {c && (
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
              <div>
                <div className="flex items-end gap-3">
                  <p className="text-4xl font-semibold text-gray-900">{pct(c.model.prediction_pct)}</p>
                  <div className="pb-1"><RiskBadge risk={c.model.risk_class} /></div>
                </div>
                <p className="mt-2 text-xs text-gray-500">{c.model.target}. {c.model.name}.</p>
                <p className="mt-1 text-xs text-gray-500">
                  {c.model.observed_pct_this_year !== null ? `Survey value this year: ${pct(c.model.observed_pct_this_year)}. ` : 'No survey value for this year. '}
                  Model average {pct(c.model.model_average_pct)}. Typical error: {c.model.typical_error_points}.
                </p>
              </div>
              <div>
                <p className="mb-2 text-xs font-semibold text-gray-700">Largest contributions (points)</p>
                <ul className="space-y-1 text-xs">
                  {c.contributions.slice(0, 6).map((x) => (
                    <li key={x.feature} className="flex justify-between gap-3">
                      <span className="text-gray-700">{x.feature}</span>
                      <span className={`tabular-nums font-medium ${x.points > 0 ? 'text-red-600' : 'text-green-700'}`}>{signed(x.points, 1)}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <p className="mb-2 text-xs font-semibold text-gray-700">Survey history</p>
                <div className="flex flex-wrap gap-1.5">
                  {c.survey_history.map((h) => (
                    <span key={h.year} className="rounded border border-gray-100 px-2 py-1 text-[11px] text-gray-600">
                      {h.year}: <b className="text-gray-900">{pct(h.pct)}</b>
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}
        </Section>

        {runError && <ErrorState message={runError} onRetry={ready ? run : undefined} />}
        {running && (
          <div className="card flex items-center gap-3 p-5 text-sm text-gray-600">
            <Bot className="h-5 w-5 text-brand" />
            The analyst is searching the web and reading the results. This usually takes 20–60 seconds.
          </div>
        )}

        {result && a && (
          <>
            <Section title="Forecast interpretation" kinds={['ai']}>
              <p className="text-sm leading-relaxed text-gray-700">{a.interpretation}</p>
            </Section>

            <Section title="Key model drivers" kinds={['model', 'ai']}>
              <p className="mb-3 text-xs text-gray-500">Points are SHAP contributions from the model; the explanations are the AI's reading. Associations, not proven causes.</p>
              <ul className="divide-y divide-gray-100">
                {a.drivers.map((d) => (
                  <li key={d.feature} className="flex gap-4 py-2.5">
                    <span className={`w-14 shrink-0 text-right text-sm font-semibold tabular-nums ${d.direction === 'raises' ? 'text-red-600' : 'text-green-700'}`}>
                      {signed(d.direction === 'lowers' ? -Math.abs(d.points) : Math.abs(d.points), 1)}
                    </span>
                    <div>
                      <p className="text-sm font-medium text-gray-900">{d.feature}</p>
                      <p className="text-xs text-gray-600">{d.explanation}</p>
                    </div>
                  </li>
                ))}
              </ul>
            </Section>

            <Section title="External evidence" kinds={['web']}>
              {a.external_evidence.length === 0 ? (
                <p className="text-sm text-gray-500">No reliable external evidence was found for this district and year.</p>
              ) : (
                <ul className="space-y-3">
                  {a.external_evidence.map((e, i) => (
                    <li key={i} className="rounded-lg border border-gray-100 p-3">
                      <p className="text-sm text-gray-800">{e.finding}<SourceChips ids={e.sources} /></p>
                      <p className="mt-1.5 flex flex-wrap gap-2 text-[11px] text-gray-500">
                        <span className="rounded bg-gray-100 px-1.5 py-0.5">Scope: {e.scope}</span>
                        <span className="rounded bg-gray-100 px-1.5 py-0.5">Credibility: {e.credibility}</span>
                        <span>{e.relevance}</span>
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </Section>

            <Section title="Potential implications for 2027" kinds={['scenario']}>
              <ul className="space-y-3">
                {a.implications_2027.map((s, i) => (
                  <li key={i}>
                    <p className="text-sm text-gray-800">{s.scenario}</p>
                    <p className="text-xs text-gray-500">Uncertainty: {s.uncertainty}</p>
                  </li>
                ))}
              </ul>
            </Section>

            <Section title="Recommended actions" kinds={['ai']}>
              <ol className="list-decimal space-y-3 pl-5">
                {a.recommendations.map((r, i) => (
                  <li key={i}>
                    <p className="text-sm font-medium text-gray-900">{r.action}<SourceChips ids={r.sources} /></p>
                    <p className="text-xs text-gray-600">{r.rationale}</p>
                  </li>
                ))}
              </ol>
            </Section>

            <div>
              <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-gray-900">Sources <Kind kind="web" /></h2>
              {result.sources.length === 0 ? <Note>No web results were retrieved.</Note> : (
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
                  {[...result.sources].sort((x, y) => Number(y.cited) - Number(x.cited)).map((s) => <SourceCard key={s.id} s={s} />)}
                </div>
              )}
              <p className="mt-2 text-xs text-gray-500">Searches run: {result.searches.map((q) => `“${q}”`).join(', ') || 'none'}</p>
            </div>

            <Section title="Limitations" kinds={['ai']}>
              <ul className="list-disc space-y-1 pl-5 text-sm text-gray-700">
                {a.limitations.map((l, i) => <li key={i}>{l}</li>)}
                {result.context.data_notes.map((n) => <li key={n}>{n}</li>)}
              </ul>
              {result.warnings.map((w) => <div key={w} className="mt-3"><Note>{w}</Note></div>)}
            </Section>

            <p className="text-xs text-gray-400">
              Generated {new Date(result.generated_at).toLocaleString()} by <code>{result.llm_model}</code>{result.cached ? ' (cached)' : ''}.
              AI text can be wrong: check the sources before acting.
            </p>
          </>
        )}
      </div>
    </>
  )
}
