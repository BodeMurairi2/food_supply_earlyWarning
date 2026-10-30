import { ChevronDown, ChevronRight, Play, RotateCcw } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import AIAssistant from '../components/AIAssistant'
import ContributionChart from '../components/ContributionChart'
import { LocationFilters, YearSelect, type LocationValue } from '../components/LocationFilters'
import { Card, EmptyState, ErrorState, Loading, Note, PageHeader, RiskBadge } from '../components/ui'
import { useAppData } from '../hooks/AppData'
import { useApi } from '../hooks/useApi'
import { pct, RISK_COLORS } from '../lib/format'
import { api } from '../services/api'
import type { FeatureMeta, PredictResult } from '../types/api'

type Inputs = Record<string, string>

const toInputs = (vals: Record<string, number | null>): Inputs =>
  Object.fromEntries(Object.entries(vals).map(([k, v]) => [k, v === null ? '' : String(Math.round(v * 1000) / 1000)]))

function Field({ meta, value, error, onChange }: { meta: FeatureMeta; value: string; error?: string; onChange: (v: string) => void }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium text-gray-600">
        {meta.label}{meta.unit && <span className="text-gray-400"> ({meta.unit})</span>}
      </span>
      <input type="number" step="any" value={value} placeholder="empty: model fills it" onChange={(e) => onChange(e.target.value)}
        className={`select ${error ? 'border-red-400 focus:border-red-500 focus:ring-red-200' : ''}`} />
      {error && <span className="mt-1 block text-xs text-red-600">{error}</span>}
    </label>
  )
}

