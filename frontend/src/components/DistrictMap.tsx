import { geoMercator, geoPath } from 'd3-geo'
import { useMemo, useState } from 'react'
import { api } from '../services/api'
import { useApi } from '../hooks/useApi'
import { NO_DATA_COLOR, RISK_COLORS, pct } from '../lib/format'
import type { MapValue } from '../types/api'
import { ErrorState, Loading } from './ui'

const W = 420
const H = 360

/** Rwanda district map (GADM 4.1 boundaries) coloured by risk class. */
export default function DistrictMap({ values, onSelect }: { values: MapValue[]; onSelect?: (district: string) => void }) {
  const { data: geo, loading, error, reload } = useApi(api.boundaries, [])
  const [hover, setHover] = useState<MapValue | null>(null)
  const byDistrict = useMemo(() => new Map(values.map((v) => [v.district, v])), [values])

  const paths = useMemo(() => {
    if (!geo) return []
    const projection = geoMercator().fitSize([W, H], geo)
    const path = geoPath(projection)
    return geo.features.map((f) => ({ district: f.properties?.district as string, d: path(f) ?? '' }))
  }, [geo])

  if (loading) return <Loading label="Loading map…" />
  if (error) return <ErrorState message={error} onRetry={reload} />

  return (
    <div className="relative">
      <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img" aria-label="Map of Rwanda districts by food insecurity risk">
        {paths.map(({ district, d }) => {
          const v = byDistrict.get(district)
          const fill = v?.risk ? RISK_COLORS[v.risk] : NO_DATA_COLOR
          const dimmed = v && v.selected === false
          return (
            <path key={district} d={d} fill={fill} fillOpacity={dimmed ? 0.18 : 0.85}
              stroke="#ffffff" strokeWidth={1}
              className={onSelect ? 'cursor-pointer' : ''}
              onMouseEnter={() => v && setHover(v)} onMouseLeave={() => setHover(null)}
              onClick={() => onSelect?.(district)} />
          )
        })}
      </svg>
      {hover && (
        <div className="pointer-events-none absolute left-2 top-2 rounded-lg border border-gray-200 bg-white/95 px-3 py-2 text-xs shadow">
          <p className="font-semibold text-gray-900">{hover.district}</p>
          <p className="text-gray-600">{pct(hover.value)} · {hover.risk ?? 'no data'}</p>
          <p className="text-gray-400">{hover.value_type}</p>
        </div>
      )}
      <div className="mt-2 flex flex-wrap gap-3 text-xs text-gray-600">
        {Object.entries(RISK_COLORS).map(([k, c]) => (
          <span key={k} className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: c }} />{k}</span>
        ))}
        <span className="text-gray-400">Boundaries: GADM 4.1</span>
      </div>
    </div>
  )
}
