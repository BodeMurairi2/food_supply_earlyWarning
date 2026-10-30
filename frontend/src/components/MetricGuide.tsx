import { ArrowLeft, ArrowRight, BookOpen, X } from 'lucide-react'
import { useEffect, useRef, useState, type ReactNode } from 'react'
import { num } from '../lib/format'
import type { EvaluationSet } from '../types/api'

const percent = (v: number | null | undefined) => (v === null || v === undefined ? '—' : `${(v * 100).toFixed(1)}%`)

interface Topic {
  id: string
  name: string
  value?: string
  body: ReactNode
}

function Part({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="mt-6">
      <h3 className="text-sm font-semibold text-gray-900">{title}</h3>
      <div className="mt-2 space-y-3 text-[15px] leading-7 text-gray-700">{children}</div>
    </section>
  )
}

function topics(test: EvaluationSet, surveys: EvaluationSet): Topic[] {
  const r = test.regression
  const c = test.classification
  const high = c.classes.find((x) => x.label === 'High')!
  const low = c.classes.find((x) => x.label === 'Low')!
  const mae = r.mae ?? 0
  const missed = high.observed - high.correct

  return [
    {
      id: 'start', name: 'Start here',
      body: (
        <>
          <p className="text-[15px] leading-7 text-gray-700">
            This page answers one practical question: <b>how far can you rely on the model when you decide where to look first?</b>
          </p>
          <p className="mt-3 text-[15px] leading-7 text-gray-700">
            To answer it fairly, we taught the model using data up to 2020 only. We then asked it to estimate food insecurity for 2021 to 2024,
            years it had never seen, and compared its answers with what was recorded.
          </p>
          <Part title="The short version">
            <ul className="list-disc space-y-2 pl-5">
              <li>Its estimates are usually within about {num(mae, 1)} percentage points of the recorded value.</li>
              <li>It is more accurate than simply assuming nothing has changed since the last survey.</li>
              <li>It is good at putting districts in the right order, from least to most food insecure.</li>
              <li>It is more cautious than reality at the top: it found {high.correct} of the {high.observed} High districts and placed most of the others in Medium.</li>
            </ul>
          </Part>
          <Part title="What we suggest">
            <p>Use the model to decide where to look first, then confirm with field knowledge before committing resources. It supports a decision; it does not replace one.</p>
          </Part>
          <Part title="Reading the columns">
            <p>
              <b>Test data 2021–2024</b> covers all four years. <b>Real surveys</b> covers only 2021 and 2024, when households were actually surveyed;
              the two years between are estimated from those surveys. The real-survey columns are therefore the strictest test.
            </p>
          </Part>
          <p className="mt-6 text-sm text-gray-500">Each of the next sections covers one measure. Take them in order, or jump to the one you need.</p>
        </>
      ),
    },
    {
      id: 'mae', name: 'Average error (MAE)', value: `${num(mae, 2)} pts`,
      body: (
        <>
          <Part title="What it tells you">
            <p>This is the typical size of the model's mistake. If we estimate that 20% of households in a district are food insecure and the recorded value is 25%, that is an error of 5 points. MAE is the average of those errors. Lower is better.</p>
          </Part>
          <Part title="Where we stand">
            <p>The average error is {num(mae, 2)} points. So if the true value were 20%, you would typically see an estimate between about {num(20 - mae, 1)}% and {num(20 + mae, 1)}%.</p>
            <p>On real surveys alone, the error is {num(surveys.regression.mae, 2)} points. That is the better guide for a forecast, because a forecast will eventually be compared with a real survey.</p>
          </Part>
          <Part title="How to use it">
            <p>Read every forecast as a range, not a precise figure. A forecast of 28% is not clearly different from one of 31%, even though they carry different risk labels. Two districts only a few points apart should be treated as similar.</p>
          </Part>
        </>
      ),
    },
    {
      id: 'rmse', name: 'RMSE', value: `${num(r.rmse, 2)} pts`,
      body: (
        <>
          <Part title="What it tells you">
            <p>RMSE is also an average error, but it penalises large mistakes much more than small ones. Being wrong by 15 points once counts for far more than being wrong by 3 points five times. Lower is better.</p>
          </Part>
          <Part title="Where we stand">
            <p>RMSE is {num(r.rmse, 2)} points, against {num(mae, 2)} for the average error. The gap between the two is what matters: most errors are moderate, but there are some larger misses.</p>
          </Part>
          <Part title="How to use it">
            <p>Large misses are the ones that hurt in planning. This measure is a reminder that an individual district can occasionally be further off than the average suggests, so an unexpected result deserves a second look rather than immediate action.</p>
          </Part>
        </>
      ),
    },
    {
      id: 'r2', name: 'R²', value: percent(r.r2),
      body: (
        <>
          <Part title="What it tells you">
            <p>Food insecurity differs from one district and year to another. R² shows how much of that difference the model accounts for. At 100%, it would explain everything. At 0%, it would be no better than giving every district the national average. Higher is better.</p>
          </Part>
          <Part title="Where we stand">
            <p>The model explains about {percent(r.r2)} of the differences across the test years, and {percent(surveys.regression.r2)} on real surveys alone.</p>
          </Part>
          <Part title="How to use it">
            <p>This tells you the model is picking up real differences between places and years, which is what you need to compare districts. The part it does not explain is also real: local shocks and conditions that are not in our data can move a district in ways the model cannot see.</p>
          </Part>
        </>
      ),
    },
    {
      id: 'baseline', name: 'Compared with the last survey', value: `${num(test.last_survey.mae, 2)} pts`,
      body: (
        <>
          <Part title="What it tells you">
            <p>The simplest forecast needs no model at all: assume each district is the same as at its last survey. We use that as our benchmark. A model only earns its place if it beats this.</p>
          </Part>
          <Part title="Where we stand">
            <p>Copying the last survey gives an average error of {num(test.last_survey.mae, 2)} points; the model gives {num(mae, 2)}. On real surveys the gap is wider: {num(surveys.last_survey.mae, 2)} against {num(surveys.regression.mae, 2)} points.</p>
          </Part>
          <Part title="How to use it">
            <p>This is the clearest evidence that the model adds value when estimating the percentage. It gives you an updated estimate between surveys, which come only every few years, instead of relying on an ageing number.</p>
          </Part>
        </>
      ),
    },
    {
      id: 'accuracy', name: 'Accuracy', value: percent(c.accuracy),
      body: (
        <>
          <Part title="What it tells you">
            <p>We place each estimate in a class: Low (below 15%), Medium (15–30%) or High (30% or more). Accuracy is the share of districts placed in the correct class. Higher is better.</p>
          </Part>
          <Part title="Where we stand">
            <p>The model places about {Math.round(c.accuracy * 10)} in 10 districts in the correct class ({percent(c.accuracy)}).</p>
          </Part>
          <Part title="How to use it">
            <p>Accuracy is a useful first impression, but it should not be read alone. Most districts are Medium, so a model can score well here and still struggle with the rarer classes. The High class matters most for early warning, so continue to precision and recall.</p>
          </Part>
        </>
      ),
    },
    {
      id: 'precision', name: 'Precision', value: percent(c.macro.precision),
      body: (
        <>
          <Part title="What it tells you">
            <p>When the model names a class, how often is it right? Think of it as a measure of false alarms. Higher is better.</p>
          </Part>
          <Part title="Where we stand">
            <p>For the High class, precision is {percent(high.precision)}: of the {high.predicted} districts it flagged as High, {high.correct} really were. For Low, it is {percent(low.precision)}.</p>
          </Part>
          <Part title="How to use it">
            <p>Low precision would mean attention and resources going to places that did not need them. A High label from this model is a strong signal that deserves prompt attention, but it should still be checked with people on the ground.</p>
          </Part>
        </>
      ),
    },
    {
      id: 'recall', name: 'Recall', value: percent(c.macro.recall),
      body: (
        <>
          <Part title="What it tells you">
            <p>Of all the districts truly in a class, how many did the model find? Think of it as a measure of missed cases. Higher is better.</p>
          </Part>
          <Part title="Where we stand">
            <p>For the High class, recall is {percent(high.recall)}: the model found {high.correct} of the {high.observed} districts that were truly High, and missed {missed}. This is the weakest part of its performance.</p>
          </Part>
          <Part title="How to use it">
            <p>For an early warning tool, this is the measure to keep in mind, because a missed district receives no warning. In practice: <b>do not wait for a High label</b>. A Medium district with an estimate close to 30% could well be High, so treat it as a warning too.</p>
          </Part>
        </>
      ),
    },
    {
      id: 'f1', name: 'F1', value: percent(c.macro.f1),
      body: (
        <>
          <Part title="What it tells you">
            <p>F1 combines precision and recall into one score. It is high only when both are good, so a model cannot look strong by flagging every district, or by flagging almost none. Higher is better.</p>
          </Part>
          <Part title="Where we stand">
            <p>For the High class, F1 is {percent(high.f1)}, from a precision of {percent(high.precision)} and a recall of {percent(high.recall)}. The score is held back by the missed cases.</p>
          </Part>
          <Part title="How to use it">
            <p>Use F1 as a quick summary when comparing classes or test periods. For a decision, go back to precision and recall, because a false alarm and a missed district have very different costs.</p>
          </Part>
        </>
      ),
    },
    {
      id: 'auc', name: 'ROC-AUC', value: percent(c.macro.roc_auc),
      body: (
        <>
          <Part title="What it tells you">
            <p>This measures how well the model puts districts in the right order. Take one district that is truly High and one that is not: ROC-AUC is the chance that the model gives the High district the stronger signal. 50% is a coin toss; 100% is perfect.</p>
          </Part>
          <Part title="Where we stand">
            <p>For the High class it is {percent(high.roc_auc)}. So even when a district's label is wrong, the model usually still ranks it above the districts that are less at risk.</p>
          </Part>
          <Part title="How to use it">
            <p>This is the model's greatest strength for planning. When you have limited time and resources, sort the districts by their estimate and start from the top, rather than looking only at those labelled High.</p>
          </Part>
        </>
      ),
    },
    {
      id: 'practice', name: 'Using this in practice',
      body: (
        <>
          <p className="text-[15px] leading-7 text-gray-700">Taken together, these results suggest a simple way of working with the model.</p>
          <Part title="Our guidance">
            <ol className="list-decimal space-y-3 pl-5">
              <li><b>Rank first.</b> Sort districts by their estimate and start at the top. This is what the model does best.</li>
              <li><b>Look beyond the label.</b> Treat districts close to 30% as a warning, because the model tends to place High districts in Medium.</li>
              <li><b>Read a range.</b> Allow about 5 to 6 points either side of a forecast.</li>
              <li><b>Confirm locally.</b> Check priority districts with field teams and recent market information. The model cannot see sudden local shocks.</li>
              <li><b>Update your view.</b> Revisit the estimates as new harvest, price and rainfall data arrive, and when each new survey is published.</li>
            </ol>
          </Part>
          <Part title="What the model cannot do">
            <p>It estimates one value per year for each district. It does not forecast month by month, and it shows associations in the data, not proven causes.</p>
          </Part>
        </>
      ),
    },
  ]
}

