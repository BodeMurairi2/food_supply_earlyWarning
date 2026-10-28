import { ArrowDown, ArrowUp, ArrowUpDown, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useEffect, useMemo, useState } from 'react'
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import ContributionChart from '../components/ContributionChart'
import { LocationFilters, type LocationValue } from '../components/LocationFilters'
import { Card, EmptyState, ErrorState, Loading, Note, PageHeader, Pagination, RiskBadge } from '../components/ui'
import { useApi } from '../hooks/useApi'
import { pct, shortProvince, signed } from '../lib/format'
import { api } from '../services/api'
import type { Driver, ForecastRow, SeriesPoint } from '../types/api'

const PAGE_SIZE = 10

// Start the dashed forecast line at the last observed year so the two lines connect.
const joinForecast = (series: SeriesPoint[]) => {
  const first = series.findIndex((p) => p.forecast !== null)
  return series.map((p, i) => (i === first - 1 && p.forecast === null ? { ...p, forecast: p.observed } : p))
}
type SortKey = 'district' | 'observed_2024' | 'predicted_2025' | 'predicted_2026'

function Drivers({ drivers }: { drivers: Driver[] }) {
  return (
    <div className="flex flex-wrap gap-1">
      {drivers.map((d) => (
        <span key={d.label} className={`rounded px-1.5 py-0.5 text-[11px] ${d.contribution > 0 ? 'bg-red-50 text-red-700' : 'bg-green-50 text-green-700'}`}>
          {d.label} {signed(d.contribution)}
        </span>
      ))}
    </div>
  )
}

