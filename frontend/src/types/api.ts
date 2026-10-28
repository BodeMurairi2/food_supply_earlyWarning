export type Risk = 'Low' | 'Medium' | 'High'

export interface Threshold { label: Risk; min: number | null; max: number | null }

export interface FeatureMeta {
  feature: string
  label: string
  group: string
  unit: string
  categorical: boolean
  can_be_negative: boolean
}

export interface Metadata {
  target: string
  target_label: string
  target_scale: string
  years: { dataset: [number, number]; test: [number, number]; forecast: [number, number]; survey_years: number[] }
  risk_thresholds: Threshold[]
  risk_thresholds_note: string
  model: Record<string, string | number>
  features: FeatureMeta[]
  key_features: string[]
  n_districts: number
}

export interface Locations { provinces: { province: string; districts: string[] }[] }

export interface Scores { n: number; mae: number | null; rmse: number | null; r2: number | null }

export interface MapValue {
  province: string
  district: string
  value: number | null
  value_type: string
  risk: Risk | null
  selected?: boolean
}

export interface TrendPoint {
  year: number
  food_insecure_pct: number | null
  value_type: string
  rain_pct_normal: number | null
  temp_anomaly_c: number | null
  maize_yield_kg_ha: number | null
  beans_yield_kg_ha: number | null
}

export interface Overview {
  filters: { province: string | null; district: string | null; year: number }
  n_districts: number
  latest_survey: { year: number; avg_food_insecure_pct: number | null }
  forecast_avg: Record<string, number | null>
  selected_year: { year: number; value_type: string; avg_food_insecure_pct: number | null; risk_counts: Record<Risk, number> }
  map: MapValue[]
  trend: TrendPoint[]
  top_districts: MapValue[]
  note: string
}

export interface HistoricalRow {
  year: number
  province: string
  district: string
  observed: number
  observation_type: string
  is_real_survey: boolean
  predicted: number
  error: number
  observed_risk: Risk
  predicted_risk: Risk
  persistence: number | null
}

export interface Historical {
  rows: HistoricalRow[]
  metrics: { all_rows: Scores; real_surveys: Scores; persistence_real_surveys: Scores }
}

export interface Performance {
  evaluation_setup: string
  train: Scores
  test_all_rows: Scores
  test_real_surveys: Scores
  persistence_real_surveys: Scores
  risk_class_agreement_real_surveys: number
  by_year: (Scores & { year: number; observation_type: string })[]
  by_province_real_surveys: (Scores & { province: string })[]
  caveats: string[]
}

export interface ImportanceItem {
  feature: string
  label: string
  group: string
  impurity_importance: number
  mean_abs_shap: number
}

export interface FeatureImportance { model: string; shap_rows: string; note: string; features: ImportanceItem[] }

export interface Contribution {
  feature: string
  label: string
  group: string
  unit: string
  value: number | string | null
  contribution: number
}

export interface Explanation {
  district: string
  province: string
  year: number
  model: string
  prediction: number
  risk: Risk
  observed: number | null
  base_value: number
  contributions: Contribution[]
  note: string
}

export interface Driver { label: string; contribution: number }

export interface ForecastRow {
  province: string
  district: string
  observed_2024: number | null
  predicted_2025: number
  risk_2025: Risk
  drivers_2025: Driver[]
  predicted_2026: number
  risk_2026: Risk
  drivers_2026: Driver[]
}

export interface Forecasts { rows: ForecastRow[]; status: Record<string, string>; note: string }

export interface SeriesPoint {
  year: number
  observed: number | null
  observation_type: string | null
  test_prediction: number | null
  forecast: number | null
}

export interface DistrictSeries { district: string; province: string; series: SeriesPoint[] }

export interface PredictDefaults { district: string; province: string; year: number; inputs: Record<string, number | null> }

export interface PredictResult {
  district: string
  province: string
  year: number
  prediction: number
  risk: Risk
  base_value: number
  contributions: Contribution[]
  missing_inputs_imputed: string[]
  history: { year: number; observed: number | null; observation_type: string | null }[]
  dataset_value_this_year: number | null
  model: string
  note: string
}

export interface VizVariable {
  key: string
  label: string
  topic: string
  unit: string
  aggregation: 'sum' | 'mean'
  change: 'pct' | 'diff'
  years: number[]
  partial_years: number[]
}

export interface VizVariables {
  variables: VizVariable[]
  topics: string[]
  years: [number, number]
  default_years: [number, number]
  note: string
}

export interface YearValue { year: number; value: number | null }

export interface VizTrends {
  variable: VizVariable
  level: 'province' | 'district'
  filters: { province: string | null; district: string | null; start_year: number; end_year: number }
  highlight: string | null
  years: number[]
  series: { name: string; province: string; points: YearValue[] }[]
  national: YearValue[]
  comparison: {
    from_year: number | null
    to_year: number | null
    change_kind: 'pct' | 'diff'
    rows: { name: string; province: string; mean: number | null; start: number | null; end: number | null; change: number | null }[]
  }
  partial_years: number[]
  notes: string[]
}

export interface VizProfile {
  area: string
  level: 'district' | 'province' | 'national'
  crops: { key: string; label: string }[]
  rows: ({ year: number; rain_12m_mm: number | null; rain_12m_pct_normal: number | null; temp_12m_c: number | null; temp_12m_anomaly_c: number | null } & Record<string, number | null>)[]
  partial_years: number[]
  notes: string[]
}

export interface AIStatus { llm: boolean; search: boolean; model: string }

export interface AIContext {
  district: string
  province: string
  year: number
  model: {
    name: string
    target: string
    prediction_pct: number
    risk_class: Risk
    risk_thresholds: string
    observed_pct_this_year: number | null
    model_average_pct: number
    typical_error_points: string
    forecasts: Record<string, number>
  }
  contributions: { feature: string; value: number | string | null; unit: string; points: number }[]
  survey_history: { year: number; pct: number | null; type: string }[]
  data_notes: string[]
}

export interface AISource {
  id: string
  title: string
  url: string
  snippet: string
  published_date: string | null
  query: string
  cited: boolean
}

export interface AIAnalysis {
  interpretation: string
  drivers: { feature: string; direction: 'raises' | 'lowers'; points: number; explanation: string }[]
  external_evidence: { finding: string; sources: string[]; scope: string; credibility: string; relevance: string }[]
  implications_2027: { scenario: string; uncertainty: string }[]
  recommendations: { action: string; rationale: string; sources: string[] }[]
  limitations: string[]
}

export interface AIResult {
  district: string
  year: number
  question: string | null
  context: AIContext
  analysis: AIAnalysis
  sources: AISource[]
  searches: string[]
  llm_model: string
  generated_at: string
  warnings: string[]
  cached: boolean
}
