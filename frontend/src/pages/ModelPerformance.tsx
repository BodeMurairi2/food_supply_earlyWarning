import { Crosshair, Gauge, Scale, Target } from 'lucide-react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import MetricGuide from '../components/MetricGuide'
import { Card, ErrorState, Loading, PageHeader, RiskBadge, StatCard } from '../components/ui'
import { useApi } from '../hooks/useApi'
import { num, pct } from '../lib/format'
import { api } from '../services/api'
import type { EvaluationSet } from '../types/api'

const score = (v: number | null | undefined, digits = 3) => (v === null || v === undefined ? '—' : v.toFixed(digits))
const percent = (v: number | null | undefined) => (v === null || v === undefined ? '—' : `${(v * 100).toFixed(1)}%`)

/** One row per metric, one column per evaluation set. */
function CompareTable({ sets, rows }: { sets: EvaluationSet[]; rows: { label: string; value: (s: EvaluationSet) => string }[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[640px]">
        <thead>
          <tr className="border-b border-gray-100">
            <th className="th">Metric</th>
            {sets.map((s) => <th key={s.key} className="th text-right">{s.label}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.label} className="border-b border-gray-50 last:border-0">
              <td className="td font-medium text-gray-900">{r.label}</td>
              {sets.map((s) => <td key={s.key} className="td text-right tabular-nums">{r.value(s)}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function ClassTable({ set }: { set: EvaluationSet }) {
  const { classes, macro } = set.classification
  return (
    <Card title={set.label}>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[420px]">
          <thead>
            <tr className="border-b border-gray-100">
              <th className="th">Class</th><th className="th text-right">Precision</th><th className="th text-right">Recall</th>
              <th className="th text-right">F1</th><th className="th text-right">ROC-AUC</th>
            </tr>
          </thead>
          <tbody>
            {classes.map((c) => (
              <tr key={c.label} className="border-b border-gray-50">
                <td className="td"><RiskBadge risk={c.label} /></td>
                <td className="td text-right tabular-nums">{percent(c.precision)}</td>
                <td className="td text-right tabular-nums">{percent(c.recall)}</td>
                <td className="td text-right tabular-nums">{percent(c.f1)}</td>
                <td className="td text-right tabular-nums">{percent(c.roc_auc)}</td>
              </tr>
            ))}
            <tr className="font-medium text-gray-900">
              <td className="td">Average</td>
              <td className="td text-right tabular-nums">{percent(macro.precision)}</td>
              <td className="td text-right tabular-nums">{percent(macro.recall)}</td>
              <td className="td text-right tabular-nums">{percent(macro.f1)}</td>
              <td className="td text-right tabular-nums">{percent(macro.roc_auc)}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </Card>
  )
}

export default function ModelPerformance() {
  const { data, loading, error, reload } = useApi(api.performance, [])
  const test = data?.datasets.find((d) => d.key === 'test')

  return (
    <>
      <PageHeader title="Model Performance" subtitle="Trained on 2006–2020, tested on 2021–2024" />

      {error && <ErrorState message={error} onRetry={reload} />}
      {loading && <Loading />}
      {data && test && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard icon={<Target className="h-5 w-5" />} label="Average error (MAE)" value={`${num(test.regression.mae, 2)} pts`} />
            <StatCard icon={<Scale className="h-5 w-5" />} tone="blue" label="RMSE" value={`${num(test.regression.rmse, 2)} pts`} />
            <StatCard icon={<Gauge className="h-5 w-5" />} tone="amber" label="R²" value={percent(test.regression.r2)} />
            <StatCard icon={<Crosshair className="h-5 w-5" />} tone="danger" label="Risk class accuracy" value={pct(test.classification.accuracy * 100, 0)} />
          </div>

          <MetricGuide sets={data.datasets} />

          <Card title="Predicting the percentage" subtitle="Error in percentage points">
            <CompareTable sets={data.datasets} rows={[
              { label: 'MAE', value: (s) => score(s.regression.mae, 2) },
              { label: 'RMSE', value: (s) => score(s.regression.rmse, 2) },
              { label: 'R²', value: (s) => percent(s.regression.r2) },
              { label: 'MAE when copying the last survey', value: (s) => score(s.last_survey.mae, 2) },
            ]} />
          </Card>

          <Card title="Predicting the risk class" subtitle="Average across Low, Medium and High">
            <CompareTable sets={data.datasets} rows={[
              { label: 'Accuracy', value: (s) => percent(s.classification.accuracy) },
              { label: 'Precision', value: (s) => percent(s.classification.macro.precision) },
              { label: 'Recall', value: (s) => percent(s.classification.macro.recall) },
              { label: 'F1', value: (s) => percent(s.classification.macro.f1) },
              { label: 'ROC-AUC', value: (s) => percent(s.classification.macro.roc_auc) },
            ]} />
          </Card>

          <section>
            <h2 className="mb-3 text-sm font-semibold text-gray-900">Risk class details</h2>
            <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
              {data.datasets.map((s) => <ClassTable key={s.key} set={s} />)}
            </div>
          </section>

          <Card title="Error by year" subtitle="Mean absolute error in percentage points">
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={data.by_year} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
                <CartesianGrid stroke="#eef0ef" vertical={false} />
                <XAxis dataKey="year" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip cursor={{ fill: '#f3f4f6' }} formatter={(v: number) => [`${num(v, 2)} pts`, 'MAE']} />
                <Bar isAnimationActive={false} dataKey="mae" name="MAE" fill="#059669" radius={[4, 4, 0, 0]} barSize={56} />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </div>
      )}
    </>
  )
}