export default function Forecasts() {
  const [loc, setLoc] = useState<LocationValue>({ province: '', district: '' })
  const [sort, setSort] = useState<{ key: SortKey; desc: boolean }>({ key: 'predicted_2025', desc: true })
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState<string | null>(null)
  const [explainYear, setExplainYear] = useState(2025)

  const fc = useApi(() => api.forecasts({ province: loc.province, district: loc.district }), [loc.province, loc.district])
  const series = useApi(() => api.districtSeries(selected!), [selected], !!selected)
  const expl = useApi(() => api.explain(selected!, explainYear), [selected, explainYear], !!selected)

  useEffect(() => setPage(1), [loc.province, loc.district, sort])

  const rows = useMemo(() => {
    const r = [...(fc.data?.rows ?? [])]
    r.sort((a: ForecastRow, b: ForecastRow) => {
      const va = a[sort.key] ?? -Infinity
      const vb = b[sort.key] ?? -Infinity
      const c = typeof va === 'string' ? va.localeCompare(vb as string) : (va as number) - (vb as number)
      return sort.desc ? -c : c
    })
    return r
  }, [fc.data, sort])
  const pages = Math.ceil(rows.length / PAGE_SIZE)
  const pageRows = rows.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  const header = (key: SortKey, label: string, right = false) => (
    <th className={`th ${right ? 'text-right' : ''}`}>
      <button className="inline-flex items-center gap-1 uppercase" onClick={() => setSort({ key, desc: sort.key === key ? !sort.desc : true })}>
        {label}
        {sort.key !== key ? <ArrowUpDown className="h-3 w-3 opacity-40" /> : sort.desc ? <ArrowDown className="h-3 w-3" /> : <ArrowUp className="h-3 w-3" />}
      </button>
    </th>
  )

  return (
    <>
      <PageHeader title="Forecasts (2025–2026)" subtitle="Random forest retrained on 2006–2024. No survey exists yet for these years.">
        <div className="flex flex-wrap gap-3"><LocationFilters value={loc} onChange={setLoc} /></div>
      </PageHeader>

      <div className="space-y-6">
        {fc.error && <ErrorState message={fc.error} onRetry={fc.reload} />}
        {fc.loading && !fc.data && <Loading />}
        {fc.data && (
          <>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              {Object.entries(fc.data.status).map(([y, s]) => <Note key={y}><b>{y}:</b> {s}</Note>)}
            </div>

            <Card title="District forecasts" subtitle="Click a row to see the district's history and the drivers of its forecast">
              {rows.length === 0 ? <EmptyState message="No districts for this selection." /> : (
                <>
                  <div className="overflow-x-auto">
                    <table className="w-full min-w-[900px]">
                      <thead>
                        <tr className="border-b border-gray-100">
                          {header('district', 'District')}<th className="th">Province</th>
                          {header('observed_2024', 'Survey 2024', true)}
                          {header('predicted_2025', '2025', true)}<th className="th">Risk</th>
                          {header('predicted_2026', '2026', true)}<th className="th">Risk</th>
                          <th className="th">Top drivers 2025</th>
                        </tr>
                      </thead>
                      <tbody>
                        {pageRows.map((r) => (
                          <tr key={r.district} onClick={() => setSelected(r.district)}
                            className={`cursor-pointer border-b border-gray-50 hover:bg-emerald-50/40 ${selected === r.district ? 'bg-emerald-50' : ''}`}>
                            <td className="td font-medium text-gray-900">{r.district}</td>
                            <td className="td">{shortProvince(r.province)}</td>
                            <td className="td text-right tabular-nums">{pct(r.observed_2024)}</td>
                            <td className="td text-right font-medium tabular-nums">{pct(r.predicted_2025)}</td>
                            <td className="td"><RiskBadge risk={r.risk_2025} /></td>
                            <td className="td text-right font-medium tabular-nums">{pct(r.predicted_2026)}</td>
                            <td className="td"><RiskBadge risk={r.risk_2026} /></td>
                            <td className="td"><Drivers drivers={r.drivers_2025} /></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <Pagination page={page} pages={pages} onChange={setPage} total={rows.length} pageSize={PAGE_SIZE} />
                </>
              )}
            </Card>
          </>
        )}

        <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
          <Card title={selected ? `${selected}: 2006–2026` : 'District history'}
            subtitle={selected ? 'Observed/estimated values, the 2021–2024 test predictions and the 2025–2026 forecast' : undefined}>
            {!selected && <EmptyState message="Pick a district in the table." />}
            {selected && series.loading && <Loading />}
            {selected && series.error && <ErrorState message={series.error} onRetry={series.reload} />}
            {selected && series.data && (
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={joinForecast(series.data.series)} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                  <CartesianGrid stroke="#eef0ef" vertical={false} />
                  <XAxis dataKey="year" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} unit="%" />
                  <Tooltip formatter={(v: number) => pct(v)} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Line isAnimationActive={false} dataKey="observed" name="Observed / estimated" stroke="#059669" strokeWidth={2} dot={{ r: 2 }} />
                  <Line isAnimationActive={false} dataKey="test_prediction" name="Test prediction" stroke="#2563eb" strokeWidth={2} dot={{ r: 3 }} />
                  <Line isAnimationActive={false} dataKey="forecast" name="Forecast" stroke="#d97706" strokeWidth={2} strokeDasharray="5 4" dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            )}
          </Card>

          <Card title={selected ? `Why this forecast for ${selected}?` : 'Forecast drivers'}
            subtitle={expl.data && !expl.loading ? `Predicted ${pct(expl.data.prediction)} = average ${pct(expl.data.base_value)} + contributions below` : undefined}
            actions={selected && (
              <div className="flex items-center gap-2">
              <Link to={`/ai-analyst?district=${encodeURIComponent(selected)}&year=${explainYear}`}
                className="inline-flex items-center gap-1 rounded-lg border border-violet-200 bg-violet-50 px-2.5 py-1 text-xs font-medium text-violet-700 hover:bg-violet-100">
                <Sparkles className="h-3.5 w-3.5" /> AI analysis
              </Link>
              <div className="flex rounded-lg border border-gray-200 p-0.5 text-xs">
                {[2025, 2026].map((y) => (
                  <button key={y} onClick={() => setExplainYear(y)}
                    className={`rounded-md px-3 py-1 ${explainYear === y ? 'bg-brand text-white' : 'text-gray-600'}`}>{y}</button>
                ))}
              </div>
              </div>
            )}>
            {!selected && <EmptyState message="Pick a district in the table." />}
            {selected && expl.loading && <Loading />}
            {selected && expl.error && <ErrorState message={expl.error} onRetry={expl.reload} />}
            {selected && expl.data && !expl.loading && <ContributionChart contributions={expl.data.contributions} />}
          </Card>
        </div>

        {fc.data && <Note>{fc.data.note}</Note>}
      </div>
    </>
  )
}
