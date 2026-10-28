import type { Risk } from '../types/api'

export const RISK_COLORS: Record<Risk, string> = {
  Low: '#16a34a',
  Medium: '#d97706',
  High: '#dc2626',
}

export const NO_DATA_COLOR = '#d1d5db'

export const PROVINCE_COLORS: Record<string, string> = {
  'Eastern Province': '#2563eb',
  'Kigali City': '#7c3aed',
  'Northern Province': '#059669',
  'Southern Province': '#d97706',
  'Western Province': '#dc2626',
}

// Categorical slots in fixed order (validated for colour-vision deficiency on a white surface).
// Colour follows the entity: a series keeps its slot when filters change.
export const SERIES_COLORS = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#6250d6', '#e34948']
export const NATIONAL_COLOR = '#52514e'

export function pct(v: number | null | undefined, digits = 1) {
  return v === null || v === undefined || Number.isNaN(v) ? '—' : `${v.toFixed(digits)}%`
}

export function num(v: number | null | undefined, digits = 1) {
  return v === null || v === undefined || Number.isNaN(v) ? '—' : v.toLocaleString(undefined, { maximumFractionDigits: digits })
}

export function signed(v: number | null | undefined, digits = 1) {
  if (v === null || v === undefined || Number.isNaN(v)) return '—'
  return `${v > 0 ? '+' : ''}${v.toFixed(digits)}`
}

export function shortProvince(p: string) {
  return p.replace(' Province', '')
}