/** A button that opens a guide to the metrics: one topic at a time, in a scrollable reader. */
export default function MetricGuide({ sets }: { sets: EvaluationSet[] }) {
  const [open, setOpen] = useState(false)
  const [index, setIndex] = useState(0)
  const pane = useRef<HTMLDivElement>(null)
  const test = sets.find((s) => s.key === 'test')
  const surveys = sets.find((s) => s.key === 'surveys')

  useEffect(() => { pane.current?.scrollTo({ top: 0 }) }, [index])
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false) }
    window.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => { window.removeEventListener('keydown', onKey); document.body.style.overflow = '' }
  }, [open])

  if (!test || !surveys) return null
  const list = topics(test, surveys)
  const topic = list[index]

  return (
    <>
      <div className="card flex flex-wrap items-center justify-between gap-4 border-emerald-200 bg-emerald-50/60 p-5">
        <div className="flex min-w-0 items-start gap-3">
          <div className="rounded-lg bg-white p-2 text-brand shadow-sm"><BookOpen className="h-5 w-5" /></div>
          <div className="min-w-0">
            <h2 className="text-sm font-semibold text-gray-900">What do these results mean for your decisions?</h2>
            <p className="mt-0.5 text-sm text-gray-600">A short guide that explains each measure in plain language, one at a time.</p>
          </div>
        </div>
        <button className="btn-primary" onClick={() => { setIndex(0); setOpen(true) }}>
          Read the guide <ArrowRight className="h-4 w-4" />
        </button>
      </div>

      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-0 md:p-6" role="dialog" aria-modal="true" aria-label="Guide to the model's results"
          onClick={(e) => { if (e.target === e.currentTarget) setOpen(false) }}>
          <div className="flex h-full w-full max-w-5xl flex-col overflow-hidden bg-white shadow-xl md:h-[85vh] md:rounded-2xl">
            <header className="flex items-center justify-between border-b border-gray-200 px-5 py-3">
              <h2 className="flex items-center gap-2 text-sm font-semibold text-gray-900"><BookOpen className="h-4 w-4 text-brand" /> Understanding the model's results</h2>
              <button onClick={() => setOpen(false)} aria-label="Close the guide" className="rounded-md p-1 text-gray-500 hover:bg-gray-100"><X className="h-5 w-5" /></button>
            </header>

            <div className="flex min-h-0 flex-1">
              <nav className="hidden w-60 shrink-0 overflow-y-auto border-r border-gray-100 bg-gray-50 p-2 md:block">
                {list.map((t, i) => (
                  <button key={t.id} onClick={() => setIndex(i)}
                    className={`mb-0.5 flex w-full items-center justify-between gap-2 rounded-lg px-3 py-2 text-left text-sm ${i === index ? 'bg-sidebar font-medium text-white' : 'text-gray-700 hover:bg-gray-200/60'}`}>
                    <span>{t.name}</span>
                    {t.value && <span className={`shrink-0 text-xs tabular-nums ${i === index ? 'text-emerald-100' : 'text-gray-400'}`}>{t.value}</span>}
                  </button>
                ))}
              </nav>

              <div ref={pane} className="min-w-0 flex-1 overflow-y-auto px-6 py-6 md:px-10">
                <p className="text-xs font-medium text-gray-400">{index + 1} of {list.length}</p>
                <div className="mt-1 flex flex-wrap items-baseline justify-between gap-3">
                  <h2 className="text-xl font-semibold text-gray-900">{topic.name}</h2>
                  {topic.value && <span className="text-2xl font-semibold tabular-nums text-brand-dark">{topic.value}</span>}
                </div>
                <div className="mt-3 max-w-2xl pb-4">{topic.body}</div>
              </div>
            </div>

            <footer className="flex items-center justify-between gap-3 border-t border-gray-200 px-5 py-3">
              <button className="btn-secondary disabled:cursor-not-allowed disabled:opacity-40" disabled={index === 0} onClick={() => setIndex(index - 1)}>
                <ArrowLeft className="h-4 w-4" /> Previous
              </button>
              <div className="hidden gap-1 sm:flex" aria-hidden>
                {list.map((t, i) => <span key={t.id} className={`h-1.5 w-1.5 rounded-full ${i === index ? 'bg-brand' : 'bg-gray-300'}`} />)}
              </div>
              {index < list.length - 1 ? (
                <button className="btn-primary" onClick={() => setIndex(index + 1)}>Next: {list[index + 1].name} <ArrowRight className="h-4 w-4" /></button>
              ) : (
                <button className="btn-primary" onClick={() => setOpen(false)}>Finish</button>
              )}
            </footer>
          </div>
        </div>
      )}
    </>
  )
}
