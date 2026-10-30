import { AlertTriangle, Search } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import AIAssistant from '../components/AIAssistant'
import { LocationFilters, YearSelect, type LocationValue } from '../components/LocationFilters'
import { Card, ErrorState, Loading, PageHeader, RiskBadge } from '../components/ui'
import { useAppData } from '../hooks/AppData'
import { useApi } from '../hooks/useApi'
import { pct, signed } from '../lib/format'
import { api } from '../services/api'

const YEARS = [2026, 2025, 2024, 2023, 2022, 2021]
const FIRST_FORECAST_YEAR = 2025
const SUGGESTIONS = [
  'What is the rainfall outlook for the next Season A?',
  'Are bean and maize prices rising in Rwanda?',
  'Recent crop production or harvest problems in this province',
  'Floods, landslides or drought affecting this area',
]

export default function AIAnalyst() {
  const { provinceOf } = useAppData()
  const [params] = useSearchParams()
  const initial = params.get('district') || 'Rutsiro'
  const [loc, setLoc] = useState<LocationValue>({ province: '', district: initial })
  const [year, setYear] = useState(Number(params.get('year')) || 2026)
  const [question, setQuestion] = useState('')

  useEffect(() => {
    const p = provinceOf(loc.district)
    if (p && !loc.province) setLoc((l) => ({ ...l, province: p }))
  }, [provinceOf, loc.district, loc.province])

  const status = useApi(api.aiStatus, [])
  // The model numbers are cheap and shown at once; the web research runs only when the user clicks.
  const ctx = useApi(() => api.aiContext(loc.district, year), [loc.district, year], !!loc.district)
  const ready = status.data?.llm && status.data?.search
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
                onChange={(e) => setQuestion(e.target.value)} />
            </div>
          </label>
          <div className="mt-3 flex flex-wrap gap-2">
            {SUGGESTIONS.map((s) => (
              <button key={s} onClick={() => setQuestion(s)}
                className="rounded-full border border-gray-200 px-3 py-1 text-xs text-gray-600 hover:border-brand hover:text-brand">{s}</button>
            ))}
          </div>
        </Card>

        <Card title={`Model result: ${loc.district || '…'}, ${year}`}>
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
        </Card>

        {loc.district && (
          <AIAssistant key={`${loc.district}-${year}`} title={`AI Analyst: ${loc.district}, ${year}`}
            disabledReason={status.data && !ready ? 'The AI Analyst needs its keys before it can run.' : undefined}
            request={{ kind: year >= FIRST_FORECAST_YEAR ? 'forecast' : 'historical', district: loc.district, year, question: question.trim() || undefined }} />
        )}
      </div>
    </>
  )
}
