import { Table2 } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, ReferenceArea, ReferenceLine, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from 'recharts'
import { LocationFilters, YearSelect, type LocationValue } from '../components/LocationFilters'
import { Card, EmptyState, ErrorState, Loading, Note, PageHeader } from '../components/ui'
import { useApi } from '../hooks/useApi'
import { NATIONAL_COLOR, SERIES_COLORS, num, shortProvince, signed } from '../lib/format'
import { api } from '../services/api'
import type { VizTrends, VizVariable } from '../types/api'

type Level = 'province' | 'district'
type View = 'values' | 'change'
const NATIONAL = 'Rwanda (all districts)'
const INCREASE = '#2a78d6'
const DECREASE = '#eb6834'

const digitsFor = (unit: string) => (unit === 't' || unit === 'mm' || unit === 'RWF/kg' || unit === 'kg/ha' ? 0 : unit === '°C' ? 2 : 1)
const compact = (v: number) => (Math.abs(v) >= 1e6 ? `${num(v / 1e6, 1)}M` : Math.abs(v) >= 1e4 ? `${num(v / 1e3, 0)}k` : num(v, 1))

function Segmented<T extends string>({ value, options, onChange }: { value: T; options: { value: T; label: string }[]; onChange: (v: T) => void }) {
  return (
    <div className="inline-flex rounded-lg border border-gray-200 bg-white p-0.5 text-xs">
      {options.map((o) => (
        <button key={o.value} onClick={() => onChange(o.value)}
          className={`rounded-md px-3 py-1.5 ${value === o.value ? 'bg-brand text-white' : 'text-gray-600 hover:bg-gray-50'}`}>
          {o.label}
        </button>
      ))}
    </div>
  )
}

/** Turn the long series into one row per year, optionally as change from each series' first value in range. */
function pivot(t: VizTrends, names: string[], view: View, withNational: boolean) {
  const all = [...t.series.filter((s) => names.includes(s.name)), ...(withNational ? [{ name: NATIONAL, points: t.national }] : [])]
  const pct = t.variable.change === 'pct'
  const bases = Object.fromEntries(all.map((s) => [s.name, s.points.find((p) => p.value !== null && !t.partial_years.includes(p.year))?.value ?? null]))
  return {
    keys: all.map((s) => s.name),
    rows: t.years.map((year) => {
      const row: Record<string, number | null> = { year }
      all.forEach((s) => {
        const v = s.points.find((p) => p.year === year)?.value ?? null
        const b = bases[s.name]
        row[s.name] = view === 'values' || v === null ? v : b === null ? null : pct ? (b ? ((v - b) / b) * 100 : null) : v - b
      })
      return row
    }),
  }
}

