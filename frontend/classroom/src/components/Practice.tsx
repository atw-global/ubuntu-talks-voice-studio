import { useEffect, useMemo, useState } from 'react'
import type { Activity, StagePayload } from '../types'

type Result = { id: string; prompt: string; ok: boolean }

function seededOrder(items: string[], seed: string) {
  const rows = items.map((item, index) => ({ item, index }))
  let hash = 0
  for (let i = 0; i < seed.length; i += 1) hash = (hash * 33 + seed.charCodeAt(i)) >>> 0
  for (let i = rows.length - 1; i > 0; i -= 1) {
    hash = (hash * 1664525 + 1013904223) >>> 0
    const swap = hash % (i + 1)
    ;[rows[i], rows[swap]] = [rows[swap], rows[i]]
  }
  return rows
}

export function PracticeEngine({
  stage,
  onComplete,
  onReplay,
  onEngage,
}: {
  stage: StagePayload
  onComplete: (results: Result[]) => void
  onReplay: (text: string) => void
  onEngage?: () => void
}) {
  const [index, setIndex] = useState(0)
  const [choice, setChoice] = useState<number | null>(null)
  const [checked, setChecked] = useState(false)
  const [order, setOrder] = useState<number[]>([])
  const [matches, setMatches] = useState<Record<number, string>>({})
  const [results, setResults] = useState<Result[]>([])
  const activity = stage.activities[index]
  const finished = index >= stage.activities.length

  useEffect(() => {
    setIndex(0)
    setChoice(null)
    setChecked(false)
    setOrder([])
    setMatches({})
    setResults([])
  }, [stage.id])

  const shuffled = useMemo(
    () => (activity?.type === 'order' && activity.items ? seededOrder(activity.items, activity.id) : []),
    [activity],
  )

  if (finished) {
    const correct = results.filter((item) => item.ok).length
    const missed = results.filter((item) => !item.ok)
    return (
      <section className="practice done" aria-label="Stage summary">
        <p className="eyebrow">Stage complete</p>
        <h3>{stage.title}</h3>
        <p className="practice-status" role="status">
          You matched {correct} of {results.length} in {stage.title}.
          {stage.id === 'imitate' ? ' Pronunciation was not scored.' : ''}
        </p>
        {missed.length > 0 && (
          <ul className="revise">
            {missed.map((item) => <li key={item.id}>Practise again: {item.prompt}</li>)}
          </ul>
        )}
        <button type="button" className="button button-primary" onClick={() => onComplete(results)}>Save this stage on this device</button>
      </section>
    )
  }

  if (!activity) return null
  const passed = isPassed(activity, choice, order, matches, shuffled)

  function check() {
    onEngage?.()
    if (activity.type === 'self_check') {
      if (choice == null) return
      setChecked(true)
      return
    }
    if (activity.type === 'order' && order.length !== shuffled.length) return
    if (activity.type === 'match' && activity.pairs && Object.keys(matches).length !== activity.pairs.length) return
    if (activity.type === 'choice' && choice == null) return
    setChecked(true)
  }

  function next() {
    const ok = activity.type === 'self_check' ? choice === 0 : passed
    const entry = { id: activity.id, prompt: activity.prompt, ok }
    if (index + 1 >= stage.activities.length) {
      setResults((current) => [...current, entry])
      setIndex(index + 1)
      return
    }
    setResults((current) => [...current, entry])
    setIndex(index + 1)
    setChoice(null)
    setChecked(false)
    setOrder([])
    setMatches({})
  }

  return (
    <section className="practice" aria-label={`${stage.title} practice`}>
      <div className="practice-top">
        <p className="eyebrow">{stage.title} · {String(index + 1).padStart(2, '0')} / {String(stage.activities.length).padStart(2, '0')}</p>
        <span>{results.filter((item) => item.ok).length} matched</span>
      </div>
      <div className="meter" aria-hidden="true"><span style={{ width: `${((index + (checked && passed ? 1 : 0)) / stage.activities.length) * 100}%` }} /></div>
      <h3>{activity.prompt}</h3>
      {activity.note && <p className="practice-note">{activity.note}</p>}
      {activity.type === 'choice' || activity.type === 'self_check' ? (
        <div className="choices">
          {activity.choices?.map((label, option) => (
            <button
              key={label}
              type="button"
              className={choice === option ? 'choice chosen' : 'choice'}
              onClick={() => { setChoice(option); setChecked(false) }}
              lang={activity.type === 'self_check' ? 'en' : 'zu'}
            >
              <span>{String.fromCharCode(65 + option)}</span>{label}
            </button>
          ))}
        </div>
      ) : null}
      {activity.type === 'match' && activity.pairs ? (
        <div className="match-list">
          {activity.pairs.map((pair, row) => (
            <label key={pair.zu}>
              <span lang="zu">{pair.zu}</span>
              <select
                value={matches[row] || ''}
                onChange={(event) => {
                  setMatches({ ...matches, [row]: event.target.value })
                  setChecked(false)
                }}
                aria-label={`Meaning of ${pair.zu}`}
              >
                <option value="">Choose the meaning</option>
                {activity.pairs?.map((item) => <option key={item.en} value={item.en}>{item.en}</option>)}
              </select>
            </label>
          ))}
        </div>
      ) : null}
      {activity.type === 'order' ? (
        <div className="order-list">
          <div className="order-bank">
            {shuffled.map((row) => (
              <button
                key={row.item}
                type="button"
                className="choice"
                disabled={order.includes(row.index)}
                onClick={() => { setOrder([...order, row.index]); setChecked(false) }}
                lang="zu"
              >{row.item}</button>
            ))}
          </div>
          <ol>
            {order.map((original, position) => (
              <li key={`${original}-${position}`} lang="zu">{activity.items?.[original]}</li>
            ))}
          </ol>
          <button type="button" className="text-button" onClick={() => { setOrder([]); setChecked(false) }}>Clear order</button>
        </div>
      ) : null}
      {checked && (
        <p className={(activity.type === 'self_check' ? choice === 0 : passed) ? 'feedback ok' : 'feedback retry'} role="status">
          {activity.type === 'self_check'
            ? (choice === 0 ? 'You noted that you could follow the greeting.' : 'Listen again and say the line once more. This check does not score your pronunciation.')
            : (passed ? (activity.success || 'Noted.') : (activity.retry || 'Try another response.'))}
        </p>
      )}
      <div className="practice-actions">
        {activity.replay_text && (
          <button type="button" className="text-button" onClick={() => onReplay(activity.replay_text || '')}>Play the greeting again</button>
        )}
        {!checked || !passed ? (
          <button type="button" className="button button-dark" onClick={check} disabled={!canCheck(activity, choice, order, matches, shuffled)}>
            {activity.type === 'self_check' ? 'Record my check' : 'Check answer'}
          </button>
        ) : (
          <button type="button" className="button button-primary" onClick={next}>
            {index + 1 === stage.activities.length ? 'See what to practise' : 'Next'}
          </button>
        )}
      </div>
    </section>
  )
}

function canCheck(activity: Activity, choice: number | null, order: number[], matches: Record<number, string>, shuffled: { index: number }[]) {
  if (activity.type === 'choice' || activity.type === 'self_check') return choice != null
  if (activity.type === 'order') return order.length === shuffled.length && shuffled.length > 0
  if (activity.type === 'match') return !!activity.pairs && Object.keys(matches).length === activity.pairs.length && activity.pairs.every((_, row) => matches[row])
  return false
}

function isPassed(activity: Activity, choice: number | null, order: number[], matches: Record<number, string>, shuffled: { index: number }[]) {
  if (activity.type === 'self_check') return choice != null
  if (activity.type === 'choice') return choice === activity.correct
  if (activity.type === 'order') return order.length === shuffled.length && order.every((value, position) => value === position)
  if (activity.type === 'match' && activity.pairs) {
    return activity.pairs.every((pair, row) => matches[row] === pair.en)
  }
  return false
}
