import { BookOpen, ChevronDown, ChevronUp } from 'lucide-react'
import { useState } from 'react'
import { num } from '../lib/format'
import type { EvaluationSet } from '../types/api'

interface Entry {
  name: string
  direction: string
  meaning: string
  forecasting: string
  example: string
}

const percent = (v: number | null | undefined) => (v === null || v === undefined ? '—' : `${(v * 100).toFixed(1)}%`)

function entries(set: EvaluationSet): { title: string; intro: string; items: Entry[] }[] {
  const { regression: r, last_survey: last, classification: c } = set
  const high = c.classes.find((x) => x.label === 'High')
  const mae = r.mae ?? 0
  return [
    {
      title: 'Predicting the percentage',
      intro: 'The model estimates the share of households in a district that are food insecure. These numbers show how close that estimate gets.',
      items: [
        {
          name: 'MAE (average error)',
          direction: 'Lower is better',
          meaning: 'How far the estimate is from the true value, on average.',
          forecasting: 'It tells you how much room to leave around a forecast. Treat a forecast as a range, not an exact number.',
          example: `Here it is ${num(mae, 2)} points. If the true value is 20%, the estimate is typically between about ${num(20 - mae, 1)}% and ${num(20 + mae, 1)}%.`,
        },
        {
          name: 'RMSE',
          direction: 'Lower is better',
          meaning: 'Also an average error, but big mistakes count much more than small ones.',
          forecasting: 'Big misses are the costly ones in planning. When RMSE is well above MAE, the model sometimes misses by a lot.',
          example: `Here it is ${num(r.rmse, 2)} points, against ${num(mae, 2)} for MAE.`,
        },
        {
          name: 'R²',
          direction: 'Higher is better',
          meaning: 'How much of the differences between districts and years the model explains. 100% is perfect; 0% is no better than always guessing the average.',
          forecasting: 'It shows whether the model really tells districts apart, which is what you need to decide where to look first.',
          example: `Here it is ${r.r2?.toFixed(2) ?? '—'}, so the model explains about ${Math.round((r.r2 ?? 0) * 100)}% of those differences.`,
        },
        {
          name: 'MAE when copying the last survey',
          direction: 'The model should beat this',
          meaning: 'The error you would get with no model at all, by assuming nothing has changed since the last survey.',
          forecasting: 'This is the simplest possible forecast. A model is only worth using if it does better.',
          example: `Copying the last survey gives ${num(last.mae, 2)} points; the model gives ${num(mae, 2)}.`,
        },
      ],
    },
    {
      title: 'Predicting the risk class',
      intro: 'Each estimate is also placed in a class: Low (below 15%), Medium (15–30%) or High (30% or more). These numbers show how often that class is right.',
      items: [
        {
          name: 'Accuracy',
          direction: 'Higher is better',
          meaning: 'The share of districts placed in the correct class.',
          forecasting: 'A quick overall score. It can hide problems with rare classes, so read it together with recall.',
          example: `Here it is ${percent(c.accuracy)}, about ${Math.round(c.accuracy * 10)} districts out of 10.`,
        },
        {
          name: 'Precision',
          direction: 'Higher is better',
          meaning: 'When the model names a class, how often it is right.',
          forecasting: 'It measures false alarms. Low precision for High means attention and resources go to districts that did not need them.',
          example: high ? `For High it is ${percent(high.precision)}: of ${high.predicted} districts flagged High, ${high.correct} really were.` : '',
        },
        {
          name: 'Recall',
          direction: 'Higher is better',
          meaning: 'Of all the districts truly in a class, how many the model found.',
          forecasting: 'It measures missed cases. For an early warning system, recall on High matters most: a missed district gets no warning.',
          example: high ? `For High it is ${percent(high.recall)}: the model found ${high.correct} of the ${high.observed} districts that were truly High.` : '',
        },
        {
          name: 'F1',
          direction: 'Higher is better',
          meaning: 'One score that combines precision and recall. It is only high when both are good.',
          forecasting: 'It stops a model from looking good by flagging everything, or by flagging almost nothing.',
          example: high ? `For High it is ${percent(high.f1)}, from precision ${percent(high.precision)} and recall ${percent(high.recall)}.` : '',
        },
        {
          name: 'ROC-AUC',
          direction: 'Higher is better',
          meaning: 'How well the model ranks districts. Take one district truly in a class and one that is not: this is the chance the model gives the right one the higher score. 50% is a coin toss; 100% is perfect.',
          forecasting: 'It shows whether the model can put districts in the right order, which helps decide who to check first, even when the class label is wrong.',
          example: high ? `For High it is ${percent(high.roc_auc)}. So the ranking is much stronger than the High label alone suggests.` : '',
        },
      ],
    },
  ]
}

/** A button that opens a plain-language explanation of the metrics, using the values on the page. */
export default function MetricGuide({ set }: { set: EvaluationSet }) {
  const [open, setOpen] = useState(false)
  return (
    <div>
      <button className="btn-secondary" onClick={() => setOpen(!open)} aria-expanded={open} aria-controls="metric-guide">
        <BookOpen className="h-4 w-4" />
        What do these numbers mean?
        {open ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
      </button>

      {open && (
        <div id="metric-guide" className="mt-4 space-y-6">
          <p className="text-sm text-gray-600">The examples use the {set.label} results.</p>
          {entries(set).map((group) => (
            <section key={group.title} className="card p-5">
              <h2 className="text-sm font-semibold text-gray-900">{group.title}</h2>
              <p className="mt-1 text-sm text-gray-600">{group.intro}</p>
              <dl className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
                {group.items.map((m) => (
                  <div key={m.name} className="rounded-lg border border-gray-100 p-4">
                    <dt className="flex flex-wrap items-center justify-between gap-2">
                      <span className="text-sm font-semibold text-gray-900">{m.name}</span>
                      <span className="rounded-full bg-gray-100 px-2 py-0.5 text-[11px] text-gray-600">{m.direction}</span>
                    </dt>
                    <dd className="mt-2 space-y-2 text-sm text-gray-700">
                      <p>{m.meaning}</p>
                      <p><span className="font-medium text-gray-900">For forecasting: </span>{m.forecasting}</p>
                      <p className="text-gray-500">{m.example}</p>
                    </dd>
                  </div>
                ))}
              </dl>
            </section>
          ))}
        </div>
      )}
    </div>
  )
}
