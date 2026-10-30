import { Bot, ChevronDown, Loader2, Sparkles } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { api } from '../services/api'
import type { AssistantOutlook, AssistantRequest, AssistantResult } from '../types/api'
import SourceCard from './SourceCard'
import { ErrorState } from './ui'

const INITIAL_SOURCES = 2
const SOURCE_STEP = 2
const MAX_SOURCES = 6

function Heading({ children, tag }: { children: React.ReactNode; tag?: string }) {
  return (
    <h3 className="mb-2 flex flex-wrap items-center gap-2 text-sm font-semibold text-gray-900">
      {children}
      {tag && <span className="rounded-full border border-gray-200 bg-gray-50 px-2 py-0.5 text-[11px] font-medium text-gray-600">{tag}</span>}
    </h3>
  )
}

function Outlook({ title, outlook }: { title: string; outlook: AssistantOutlook }) {
  return (
    <section>
      <Heading tag="AI judgement, not a model forecast">{title}</Heading>
      <div className="space-y-3 text-sm leading-relaxed text-gray-700">
        {outlook.assessment.map((p, i) => <p key={i}>{p}</p>)}
      </div>
      {outlook.watch_for.length > 0 && (
        <div className="mt-3">
          <p className="mb-1 text-xs font-semibold text-gray-700">What to watch</p>
          <ul className="list-disc space-y-1 pl-5 text-sm text-gray-700">{outlook.watch_for.map((w, i) => <li key={i}>{w}</li>)}</ul>
        </div>
      )}
      {outlook.scenarios.length > 0 && (
        <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
          {outlook.scenarios.map((s, i) => (
            <div key={i} className="rounded-lg border border-amber-100 bg-amber-50/50 p-3 text-sm">
              <p className="font-medium text-gray-900">{s.scenario}</p>
              <p className="mt-1 text-gray-700">{s.implication}</p>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

/** A button that asks the AI to explain the result on screen, then shows its answer and sources. */
export default function AIAssistant({ title, request, disabledReason }: { title: string; request: AssistantRequest; disabledReason?: string }) {
  const [result, setResult] = useState<AssistantResult | null>(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [elapsed, setElapsed] = useState(0)
  const [visible, setVisible] = useState(INITIAL_SOURCES)
  const timer = useRef<number | undefined>(undefined)

  useEffect(() => () => window.clearInterval(timer.current), [])

  const run = async () => {
    setRunning(true); setError(null); setResult(null); setElapsed(0); setVisible(INITIAL_SOURCES)
    const start = Date.now()
    timer.current = window.setInterval(() => setElapsed(Math.round((Date.now() - start) / 1000)), 1000)
    try {
      setResult(await api.aiAssistant(request))
    } catch (e) {
      setError((e as Error).message)
    } finally {
      window.clearInterval(timer.current)
      setRunning(false)
    }
  }

  const b = result?.briefing
  const sources = result?.sources.slice(0, MAX_SOURCES) ?? []

  // A citation may point to a source that is still hidden: reveal them before jumping to it.
  const openSource = (id: string) => {
    setVisible(MAX_SOURCES)
    window.setTimeout(() => document.getElementById(`source-${id}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' }), 0)
  }
  const Cites = ({ ids }: { ids: string[] }) => (
    <>
      {ids.map((id) => (
        <button key={id} onClick={() => openSource(id)} className="ml-1 rounded bg-blue-50 px-1.5 py-0.5 text-[11px] font-medium text-blue-700 hover:underline">{id}</button>
      ))}
    </>
  )

  return (
    <section className="card overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-4 bg-sidebar px-5 py-4 text-white">
        <div className="flex min-w-0 items-start gap-3">
          <div className="rounded-lg bg-white/10 p-2"><Bot className="h-5 w-5 text-emerald-300" /></div>
          <div className="min-w-0">
            <h2 className="text-sm font-semibold">{title}</h2>
            <p className="mt-0.5 text-xs text-emerald-100/80">What this result means, and what it implies for the next 3–6 months and the next year</p>
          </div>
        </div>
        <button onClick={run} disabled={running || !!disabledReason}
          className="inline-flex items-center gap-2 rounded-lg bg-white px-4 py-2 text-sm font-medium text-sidebar hover:bg-emerald-50 disabled:cursor-not-allowed disabled:opacity-60">
          {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
          {running ? `Researching… ${elapsed}s` : result ? 'Ask again' : 'Ask the AI assistant'}
        </button>
      </div>

      {disabledReason && <p className="px-5 py-3 text-sm text-gray-600">{disabledReason}</p>}
      {running && <p className="px-5 py-4 text-sm text-gray-600">The assistant is reading the result and searching the web. This usually takes up to two minutes.</p>}
      {error && <div className="p-5"><ErrorState message={error} onRetry={run} /></div>}

      {result && b && (
        <div className="space-y-6 p-5">
          <p className="text-base font-medium leading-relaxed text-gray-900">{b.headline}</p>

          <section>
            <Heading>What this means</Heading>
            <div className="space-y-3 text-sm leading-relaxed text-gray-700">{b.what_it_means.map((p, i) => <p key={i}>{p}</p>)}</div>
          </section>

          {b.drivers.length > 0 && (
            <section>
              <Heading>What is behind it</Heading>
              <ul className="divide-y divide-gray-100">
                {b.drivers.map((d, i) => (
                  <li key={i} className="py-2.5 text-sm">
                    <span className="font-medium text-gray-900">{d.factor}</span>
                    {d.direction !== 'neutral' && <span className={`ml-2 text-xs ${d.direction === 'raises' ? 'text-red-600' : 'text-green-700'}`}>{d.direction}</span>}
                    <p className="mt-0.5 text-gray-700">{d.explanation}</p>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <section>
            <Heading tag="Web evidence">What outside sources say</Heading>
            {b.evidence.length === 0 ? <p className="text-sm text-gray-600">We found no reliable outside evidence for this area.</p> : (
              <ul className="space-y-3">
                {b.evidence.map((e, i) => (
                  <li key={i} className="rounded-lg border border-gray-100 p-3 text-sm">
                    <p className="text-gray-800">{e.finding}<Cites ids={e.sources} /></p>
                    <p className="mt-1 text-xs text-gray-500">{e.relevance} · Scope: {e.scope} · Credibility: {e.credibility}</p>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <Outlook title="The next 3–6 months" outlook={b.outlook_3_6_months} />
          <Outlook title="The next year" outlook={b.outlook_1_year} />

          {b.actions.length > 0 && (
            <section>
              <Heading>Recommended actions</Heading>
              <ol className="list-decimal space-y-3 pl-5 text-sm">
                {b.actions.map((a, i) => (
                  <li key={i}>
                    <p className="font-medium text-gray-900">{a.action}<Cites ids={a.sources} /></p>
                    {(a.who || a.when) && <p className="text-xs text-gray-500">{[a.who, a.when].filter(Boolean).join(' · ')}</p>}
                    <p className="mt-0.5 text-gray-700">{a.rationale}</p>
                  </li>
                ))}
              </ol>
            </section>
          )}

          {b.limitations.length > 0 && (
            <section>
              <Heading>Limits of this explanation</Heading>
              <ul className="list-disc space-y-1 pl-5 text-sm text-gray-700">{b.limitations.map((l, i) => <li key={i}>{l}</li>)}</ul>
            </section>
          )}

          <section>
            <Heading>Sources</Heading>
            {sources.length === 0 ? <p className="text-sm text-gray-600">No web sources were retrieved.</p> : (
              <>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  {sources.slice(0, visible).map((s) => <SourceCard key={s.id} s={s} />)}
                </div>
                <div className="mt-3 flex items-center gap-3">
                  {visible < sources.length && (
                    <button className="btn-secondary" onClick={() => setVisible(Math.min(visible + SOURCE_STEP, sources.length))}>
                      <ChevronDown className="h-4 w-4" /> Load more sources
                    </button>
                  )}
                  <span className="text-xs text-gray-500">Showing {Math.min(visible, sources.length)} of {sources.length}</span>
                </div>
              </>
            )}
          </section>

          {result.warnings.map((w) => <p key={w} className="text-xs text-gray-500">{w}</p>)}
          <p className="text-xs text-gray-400">
            Generated {new Date(result.generated_at).toLocaleString()} by {result.llm_model}. AI text can be wrong: check the sources before acting.
          </p>
        </div>
      )}
    </section>
  )
}
