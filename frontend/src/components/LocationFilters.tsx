import { useAppData } from '../hooks/AppData'
import { shortProvince } from '../lib/format'

export interface LocationValue { province: string; district: string }

/** Province + district selects; the district list is limited to the chosen province. */
export function LocationFilters({ value, onChange, allowAll = true }: {
  value: LocationValue; onChange: (v: LocationValue) => void; allowAll?: boolean
}) {
  const { locations, provinceOf } = useAppData()
  const provinces = locations?.provinces ?? []
  const districts = value.province
    ? provinces.find((p) => p.province === value.province)?.districts ?? []
    : provinces.flatMap((p) => p.districts).sort()

  return (
    <>
      <label className="block min-w-44">
        <span className="mb-1 block text-xs font-medium text-gray-500">Province</span>
        <select className="select" value={value.province}
          onChange={(e) => onChange({ province: e.target.value, district: '' })}>
          {allowAll && <option value="">All provinces</option>}
          {provinces.map((p) => <option key={p.province} value={p.province}>{shortProvince(p.province)}</option>)}
        </select>
      </label>
      <label className="block min-w-44">
        <span className="mb-1 block text-xs font-medium text-gray-500">District</span>
        <select className="select" value={value.district}
          onChange={(e) => {
            const d = e.target.value
            onChange({ province: d ? provinceOf(d) ?? value.province : value.province, district: d })
          }}>
          {allowAll && <option value="">All districts</option>}
          {districts.map((d) => <option key={d} value={d}>{d}</option>)}
        </select>
      </label>
    </>
  )
}

export function YearSelect({ value, onChange, years, label = 'Year', allowAll }: {
  value: number | ''; onChange: (y: number | '') => void; years: number[]; label?: string; allowAll?: string
}) {
  return (
    <label className="block min-w-32">
      <span className="mb-1 block text-xs font-medium text-gray-500">{label}</span>
      <select className="select" value={value}
        onChange={(e) => onChange(e.target.value === '' ? '' : Number(e.target.value))}>
        {allowAll && <option value="">{allowAll}</option>}
        {years.map((y) => <option key={y} value={y}>{y}</option>)}
      </select>
    </label>
  )
}