export default function Visualizations() {
  const vars = useApi(api.vizVariables, [])
  const [level, setLevel] = useState<Level>('province')
  const [loc, setLoc] = useState<LocationValue>({ province: '', district: '' })
  const [startYear, setStartYear] = useState(2021)
  const [endYear, setEndYear] = useState(2026)
  const [topic, setTopic] = useState('Rainfall')
  // Remember the chosen variable per topic, so switching topics and back keeps the choice.
  const [choice, setChoice] = useState<Record<string, string>>({})
  const [view, setView] = useState<View>('values')
  const [rank, setRank] = useState<'mean' | 'change'>('mean')
  const [showTable, setShowTable] = useState(false)

  const byTopic = useMemo(() => {
    const m: Record<string, VizVariable[]> = {}
    vars.data?.variables.forEach((v) => (m[v.topic] ??= []).push(v))
    return m
  }, [vars.data])
  const variable = byTopic[topic]?.find((v) => v.key === choice[topic]) ?? byTopic[topic]?.[0]

  useEffect(() => {
    if (vars.data) { setStartYear(vars.data.default_years[0]); setEndYear(vars.data.default_years[1]) }
  }, [vars.data])

  const q = { province: loc.province, district: level === 'district' ? loc.district : '', start_year: startYear, end_year: endYear }
  const trends = useApi(() => api.vizTrends({ ...q, variable: variable!.key, level }),
    [variable?.key, level, q.province, q.district, startYear, endYear], !!variable)
  const profile = useApi(() => api.vizProfile({ province: loc.province, district: loc.district, start_year: startYear, end_year: endYear }),
    [loc.province, loc.district, startYear, endYear])

  const [y0, y1] = vars.data?.years ?? [2006, 2026]
  const years = Array.from({ length: y1 - y0 + 1 }, (_, i) => y0 + i)
  const t = trends.data
  const unit = t?.variable.unit ?? ''
  const digits = digitsFor(unit)
  const canPct = t?.variable.change === 'pct'
  const changeUnit = canPct ? '%' : ` ${unit}`
  // Small differences (e.g. +0.3 °C) need a decimal on the axis; percentages do not.
  const tickDigits = canPct ? 0 : 1

  // Which lines to draw: never more than 8 categorical series.
  const tooManyDistricts = level === 'district' && !loc.province
  const lineNames = !t ? [] : tooManyDistricts ? (loc.district ? [loc.district] : []) : t.series.map((s) => s.name)
  const colorOf = (name: string) => SERIES_COLORS[(t?.series.findIndex((s) => s.name === name) ?? 0) % SERIES_COLORS.length]
  // A national total is not comparable with one area's total, so the Rwanda line is shown for averaged variables only.
  const withNational = t?.variable.aggregation === 'mean'
  const chart = t ? pivot(t, lineNames, view, withNational) : null
  const hasData = !!t && t.national.some((p) => p.value !== null)
  const highlight = t?.highlight

  const comparison = useMemo(() => {
    if (!t) return []
    return [...t.comparison.rows].filter((r) => r[rank] !== null).sort((a, b) => (b[rank] as number) - (a[rank] as number))
  }, [t, rank])

  return (
    <>
      <PageHeader title="Visualizations" subtitle="Rainfall, temperature, harvests and prices by province and district, from the dataset" />

      {vars.error && <ErrorState message={vars.error} onRetry={vars.reload} />}
      {vars.loading && <Loading />}
      {vars.data && variable && (
        <div className="space-y-6">
          <div className="card flex flex-wrap items-end gap-3 p-4">
            <div>
              <span className="mb-1 block text-xs font-medium text-gray-500">Geographic level</span>
              <Segmented value={level} onChange={setLevel}
                options={[{ value: 'province', label: 'Province' }, { value: 'district', label: 'District' }]} />
            </div>
            <LocationFilters value={loc} onChange={setLoc} />
            <YearSelect label="Start year" value={startYear} years={years}
              onChange={(y) => { const v = Number(y); setStartYear(v); if (v > endYear) setEndYear(v) }} />
            <YearSelect label="End year" value={endYear} years={years}
              onChange={(y) => { const v = Number(y); setEndYear(v); if (v < startYear) setStartYear(v) }} />
          </div>

          <div className="flex flex-wrap items-end gap-3">
            <Segmented value={topic} onChange={setTopic} options={vars.data.topics.map((x) => ({ value: x, label: x }))} />
            <label className="block min-w-64">
              <span className="mb-1 block text-xs font-medium text-gray-500">Variable</span>
              <select className="select" value={variable.key} onChange={(e) => setChoice({ ...choice, [topic]: e.target.value })}>
                {byTopic[topic].map((v) => <option key={v.key} value={v.key}>{v.label} ({v.unit})</option>)}
              </select>
            </label>
            <span className="pb-2 text-xs text-gray-500">
              Available {variable.years[0]}–{variable.years[variable.years.length - 1]}
            </span>
          </div>

          {trends.error && <ErrorState message={trends.error} onRetry={trends.reload} />}
          {trends.loading && !t && <Loading />}
          {t && (
            <div className={`space-y-6 ${trends.loading ? 'opacity-60' : ''}`}>
              <Card title={`${t.variable.label} by ${level}, ${startYear}–${endYear}`}
                subtitle={view === 'values' ? `Unit: ${unit}.${withNational ? ' The dashed grey line is the Rwanda-wide average.' : ''}`
                  : `Change from each line's first complete year in the range (${canPct ? '%' : unit}).`}
                actions={
                  <div className="flex flex-wrap gap-2">
                    <Segmented value={view} onChange={setView}
                      options={[{ value: 'values', label: 'Values' }, { value: 'change', label: canPct ? '% change' : 'Difference' }]} />
                    <button className={`btn-secondary !px-3 !py-1.5 text-xs ${showTable ? '!bg-gray-100' : ''}`} onClick={() => setShowTable(!showTable)}>
                      <Table2 className="h-3.5 w-3.5" /> {showTable ? 'Chart' : 'Table'}
                    </button>
                  </div>
                }>
                {!hasData ? (
                  <EmptyState message={`No ${t.variable.label.toLowerCase()} data for ${startYear}–${endYear}. This variable is available for ${variable.years[0]}–${variable.years[variable.years.length - 1]}.`} />
                ) : showTable && chart ? (
                  <div className="overflow-x-auto">
                    <table className="w-full min-w-[600px]">
                      <thead><tr className="border-b border-gray-100"><th className="th">Area</th>
                        {chart.rows.map((r) => <th key={r.year} className="th text-right">{r.year}{t.partial_years.includes(r.year as number) ? '*' : ''}</th>)}</tr></thead>
                      <tbody>
                        {chart.keys.map((k) => (
                          <tr key={k} className={`border-b border-gray-50 ${k === highlight ? 'bg-emerald-50' : ''}`}>
                            <td className="td font-medium text-gray-900">{shortProvince(k)}</td>
                            {chart.rows.map((r) => (
                              <td key={r.year} className="td text-right tabular-nums">
                                {view === 'values' ? num(r[k], digits) : signed(r[k], 1)}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {t.partial_years.length > 0 && <p className="mt-2 text-xs text-gray-500">* incomplete year</p>}
                  </div>
                ) : chart && (
                  <>
                    {tooManyDistricts && (
                      <div className="mb-3"><Note>Choose a province to draw its districts. {loc.district ? `Showing ${loc.district}${withNational ? ' against the Rwanda-wide average' : ''}.` : withNational ? 'Showing the Rwanda-wide average.' : ''} The comparison below ranks all 30 districts.</Note></div>
                    )}
                    <ResponsiveContainer width="100%" height={340}>
                      <LineChart data={chart.rows} margin={{ top: 8, right: 16, left: 8, bottom: 0 }}>
                        <CartesianGrid stroke="#eef0ef" vertical={false} />
                        <XAxis dataKey="year" tick={{ fontSize: 11 }} />
                        <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => (view === 'values' ? compact(v) : signed(v, tickDigits))} width={56}
                          domain={['auto', 'auto']}
                          label={{ value: view === 'values' ? unit : canPct ? '%' : unit, angle: -90, position: 'insideLeft', fontSize: 11, offset: 0 }} />
                        {t.partial_years.map((y) => (
                          <ReferenceArea key={y} x1={y - 1 >= startYear ? y - 1 : y} x2={y} fill="#9ca3af" fillOpacity={0.15}
                            label={{ value: `${y} incomplete`, position: 'insideTopRight', fontSize: 10, fill: '#6b7280' }} />
                        ))}
                        {view === 'change' && <ReferenceLine y={0} stroke="#9ca3af" />}
                        <Tooltip itemSorter={(i) => -(i.value as number)}
                          formatter={(v: number, name: string) => [view === 'values' ? `${num(v, digits)} ${unit}` : `${signed(v, 1)}${changeUnit}`, shortProvince(name)]} />
                        <Legend wrapperStyle={{ fontSize: 12 }} formatter={(v: string) => shortProvince(v)} />
                        {chart.keys.map((k) => k === NATIONAL ? (
                          <Line isAnimationActive={false} key={k} dataKey={k} stroke={NATIONAL_COLOR} strokeWidth={2} strokeDasharray="5 4" dot={false} />
                        ) : (
                          <Line isAnimationActive={false} key={k} dataKey={k} stroke={colorOf(k)}
                            strokeWidth={k === highlight ? 3 : 2} strokeOpacity={highlight && k !== highlight ? 0.35 : 1}
                            dot={{ r: 3 }} activeDot={{ r: 5 }} />
                        ))}
                      </LineChart>
                    </ResponsiveContainer>
                  </>
                )}
              </Card>

              <Card title={`Compare ${level === 'province' ? 'provinces' : loc.province ? `districts in ${shortProvince(loc.province)}` : 'all districts'}`}
                subtitle={t.comparison.from_year === null ? undefined : rank === 'mean'
                  ? `Average ${t.variable.label.toLowerCase()}, ${t.comparison.from_year}–${t.comparison.to_year}${t.partial_years.length ? ' (complete years only)' : ''}`
                  : `Change from ${t.comparison.from_year} to ${t.comparison.to_year}${canPct ? ' (%)' : ` (${unit})`}`}
                actions={<Segmented value={rank} onChange={setRank} options={[{ value: 'mean', label: 'Average' }, { value: 'change', label: 'Change' }]} />}>
                {comparison.length === 0 ? <EmptyState message={rank === 'change' ? 'Pick at least two years with data to see a change.' : 'No data in this range.'} /> : (
                  <ResponsiveContainer width="100%" height={Math.max(180, comparison.length * 26 + 40)}>
                    <BarChart data={comparison} layout="vertical" margin={{ left: 8, right: 32, top: 4, bottom: 4 }}>
                      <CartesianGrid horizontal={false} stroke="#eef0ef" />
                      <XAxis type="number" tick={{ fontSize: 11 }} tickFormatter={(v) => (rank === 'mean' ? compact(v) : signed(v, tickDigits))} />
                      <YAxis type="category" dataKey="name" width={130} tick={{ fontSize: 11 }} tickFormatter={shortProvince} />
                      {rank === 'change' && <ReferenceLine x={0} stroke="#9ca3af" />}
                      <Tooltip cursor={{ fill: '#f3f4f6' }}
                        formatter={(v: number) => [rank === 'mean' ? `${num(v, digits)} ${unit}` : `${signed(v, 1)}${changeUnit}`, rank === 'mean' ? 'Average' : 'Change']}
                        labelFormatter={(l) => shortProvince(String(l))} />
                      <Bar isAnimationActive={false} dataKey={rank} radius={4} barSize={16}>
                        {comparison.map((r) => {
                          const v = r[rank] as number
                          const fill = rank === 'mean' ? INCREASE : v >= 0 ? INCREASE : DECREASE
                          return <Cell key={r.name} fill={fill} fillOpacity={highlight && r.name !== highlight ? 0.45 : 1} />
                        })}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                )}
                {rank === 'change' && comparison.length > 0 && (
                  <p className="mt-2 flex gap-4 text-xs text-gray-500">
                    <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm" style={{ background: INCREASE }} />Increase</span>
                    <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm" style={{ background: DECREASE }} />Decrease</span>
                  </p>
                )}
              </Card>

              <div className="space-y-2">{t.notes.map((n) => <Note key={n}>{n}</Note>)}</div>
            </div>
          )}

          <Card title={`Climate and harvest together: ${profile.data?.area ?? '…'}`}
            subtitle="Three charts on the same years, each in its own unit. Change the district or province above to update.">
            {profile.error && <ErrorState message={profile.error} onRetry={profile.reload} />}
            {profile.loading && !profile.data && <Loading />}
            {profile.data && (
              <div className={`grid grid-cols-1 gap-6 lg:grid-cols-3 ${profile.loading ? 'opacity-60' : ''}`}>
                <SmallChart title="Rainfall, 12 months (mm)" rows={profile.data.rows}
                  lines={[{ key: 'rain_12m_mm', label: 'Rainfall', color: SERIES_COLORS[0] }]} unit="mm" digits={0} />
                <SmallChart title="Mean temperature, 12 months (°C)" rows={profile.data.rows}
                  lines={[{ key: 'temp_12m_c', label: 'Temperature', color: SERIES_COLORS[1] }]} unit="°C" digits={2} />
                <SmallChart title="Staple crop production (t)" rows={profile.data.rows} partial={profile.data.partial_years}
                  lines={profile.data.crops.map((c, i) => ({ key: c.key, label: c.label.replace(' production', ''), color: SERIES_COLORS[i] }))} unit="t" digits={0} />
              </div>
            )}
            {profile.data && <div className="mt-4 space-y-2">{profile.data.notes.map((n) => <Note key={n}>{n}</Note>)}</div>}
          </Card>

          <Note>{vars.data.note}</Note>
        </div>
      )}
    </>
  )
}

function SmallChart({ title, rows, lines, unit, digits, partial = [] }: {
  title: string; rows: Record<string, number | null>[]; lines: { key: string; label: string; color: string }[]
  unit: string; digits: number; partial?: number[]
}) {
  const has = rows.some((r) => lines.some((l) => r[l.key] !== null))
  return (
    <div>
      <p className="mb-2 text-xs font-semibold text-gray-700">{title}</p>
      {!has ? <EmptyState message="No data in this range." /> : (
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={rows} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="#eef0ef" vertical={false} />
            <XAxis dataKey="year" tick={{ fontSize: 10 }} />
            <YAxis tick={{ fontSize: 10 }} tickFormatter={compact} width={44} domain={['auto', 'auto']} />
            {partial.map((y) => <ReferenceArea key={y} x1={rows.some((r) => r.year === y - 1) ? y - 1 : y} x2={y} fill="#9ca3af" fillOpacity={0.15} />)}
            <Tooltip formatter={(v: number, name: string) => [`${num(v, digits)} ${unit}`, name]} />
            {lines.length > 1 && <Legend wrapperStyle={{ fontSize: 11 }} />}
            {lines.map((l) => (
              <Line isAnimationActive={false} key={l.key} dataKey={l.key} name={l.label} stroke={l.color} strokeWidth={2} dot={{ r: 2.5 }} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
