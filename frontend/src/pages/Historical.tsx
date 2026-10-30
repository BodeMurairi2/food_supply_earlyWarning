import { useEffect, useMemo, useState } from 'react'
import {
  Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis,
  ReferenceLine,
} from 'recharts'
import AIAssistant from '../components/AIAssistant'
import ContributionChart from '../components/ContributionChart'
import { LocationFilters, YearSelect, type LocationValue } from '../components/LocationFilters'
import { Card, EmptyState, ErrorState, Loading, PageHeader, Pagination, RiskBadge } from '../components/ui'
import { useApi } from '../hooks/useApi'
import { num, pct, shortProvince, signed } from '../lib/format'
import { api } from '../services/api'
import type { HistoricalRow } from '../types/api'

const PAGE_SIZE = 15
const TEST_YEARS = [2021, 2022, 2023, 2024]

export default function Historical() {
  const [loc, setLoc] = useState<LocationValue>({ province: '', district: '' })
  const [year, setYear] = useState<number | ''>('')
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState<HistoricalRow | null>(null)

  const hist = useApi(() => api.historical({ province: loc.province, district: loc.district, year: year === '' ? null : year }), [loc.province, loc.district, year])
  const imp = useApi(() => api.featureImportance('evaluation'), [])
  const expl = useApi(() => api.explain(selected!.district, selected!.year), [selected?.district, selected?.year], !!selected)

  useEffect(() => setPage(1), [loc.province, loc.district, year])

  const rows = hist.data?.rows ?? []
  const pages = Math.ceil(rows.length / PAGE_SIZE)
  const pageRows = rows.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)
  const scatter = useMemo(() => ({
    real: rows.filter((r) => r.is_real_survey),
    interp: rows.filter((r) => !r.is_real_survey),
  }), [rows])
  const maxAxis = Math.ceil(Math.max(10, ...rows.flatMap((r) => [r.observed, r.predicted])) / 10) * 10

  return (
    <>
      <PageHeader title="Historical Analysis" subtitle="How the model did on 2021–2024, years it never saw in training (trained on 2006–2020)">
        <div className="flex flex-wrap gap-3">
          <LocationFilters value={loc} onChange={setLoc} />
          <YearSelect value={year} onChange={setYear} years={TEST_YEARS} allowAll="All test years" />
        </div>
      </PageHeader>

      <div className="space-y-6">
        {hist.error && <ErrorState message={hist.error} onRetry={hist.reload} />}
        {hist.loading && !hist.data && <Loading />}
        {hist.data && (
          <>
            <div>
              <Card title="Observed vs predicted" subtitle="Each dot is one district-year. Dots on the line are perfect predictions.">
                {rows.length === 0 ? <EmptyState message="No rows for this selection." /> : (
                  <ResponsiveContainer width="100%" height={300}>
                    <ScatterChart margin={{ top: 8, right: 16, bottom: 16, left: 0 }}>
                      <CartesianGrid stroke="#eef0ef" />
                      <XAxis type="number" dataKey="observed" name="Observed" unit="%" domain={[0, maxAxis]} tick={{ fontSize: 11 }}
                        label={{ value: 'Observed', position: 'insideBottom', offset: -8, fontSize: 11 }} />
                      <YAxis type="number" dataKey="predicted" name="Predicted" unit="%" domain={[0, maxAxis]} tick={{ fontSize: 11 }} />
                      <ZAxis range={[40, 40]} />
                      <ReferenceLine segment={[{ x: 0, y: 0 }, { x: maxAxis, y: maxAxis }]} stroke="#9ca3af" strokeDasharray="4 4" />
                      <Tooltip formatter={(v: number) => pct(v)}
                        labelFormatter={() => ''}
                        content={({ payload }) => {
                          const r = payload?.[0]?.payload as HistoricalRow | undefined
                          if (!r) return null
                          return (
                            <div className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs shadow">
                              <p className="font-semibold">{r.district} {r.year}</p>
                              <p>Observed {pct(r.observed)} · Predicted {pct(r.predicted)}</p>
                              <p className="text-gray-500">{r.observation_type}</p>
                            </div>
                          )
                        }} />
                      <Legend wrapperStyle={{ fontSize: 12 }} verticalAlign="top" />
                      <Scatter isAnimationActive={false} name="Real survey" data={scatter.real} fill="#059669" onClick={(d) => setSelected(d as unknown as HistoricalRow)} />
                      <Scatter isAnimationActive={false} name="Interpolated year" data={scatter.interp} fill="#9ca3af" fillOpacity={0.6} onClick={(d) => setSelected(d as unknown as HistoricalRow)} />
                    </ScatterChart>
                  </ResponsiveContainer>
                )}
              </Card>
            </div>

            <Card title="District results" subtitle="Click a row to see why the model predicted that value">
              {rows.length === 0 ? <EmptyState message="No rows for this selection." /> : (
                <>
                  <div className="overflow-x-auto">
                    <table className="w-full min-w-[720px]">
                      <thead>
                        <tr className="border-b border-gray-100">
                          <th className="th">Year</th><th className="th">District</th><th className="th">Province</th>
                          <th className="th text-right">Observed</th><th className="th text-right">Predicted</th>
                          <th className="th text-right">Error</th><th className="th">Observed risk</th><th className="th">Predicted risk</th>
                          <th className="th">Source</th>
                        </tr>
                      </thead>
                      <tbody>
                        {pageRows.map((r) => (
                          <tr key={`${r.district}-${r.year}`} onClick={() => setSelected(r)}
                            className={`cursor-pointer border-b border-gray-50 hover:bg-emerald-50/40 ${selected?.district === r.district && selected?.year === r.year ? 'bg-emerald-50' : ''}`}>
                            <td className="td">{r.year}</td>
                            <td className="td font-medium text-gray-900">{r.district}</td>
                            <td className="td">{shortProvince(r.province)}</td>
                            <td className="td text-right tabular-nums">{pct(r.observed)}</td>
                            <td className="td text-right tabular-nums">{pct(r.predicted)}</td>
                            <td className={`td text-right tabular-nums ${Math.abs(r.error) > 10 ? 'text-red-600' : ''}`}>{signed(r.error)}</td>
                            <td className="td"><RiskBadge risk={r.observed_risk} /></td>
                            <td className="td"><RiskBadge risk={r.predicted_risk} /></td>
                            <td className="td text-xs">{r.is_real_survey ? 'Survey' : <span className="text-gray-400">{r.observation_type}</span>}</td>
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
          <Card title="What drives the model" subtitle="Mean absolute SHAP value on the test years (evaluation model)">
            {imp.error && <ErrorState message={imp.error} onRetry={imp.reload} />}
            {imp.loading && <Loading />}
            {imp.data && (
              <ResponsiveContainer width="100%" height={360}>
                <BarChart data={imp.data.features.slice(0, 12)} layout="vertical" margin={{ left: 8, right: 16 }}>
                  <CartesianGrid horizontal={false} stroke="#eef0ef" />
                  <XAxis type="number" tick={{ fontSize: 11 }} />
                  <YAxis type="category" dataKey="label" width={210} tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(v: number) => `${num(v, 2)} pts`} />
                  <Bar isAnimationActive={false} dataKey="mean_abs_shap" name="Mean |SHAP|" fill="#0f3b3a" radius={3} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </Card>

          <Card title={selected ? `Why ${selected.district} ${selected.year}?` : 'District explanation'}
            subtitle={expl.data && !expl.loading ? `Predicted ${pct(expl.data.prediction)} = average ${pct(expl.data.base_value)} + contributions below. Observed ${pct(expl.data.observed)}.` : undefined}>
            {!selected && <EmptyState message="Pick a row in the table or a dot in the chart." />}
            {selected && expl.loading && <Loading />}
            {selected && expl.error && <ErrorState message={expl.error} onRetry={expl.reload} />}
            {selected && expl.data && !expl.loading && <ContributionChart contributions={expl.data.contributions} />}
          </Card>
        </div>


        {selected && (
          <AIAssistant key={`${selected.district}-${selected.year}`} title={`AI assistant: ${selected.district}, ${selected.year}`}
            request={{ kind: 'historical', district: selected.district, year: selected.year }} />
        )}
      </div>
    </>
  )
}
