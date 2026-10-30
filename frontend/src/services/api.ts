import type {
  AIContext, AIStatus, AssistantRequest, AssistantResult,
  DistrictSeries, Explanation, FeatureImportance, Forecasts, Historical, Locations, Metadata, Overview,
  Performance, PredictDefaults, PredictResult, VizProfile, VizTrends, VizVariables,
} from '../types/api'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

function query(params: Record<string, string | number | null | undefined>) {
  const q = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => {
    if (v !== null && v !== undefined && v !== '') q.set(k, String(v))
  })
  const s = q.toString()
  return s ? `?${s}` : ''
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(`/api${path}`, init)
  } catch {
    throw new ApiError(0, 'Cannot reach the HarvestWatch API. Is the backend running on port 8000?')
  }
  if (!res.ok) {
    let message = `Request failed (${res.status})`
    try {
      const body = await res.json()
      if (typeof body.detail === 'string') message = body.detail
      else if (Array.isArray(body.detail)) message = body.detail.map((d: { msg: string }) => d.msg).join('; ')
    } catch { /* keep default message */ }
    throw new ApiError(res.status, message)
  }
  return res.json() as Promise<T>
}

type LocationFilter = { province?: string | null; district?: string | null }

export const api = {
  metadata: () => request<Metadata>('/metadata'),
  locations: () => request<Locations>('/locations'),
  boundaries: () => request<GeoJSON.FeatureCollection>('/boundaries'),
  overview: (f: LocationFilter & { year: number }) => request<Overview>(`/overview${query(f)}`),
  historical: (f: LocationFilter & { year?: number | null }) => request<Historical>(`/historical${query(f)}`),
  performance: () => request<Performance>('/model/performance'),
  featureImportance: (model: 'final' | 'evaluation') => request<FeatureImportance>(`/model/feature-importance${query({ model })}`),
  explain: (district: string, year: number) => request<Explanation>(`/model/explain${query({ district, year })}`),
  forecasts: (f: LocationFilter) => request<Forecasts>(`/forecasts${query(f)}`),
  districtSeries: (district: string) => request<DistrictSeries>(`/district-series${query({ district })}`),
  predictDefaults: (district: string, year: number) => request<PredictDefaults>(`/predict/defaults${query({ district, year })}`),
  vizVariables: () => request<VizVariables>('/visualizations/variables'),
  vizTrends: (q: LocationFilter & { variable: string; level: 'province' | 'district'; start_year: number; end_year: number }) =>
    request<VizTrends>(`/visualizations/trends${query(q)}`),
  vizProfile: (q: LocationFilter & { start_year: number; end_year: number }) =>
    request<VizProfile>(`/visualizations/profile${query(q)}`),
  aiStatus: () => request<AIStatus>('/ai/status'),
  aiContext: (district: string, year: number) => request<AIContext>(`/ai/context${query({ district, year })}`),
  aiAssistant: (body: AssistantRequest) =>
    request<AssistantResult>('/ai/assistant', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }),
  predict: (body: { district: string; year: number; inputs: Record<string, number | null> }) =>
    request<PredictResult>('/predict', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
}
