import { AlertTriangle, CalendarClock, ClipboardList, MapPin } from 'lucide-react'
import { useState } from 'react'
import {
  CartesianGrid, ComposedChart, Legend, Line, ReferenceArea, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import DistrictMap from '../components/DistrictMap'
import { LocationFilters, YearSelect, type LocationValue } from '../components/LocationFilters'
import { Card, EmptyState, ErrorState, Loading, Note, PageHeader, RiskBadge, StatCard } from '../components/ui'
import { useAppData } from '../hooks/AppData'
import { useApi } from '../hooks/useApi'
import { pct, shortProvince } from '../lib/format'
import { api } from '../services/api'

export default function Overview() {
  const { metadata } = useAppData()
  const [loc, setLoc] = useState<LocationValue>({ province: '', district: '' })
  const [year, setYear] = useState<number>(2025)
  const { data, loading, error, reload } = useApi(
    () => api.overview({ province: loc.province, district: loc.district, year }),
    [loc.province, loc.district, year],
  )

  const [y0, y1] = metadata?.years.dataset ?? [2006, 2026]
  const years = Array.from({ length: y1 - y0 + 1 }, (_, i) => y1 - i)
  const forecastStart = metadata?.years.forecast[0] ?? 2025

  // Split the trend into an observed line and a forecast line that joins at the last observed year.
  const trend = (data?.trend ?? []).map((t) => ({
    ...t,
    observed: t.year < forecastStart ? t.food_insecure_pct : null,
    forecast: t.year >= forecastStart - 1 ? t.food_insecure_pct : null,
  }))

  return (
    <>
      <PageHeader title="Overview" subtitle="District food insecurity in Rwanda, 2006–2026">
        <div className="flex flex-wrap gap-3">
          <LocationFilters value={loc} onChange={setLoc} />
          <YearSelect value={year} onChange={(y) => setYear(y === '' ? 2025 : y)} years={years} label="Map year" />
        </div>
      </PageHeader>

      {error && <ErrorState message={error} onRetry={reload} />}
      {loading && !data && <Loading />}

      {data && (
        <div className={`space-y-6 ${loading ? 'opacity-60' : ''}`}>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard icon={<MapPin className="h-5 w-5" />} label="Districts in view" value={data.n_districts} />
            <StatCard icon={<ClipboardList className="h-5 w-5" />} tone="blue"
              label={`Latest survey (${data.latest_survey.year})`} value={pct(data.latest_survey.avg_food_insecure_pct)}
              hint="Average share food insecure (CARI)" />
            <StatCard icon={<CalendarClock className="h-5 w-5" />} tone="amber" label="Forecast average"
              value={<span className="flex gap-4 text-xl">{Object.entries(data.forecast_avg).map(([y, v]) => (
                <span key={y}>{pct(v)}<span className="ml-1 text-xs font-normal text-gray-400">{y}</span></span>
              ))}</span>}
              hint="Random forest trained on 2006–2024" />
            <StatCard icon={<AlertTriangle className="h-5 w-5" />} tone="danger"
              label={`High-risk districts (${data.selected_year.year})`} value={data.selected_year.risk_counts.High ?? 0}
              hint={`Medium ${data.selected_year.risk_counts.Medium ?? 0} · Low ${data.selected_year.risk_counts.Low ?? 0}`} />
          </div>

          <div className="grid grid-cols-1 gap-6 xl:grid-cols-5">
            <Card className="xl:col-span-2" title={`Risk map, ${data.selected_year.year}`}
              subtitle={`${data.selected_year.value_type} · average ${pct(data.selected_year.avg_food_insecure_pct)}`}>
              <DistrictMap values={data.map}
                onSelect={(d) => setLoc({ province: data.map.find((m) => m.district === d)?.province ?? '', district: d })} />
            </Card>

            <Card className="xl:col-span-3" title="Food insecurity trend"
              subtitle="Average share of households food insecure. Shaded years are forecasts.">
              {trend.length === 0 ? <EmptyState message="No trend data for this selection." /> : (
                <ResponsiveContainer width="100%" height={320}>
                  <ComposedChart data={trend} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                    <CartesianGrid stroke="#eef0ef" vertical={false} />
                    <XAxis dataKey="year" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} unit="%" />
                    <ReferenceArea x1={forecastStart} x2={y1} fill="#f59e0b" fillOpacity={0.08} />
                    <Tooltip formatter={(v: number) => pct(v)} />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Line isAnimationActive={false} dataKey="observed" name="Observed / estimated" stroke="#059669" strokeWidth={2} dot={{ r: 2 }} connectNulls={false} />
                    <Line isAnimationActive={false} dataKey="forecast" name="Forecast" stroke="#d97706" strokeWidth={2} strokeDasharray="5 4" dot={{ r: 3 }} />
                  </ComposedChart>
                </ResponsiveContainer>
              )}
            </Card>
          </div>

          <div className="grid grid-cols-1 gap-6 xl:grid-cols-5">
            <Card className="xl:col-span-3" title="Climate signals" subtitle="Feature window: April of the year before to March. Rwanda-wide or selected-area averages.">
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                {[
                  { key: 'rain_pct_normal', title: 'Rainfall, % of long-term normal', unit: '%', ref: 100, color: '#2a78d6' },
                  { key: 'temp_anomaly_c', title: 'Temperature anomaly (°C)', unit: '°C', ref: 0, color: '#eb6834' },
                ].map((c) => (
                  <div key={c.key}>
                    <p className="mb-2 text-xs font-semibold text-gray-700">{c.title}</p>
                    <ResponsiveContainer width="100%" height={230}>
                      <ComposedChart data={data.trend} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                        <CartesianGrid stroke="#eef0ef" vertical={false} />
                        <XAxis dataKey="year" tick={{ fontSize: 10 }} />
                        <YAxis tick={{ fontSize: 10 }} domain={['auto', 'auto']} width={40} />
                        <ReferenceLine y={c.ref} stroke="#9ca3af" strokeDasharray="3 3" />
                        <Tooltip formatter={(v: number) => [`${v.toFixed(c.unit === '%' ? 1 : 2)} ${c.unit}`, c.title]} />
                        <Line isAnimationActive={false} dataKey={c.key} stroke={c.color} strokeWidth={2} dot={false} />
                      </ComposedChart>
                    </ResponsiveContainer>
                  </div>
                ))}
              </div>
            </Card>

            <Card className="xl:col-span-2" title={`Most food insecure, ${data.selected_year.year}`}>
              {data.top_districts.length === 0 ? <EmptyState message="No values for this year." /> : (
                <table className="w-full">
                  <thead><tr className="border-b border-gray-100"><th className="th">District</th><th className="th">Province</th><th className="th text-right">Value</th><th className="th">Risk</th></tr></thead>
                  <tbody>
                    {data.top_districts.map((t) => (
                      <tr key={t.district} className="border-b border-gray-50 last:border-0">
                        <td className="td font-medium text-gray-900">{t.district}</td>
                        <td className="td">{shortProvince(t.province)}</td>
                        <td className="td text-right tabular-nums">{pct(t.value)}</td>
                        <td className="td"><RiskBadge risk={t.risk} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </Card>
          </div>

          <Note>{data.note} {metadata?.risk_thresholds_note}</Note>
        </div>
      )}
    </>
  )
}
