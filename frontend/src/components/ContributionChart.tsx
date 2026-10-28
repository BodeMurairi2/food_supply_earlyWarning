import { Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { num, signed } from '../lib/format'
import type { Contribution } from '../types/api'

/** Horizontal bars of SHAP contributions: red pushes food insecurity up, green pulls it down. */
export default function ContributionChart({ contributions, top = 10 }: { contributions: Contribution[]; top?: number }) {
  const data = contributions.slice(0, top).map((c) => ({
    name: c.label,
    contribution: c.contribution,
    value: typeof c.value === 'number' ? `${num(c.value)} ${c.unit}`.trim() : c.value ?? 'empty (imputed)',
  }))
  return (
    <ResponsiveContainer width="100%" height={Math.max(220, data.length * 30)}>
      <BarChart data={data} layout="vertical" margin={{ left: 8, right: 24, top: 4, bottom: 4 }}>
        <CartesianGrid horizontal={false} stroke="#eef0ef" />
        <XAxis type="number" tick={{ fontSize: 11 }} tickFormatter={(v) => signed(v, 1)}
          label={{ value: 'Contribution (percentage points)', position: 'insideBottom', offset: -2, fontSize: 11 }} height={36} />
        <YAxis type="category" dataKey="name" width={210} tick={{ fontSize: 11 }} />
        <ReferenceLine x={0} stroke="#9ca3af" />
        <Tooltip formatter={(v: number) => [`${signed(v, 2)} pts`, 'Contribution']}
          labelFormatter={(label, payload) => `${label}: ${payload?.[0]?.payload?.value ?? ''}`} />
        <Bar isAnimationActive={false} dataKey="contribution" radius={3}>
          {data.map((d) => <Cell key={d.name} fill={d.contribution > 0 ? '#dc2626' : '#16a34a'} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
