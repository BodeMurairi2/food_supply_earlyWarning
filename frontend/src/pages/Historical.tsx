import { Gauge, Scale, Target, TrendingDown } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import {
  Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis,
  ReferenceLine,
} from 'recharts'
import ContributionChart from '../components/ContributionChart'
import { LocationFilters, YearSelect, type LocationValue } from '../components/LocationFilters'
import { Card, EmptyState, ErrorState, Loading, Note, PageHeader, Pagination, RiskBadge, StatCard } from '../components/ui'
import { useApi } from '../hooks/useApi'
import { num, pct, shortProvince, signed } from '../lib/format'
import { api } from '../services/api'
import type { ClassificationScores, HistoricalRow } from '../types/api'

const PAGE_SIZE = 15
const TEST_YEARS = [2021, 2022, 2023, 2024]

/** How well the predicted percentages land in the right risk class, on the real surveys only. */
function RiskClassCard({ scores }: { scores: ClassificationScores }) {
  const high = scores.classes.find((c) => c.label === 'High')
  return (
    <Card title="Risk class performance on real surveys"
      subtitle={`Predictions turned into Low, Medium and High, compared with the 2021 and 2024 surveys (${scores.n} district-years). Accuracy ${num(scores.accuracy, 3)}.`}>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px]">
          <thead>
            <tr className="border-b border-gray-100">
              <th className="th">Class</th><th className="th text-right">Precision</th><th className="th text-right">Recall</th>
              <th className="th text-right">F1</th><th className="th text-right">ROC-AUC</th>
              <th className="th text-right">Correct / observed</th><th className="th text-right">Predicted</th>
            </tr>
          </thead>
          <tbody>
            {scores.classes.map((c) => (
              <tr key={c.label} className="border-b border-gray-50">
                <td className="td"><RiskBadge risk={c.label} /></td>
                <td className="td text-right tabular-nums">{c.precision.toFixed(3)}</td>
                <td className="td text-right tabular-nums">{c.recall.toFixed(3)}</td>
                <td className="td text-right tabular-nums">{c.f1.toFixed(3)}</td>
                <td className="td text-right tabular-nums">{c.roc_auc?.toFixed(3) ?? '—'}</td>
                <td className="td text-right tabular-nums">{c.correct} / {c.observed}</td>
                <td className="td text-right tabular-nums">{c.predicted}</td>
              </tr>
            ))}
            <tr className="font-medium">
              <td className="td text-gray-900">Average of classes</td>
              <td className="td text-right tabular-nums text-gray-900">{scores.macro.precision.toFixed(3)}</td>
              <td className="td text-right tabular-nums text-gray-900">{scores.macro.recall.toFixed(3)}</td>
              <td className="td text-right tabular-nums text-gray-900">{scores.macro.f1.toFixed(3)}</td>
              <td className="td text-right tabular-nums text-gray-900">{scores.macro.roc_auc?.toFixed(3) ?? '—'}</td>
              <td className="td" /><td className="td" />
            </tr>
          </tbody>
        </table>
      </div>
      <div className="mt-3 space-y-2">
        {high && (
          <Note>
            High districts are often missed: the model caught {high.correct} of {high.observed} on these surveys and labelled most of the
            others Medium. Read the percentage and the ranking as well as the label, and treat districts near 30% as a warning too.
            With only {high.observed} High districts, these figures can move a lot.
          </Note>
        )}
        <Note>
          Low, Medium and High are illustrative thresholds (15% and 30%), not official NISR categories. ROC-AUC measures how well districts
          are ranked for each class, using the share of the forest's trees that predict that class.
        </Note>
      </div>
    </Card>
  )
}

export default function Historical() {
  const [loc, setLoc] = useState<LocationValue>({ province: '', district: '' })
  const [year, setYear] = useState<number | ''>('')
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState<HistoricalRow | null>(null)

  const hist = useApi(() => api.historical({ province: loc.province, district: loc.district, year: year === '' ? null : year }), [loc.province, loc.district, year])
  const perf = useApi(api.performance, [])
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

  const p = perf.data
  return (
    <>
      <PageHeader title="Historical Analysis" subtitle="How the model did on 2021–2024, years it never saw in training (trained on 2006–2020)">
        <div className="flex flex-wrap gap-3">
          <LocationFilters value={loc} onChange={setLoc} />
          <YearSelect value={year} onChange={setYear} years={TEST_YEARS} allowAll="All test years" />
        </div>
      </PageHeader>

      <div className="space-y-6">
        {perf.error && <ErrorState message={perf.error} onRetry={perf.reload} />}
        {p && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard icon={<Target className="h-5 w-5" />} label="MAE on real surveys (2021, 2024)"
              value={`${num(p.test_real_surveys.mae, 2)} pts`} hint={`Persistence baseline ${num(p.persistence_real_surveys.mae, 2)} pts`} />
            <StatCard icon={<Scale className="h-5 w-5" />} tone="blue" label="RMSE on real surveys"
              value={`${num(p.test_real_surveys.rmse, 2)} pts`} hint={`Persistence ${num(p.persistence_real_surveys.rmse, 2)} pts`} />
            <StatCard icon={<Gauge className="h-5 w-5" />} tone="amber" label="R² on real surveys"
              value={num(p.test_real_surveys.r2, 3)} hint={`Persistence ${num(p.persistence_real_surveys.r2, 3)} · n = ${p.test_real_surveys.n}`} />
            <StatCard icon={<TrendingDown className="h-5 w-5" />} tone="danger" label="Risk class agreement"
              value={pct(p.risk_class_agreement_real_surveys * 100, 0)} hint="Low / Medium / High, real surveys" />
          </div>
        )}

        {p && <RiskClassCard scores={p.classification_real_surveys} />}

        {hist.error && <ErrorState message={hist.error} onRetry={hist.reload} />}
        {hist.loading && !hist.data && <Loading />}
        {hist.data && (
          <>
            <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
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

              <Card title="Error by year" subtitle="Mean absolute error in percentage points">
                {p && (
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={p.by_year} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
                      <CartesianGrid stroke="#eef0ef" vertical={false} />
                      <XAxis dataKey="year" tick={{ fontSize: 11 }} />
                      <YAxis tick={{ fontSize: 11 }} />
                      <Tooltip formatter={(v: number) => `${num(v, 2)} pts`}
                        labelFormatter={(y) => `${y} (${p.by_year.find((b) => b.year === y)?.observation_type ?? ''})`} />
                      <Bar isAnimationActive={false} dataKey="mae" name="MAE" fill="#059669" radius={[4, 4, 0, 0]} />
                    </BarChart>
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
                  {hist.data.metrics.real_surveys.n > 0 && (
                    <p className="mt-3 text-xs text-gray-500">
                      This selection: MAE {num(hist.data.metrics.real_surveys.mae, 2)} pts on {hist.data.metrics.real_surveys.n} real survey rows
                      (persistence {num(hist.data.metrics.persistence_real_surveys.mae, 2)} pts); {num(hist.data.metrics.all_rows.mae, 2)} pts on all {hist.data.metrics.all_rows.n} rows.
                    </p>
                  )}
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

        {p && <Note>{p.caveats.join(' ')}</Note>}
      </div>
    </>
  )
}