export default function PredictionLab() {
  const { metadata } = useAppData()
  const [loc, setLoc] = useState<LocationValue>({ province: 'Southern Province', district: 'Huye' })
  const [year, setYear] = useState<number>(2025)
  const [inputs, setInputs] = useState<Inputs>({})
  const [showMore, setShowMore] = useState(false)
  const [result, setResult] = useState<PredictResult | null>(null)
  const [running, setRunning] = useState(false)
  const [ranInputs, setRanInputs] = useState<Record<string, number | null>>({})
  const [runError, setRunError] = useState<string | null>(null)

  const defaults = useApi(() => api.predictDefaults(loc.district, year), [loc.district, year], !!loc.district)
  useEffect(() => {
    if (defaults.data) setInputs(toInputs(defaults.data.inputs))
    setResult(null)
    setRunError(null)
  }, [defaults.data])

  const numeric = useMemo(() => (metadata?.features ?? []).filter((f) => !f.categorical && f.group !== 'Location' && f.group !== 'Time'), [metadata])
  const key = new Set(metadata?.key_features ?? [])
  const keyFields = numeric.filter((f) => key.has(f.feature))
  const moreFields = numeric.filter((f) => !key.has(f.feature))
  const groups = (fields: FeatureMeta[]) =>
    fields.reduce<Record<string, FeatureMeta[]>>((acc, f) => { (acc[f.group] ??= []).push(f); return acc }, {})

  const errors = useMemo(() => {
    const e: Record<string, string> = {}
    numeric.forEach((f) => {
      const v = inputs[f.feature]
      if (v === undefined || v === '') return
      const n = Number(v)
      if (!Number.isFinite(n)) e[f.feature] = 'Enter a number'
      else if (!f.can_be_negative && n < 0) e[f.feature] = 'Cannot be negative'
    })
    return e
  }, [inputs, numeric])

  const run = async () => {
    if (!loc.district || Object.keys(errors).length) return
    setRunning(true)
    setRunError(null)
    try {
      const body = Object.fromEntries(numeric.map((f) => {
        const v = inputs[f.feature]
        return [f.feature, v === undefined || v === '' ? null : Number(v)]
      }))
      setResult(await api.predict({ district: loc.district, year, inputs: body }))
      setRanInputs(body)
    } catch (e) {
      setRunError((e as Error).message)
    } finally {
      setRunning(false)
    }
  }

  const changed = defaults.data
    ? numeric.filter((f) => (inputs[f.feature] ?? '') !== toInputs(defaults.data!.inputs)[f.feature]).length
    : 0
  const [y0, y1] = metadata?.years.dataset ?? [2006, 2026]
  const years = Array.from({ length: y1 - y0 + 1 }, (_, i) => y1 - i)

  const renderGroups = (fields: FeatureMeta[]) => Object.entries(groups(fields)).map(([g, fs]) => (
    <fieldset key={g} className="mb-5">
      <legend className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">{g}</legend>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {fs.map((f) => (
          <Field key={f.feature} meta={f} value={inputs[f.feature] ?? ''} error={errors[f.feature]}
            onChange={(v) => setInputs({ ...inputs, [f.feature]: v })} />
        ))}
      </div>
    </fieldset>
  ))

  return (
    <>
      <PageHeader title="Prediction Lab" subtitle="Start from a real district-year, change the inputs and see how the model responds">
        <div className="flex flex-wrap gap-3">
          <LocationFilters value={loc} onChange={setLoc} allowAll={false} />
          <YearSelect value={year} onChange={(y) => setYear(y === '' ? 2025 : y)} years={years} />
        </div>
      </PageHeader>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-5">
        <Card className="xl:col-span-3" title="Model inputs"
          subtitle={`Loaded from the dataset for ${loc.district || '…'} ${year}. ${changed ? `${changed} input(s) changed.` : 'No changes yet.'}`}
          actions={
            <div className="flex gap-2">
              <button className="btn-secondary" disabled={!defaults.data}
                onClick={() => { if (defaults.data) setInputs(toInputs(defaults.data.inputs)); setResult(null) }}>
                <RotateCcw className="h-4 w-4" /> Reset
              </button>
              <button className="btn-primary" onClick={run} disabled={running || !defaults.data || Object.keys(errors).length > 0}>
                <Play className="h-4 w-4" /> {running ? 'Running…' : 'Run prediction'}
              </button>
            </div>
          }>
          {!loc.district && <EmptyState message="Choose a district." />}
          {defaults.loading && <Loading />}
          {defaults.error && <ErrorState message={defaults.error} onRetry={defaults.reload} />}
          {defaults.data && (
            <>
              {renderGroups(keyFields)}
              <button className="mb-3 flex items-center gap-1 text-sm font-medium text-brand" onClick={() => setShowMore(!showMore)}>
                {showMore ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                More inputs ({moreFields.length})
              </button>
              {showMore && renderGroups(moreFields)}
              <Note>Empty fields are filled by the model's training medians. Changes to one input do not update related inputs (for example, changing rain does not change yields).</Note>
            </>
          )}
        </Card>

        <div className="space-y-6 xl:col-span-2">
          <Card title="Result">
            {runError && <ErrorState message={runError} />}
            {!result && !runError && <EmptyState message="Run the model to see a prediction." />}
            {result && (
              <div className="space-y-4">
                <div className="flex items-end gap-4">
                  <p className="text-4xl font-semibold" style={{ color: RISK_COLORS[result.risk] }}>{pct(result.prediction)}</p>
                  <div className="pb-1"><RiskBadge risk={result.risk} /></div>
                </div>
                <p className="text-sm text-gray-600">
                  Predicted share of households food insecure in {result.district}, {result.year}.
                  {result.dataset_value_this_year !== null && <> The dataset value for this year is {pct(result.dataset_value_this_year)}.</>}
                </p>
                <p className="text-xs text-gray-500">{result.model}. Average starting point {pct(result.base_value)}.</p>
                {result.missing_inputs_imputed.length > 0 && (
                  <Note>Filled by the model ({result.missing_inputs_imputed.length}): {result.missing_inputs_imputed.join(', ')}</Note>
                )}
              </div>
            )}
          </Card>

          {result && (
            <Card title="Contributions" subtitle="How each input moved the prediction away from the average">
              <ContributionChart contributions={result.contributions} />
            </Card>
          )}

          {result && (
            <Card title="Survey history" subtitle={`${result.district}, from the dataset`}>
              <div className="flex flex-wrap gap-2">
                {result.history.filter((h) => h.observed !== null).map((h) => (
                  <div key={h.year} className="rounded-lg border border-gray-100 px-2.5 py-1.5 text-xs">
                    <p className="font-medium text-gray-900">{h.year}</p>
                    <p className="tabular-nums text-gray-600">{pct(h.observed)}</p>
                    <p className="text-[10px] text-gray-400">{h.observation_type}</p>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>
      </div>
      {result && (
        <div className="mt-6">
          <AIAssistant key={JSON.stringify([result.district, result.year, ranInputs])} title={`AI assistant: ${result.district}, ${result.year}`}
            request={{ kind: 'prediction', district: result.district, year: result.year, inputs: ranInputs }} />
        </div>
      )}
      {result && <div className="mt-6"><Note>{result.note}</Note></div>}
    </>
  )
}
