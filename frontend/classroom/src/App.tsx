import { useEffect, useId, useRef, useState, type ReactNode } from 'react'
import { HERO, isLocked, loadAccess, loadStage } from './api'
import { CourseSidebar, LearnerHeader } from './components/Shell'
import { PracticeEngine } from './components/Practice'
import { useLessonAudio } from './useLessonAudio'
import type { Access, StageInfo, StagePayload } from './types'

const PROGRESS_KEY = 'ubuntu-lesson1-progress'
const FALLBACK_STAGES: StageInfo[] = [
  { id: 'hear', index: 1, title: 'Hear', free: true, intent: 'Listen to the model greetings.' },
  { id: 'understand', index: 2, title: 'Understand', free: false, intent: 'Match meanings.' },
  { id: 'imitate', index: 3, title: 'Imitate', free: false, intent: 'Repeat aloud and compare.' },
  { id: 'manipulate', index: 4, title: 'Manipulate', free: false, intent: 'Change one-person forms to group forms.' },
  { id: 'retrieve', index: 5, title: 'Retrieve', free: false, intent: 'Recall the expression.' },
  { id: 'converse', index: 6, title: 'Converse', free: false, intent: 'Choose the fitting turn.' },
  { id: 'assess', index: 7, title: 'Assess', free: false, intent: 'Use the greetings on your own.' },
]

function clock(value: number) {
  const safe = Math.max(0, Math.floor(value || 0))
  return Math.floor(safe / 60) + ':' + String(safe % 60).padStart(2, '0')
}

export function App() {
  const [retry, setRetry] = useState(0)
  const audio = useLessonAudio(retry)
  const [access, setAccess] = useState<Access | null>(null)
  const [stage, setStage] = useState<StagePayload | null>(null)
  const [stageError, setStageError] = useState('')
  const [mobile, setMobile] = useState(false)
  const [enrollOpen, setEnrollOpen] = useState(false)
  const [tipOpen, setTipOpen] = useState(false)
  const [note, setNote] = useState('')
  const [done, setDone] = useState<string[]>(() => readProgress())
  const duration = audio.manifest?.duration_seconds || 0

  useEffect(() => {
    let cancel = false
    loadAccess()
      .then((body) => { if (!cancel) setAccess(body) })
      .catch(() => { if (!cancel) setAccess(null) })
    return () => { cancel = true }
  }, [])

  useEffect(() => {
    let cancel = false
    loadStage('hear').then((body) => {
      if (cancel || isLocked(body)) return
      setStage(body)
    }).catch(() => { if (!cancel) setStageError('The greeting challenge is waiting for the classroom service.') })
    return () => { cancel = true }
  }, [])

  async function openStage(info: StageInfo) {
    setNote('')
    setStageError('')
    if (!info.free && !access?.enrolled) {
      try {
        const body = await loadStage(info.id)
        if (isLocked(body)) {
          setEnrollOpen(true)
          return
        }
        setStage(body)
      } catch {
        setEnrollOpen(true)
      }
      return
    }
    try {
      const body = await loadStage(info.id)
      if (isLocked(body)) setEnrollOpen(true)
      else setStage(body)
    } catch {
      setStageError('That stage could not be loaded.')
    }
  }

  function markStage(id: string) {
    setDone((current) => {
      const next = current.includes(id) ? current : [...current, id]
      sessionStorage.setItem(PROGRESS_KEY, JSON.stringify(next))
      return next
    })
  }

  const stages = access?.stages?.length ? access.stages : FALLBACK_STAGES
  const activeId = stage?.id || 'hear'

  return (
    <div className="app-shell">
      <a className="skip" href="#lesson">Skip to the lesson</a>
      <CourseSidebar
        open={mobile}
        access={access}
        onClose={() => setMobile(false)}
        onLessonNote={(title) => setNote(`${title} is not in the classroom yet. Lesson 1 is the lesson you can study here.`)}
      />
      {mobile && <button type="button" className="scrim" aria-label="Close lesson menu" onClick={() => setMobile(false)} />}
      <div className="workspace">
        <LearnerHeader enrolled={!!access?.enrolled} onMenu={() => setMobile(true)} onEnroll={() => setEnrollOpen(true)} />
        <main className="page" id="lesson">
          <p className="crumb">Your classroom · Lesson 01</p>
          <section className="hero-banner" aria-label="Lesson banner">
            <div className="hero-writing">
              <p className="hero-kicker">Ubuntu Talks · Everyday isiZulu</p>
              <h1>Greetings &amp; Respect</h1>
              <p className="hero-lead">Language connects us. Your first conversation begins here.</p>
            </div>
            <div className="hero-visual">
              <img src={HERO} alt="Traditional round hut with painted geometric walls, a thatched roof, and aloes in warm evening light" />
            </div>
          </section>

          <section className="guide" aria-labelledby="mrs-ubuntu">
            <div className="guide-mark" aria-hidden="true">MU</div>
            <div>
              <p className="eyebrow">Mrs Ubuntu · your guide</p>
              <h2 id="mrs-ubuntu">Welcome. I&apos;m Mrs Ubuntu, and I&apos;ll be guiding you through today&apos;s lesson.</h2>
              <p>You&apos;ll hear Thando and Themba model each greeting. Listen carefully to how the greeting changes when speaking to one person or a group. First, listen. Then, it&apos;s your turn.</p>
              <p className="guide-note">This introduction is written guidance. Recorded isiZulu in this lesson is spoken by Thando and Themba.</p>
              <button type="button" className="text-button" onClick={() => setTipOpen(true)}>About these greetings</button>
            </div>
          </section>

          <div className="layout">
            <div className="lesson-column">
              <section className="panel" aria-labelledby="stage-title">
                <div className="panel-head">
                  <div>
                    <p className="eyebrow">{String(stages.find((item) => item.id === activeId)?.index || 1).padStart(2, '0')} / 07 · {stage?.title || 'Hear'}</p>
                    <h2 id="stage-title">{stage?.intent || 'Listen to the conversation models.'}</h2>
                  </div>
                  <span className="audio-kind">MP3</span>
                </div>

                {(activeId === 'hear' || audio.ready) && (
                  <>
                    <div className="player">
                      <button type="button" className={audio.playing ? 'play is-playing' : 'play'} disabled={!audio.ready} onClick={audio.toggle} aria-label={audio.playing ? 'Pause audio' : 'Play lesson audio'}>
                        {audio.playing ? 'Pause' : 'Play'}
                      </button>
                      <div>
                        <strong>Greetings · Thando and Themba</strong>
                        <span>{audio.ready ? `${clock(audio.time)} / ${clock(duration)}` : 'Preparing the recording…'}</span>
                      </div>
                      <input
                        className="seek"
                        type="range"
                        min={0}
                        max={duration || 1}
                        step={0.05}
                        value={Math.min(audio.time, duration || 1)}
                        disabled={!audio.ready}
                        aria-label="Seek in the lesson recording"
                        aria-valuetext={clock(audio.time)}
                        onChange={(event) => audio.seek(Number(event.target.value))}
                      />
                    </div>
                    <p className={audio.error ? 'status is-error' : 'status'} role="status">{audio.status}</p>
                    {audio.error && <button type="button" className="text-button" onClick={() => setRetry(retry + 1)}>Try the recording again</button>}
                    <div className="dialogue-label">
                      <strong>Follow the models</strong>
                      <span>The card moves with the audio</span>
                    </div>
                    <div
                      className="dialogue-strip"
                      ref={audio.railRef}
                      role="list"
                      tabIndex={0}
                      aria-label="isiZulu model phrases"
                      onKeyDown={(event) => {
                        if (!audio.manifest) return
                        if (event.key !== 'ArrowRight' && event.key !== 'ArrowLeft') return
                        event.preventDefault()
                        const next = event.key === 'ArrowRight'
                          ? Math.min(audio.manifest.cues.length - 1, audio.active + 1)
                          : Math.max(0, audio.active - 1)
                        const cue = audio.manifest.cues[next]
                        void audio.jump(cue.start, next)
                      }}
                    >
                      {audio.manifest?.cues.map((cue, index) => (
                        <button
                          key={cue.cue}
                          type="button"
                          role="listitem"
                          ref={(node) => { audio.cardRefs.current[index] = node }}
                          className={index === audio.active ? 'dialogue-card is-active' : 'dialogue-card'}
                          aria-current={index === audio.active ? 'true' : undefined}
                          onClick={() => audio.jump(cue.start, index)}
                        >
                          <span className="speaker">{cue.speaker}</span>
                          <strong lang="zu">{cue.text}</strong>
                          {cue.meaning ? <span className="meaning">{cue.meaning}</span> : null}
                        </button>
                      ))}
                      {!audio.manifest && <p className="status">The phrases appear with the verified recording.</p>}
                    </div>
                    <p className="hint">Swipe or scroll sideways. Arrow keys move between phrases.</p>
                    <audio
                      ref={audio.audioRef}
                      preload="metadata"
                      playsInline
                      src={audio.src}
                      {...audio.events}
                    />
                  </>
                )}

                {stage && <PracticeEngine stage={stage} onReplay={audio.replayText} onComplete={() => markStage(stage.id)} />}
                {stageError && <p className="status is-error" role="status">{stageError}</p>}
                {note && <p className="status" role="status">{note}</p>}
              </section>
            </div>
            <aside className="path" aria-label="Learning path">
              <p className="eyebrow">Learning path</p>
              <h2>Seven stages</h2>
              <p>Hear is open. The other stages open when a membership for this course is confirmed.</p>
              <div className="progress-rail" aria-hidden="true"><span style={{ width: `${(done.length / 7) * 100}%` }} /></div>
              <p className="progress-label">{done.length} of 7 saved on this device</p>
              <ol className="stage-list">
                {stages.map((item) => {
                  const locked = !item.free && !access?.enrolled
                  return (
                    <li key={item.id}>
                      <button
                        type="button"
                        className={item.id === activeId ? 'stage current' : locked ? 'stage locked' : 'stage'}
                        aria-current={item.id === activeId ? 'step' : undefined}
                        onClick={() => openStage(item)}
                      >
                        <span>{String(item.index).padStart(2, '0')}</span>
                        <span>
                          <strong>{item.title}</strong>
                          <small>{locked ? 'Enrollment required' : done.includes(item.id) ? 'Saved on this device' : item.intent}</small>
                        </span>
                      </button>
                    </li>
                  )
                })}
              </ol>
              <button type="button" className="path-enroll" onClick={() => setEnrollOpen(true)}>See enrollment</button>
            </aside>
          </div>
          <section className="closing">
            <div>
              <p className="eyebrow">Keep going</p>
              <h2>The next stages stay with the course.</h2>
              <p>Understand, imitate, manipulate, retrieve, converse, and assess use the same approved models.</p>
            </div>
            <button type="button" className="button button-primary" onClick={() => setEnrollOpen(true)}>Review enrollment</button>
          </section>
          <footer>Ubuntu Talks · Language connects us · Lesson 1 · MP3</footer>
        </main>
      </div>
      {tipOpen && (
        <Dialog title="One person, or a group" onClose={() => setTipOpen(false)}>
          <p>Sawubona greets one person. Sanibonani greets a group. The recording models both, and the challenge asks you to tell them apart.</p>
          <button type="button" className="button button-primary" onClick={() => setTipOpen(false)}>Continue</button>
        </Dialog>
      )}
      {enrollOpen && (
        <Dialog title="Continue with enrollment" onClose={() => setEnrollOpen(false)}>
          <p>The Hear stage and its greeting challenge are open here. Understand through Assess stay locked until Whop confirms a membership on the Everyday isiZulu plan.</p>
          <p className="commercial">The checkout is the existing one-time plan at ${access?.price_usd || '29.99'}. It is a real charge. This course is not commercially released, and the recording remains a private MP3.</p>
          <a className="button button-primary" href={access?.checkout_url || 'https://whop.com/checkout/plan_KhrZ8JGb2YWRt'}>Review ${access?.price_usd || '29.99'} checkout</a>
          <button type="button" className="button button-quiet" onClick={() => setTipOpen(true)}>A note on the greetings</button>
          <button type="button" className="button button-quiet" onClick={() => setEnrollOpen(false)}>Stay in the lesson</button>
        </Dialog>
      )}
    </div>
  )
}

function Dialog({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  const headingId = useId()
  const panel = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const node = panel.current
    const previous = document.activeElement as HTMLElement | null
    node?.querySelector<HTMLElement>('h2')?.focus()
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
      if (event.key !== 'Tab' || !node) return
      const items = [...node.querySelectorAll<HTMLElement>('a, button, input, select, textarea, [tabindex]:not([tabindex="-1"])')]
      if (!items.length) return
      const first = items[0]
      const last = items[items.length - 1]
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('keydown', onKey)
      previous?.focus()
    }
  }, [onClose])
  return (
    <div className="backdrop" onMouseDown={onClose} role="presentation">
      <div
        className="dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby={headingId}
        ref={panel}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <button type="button" className="dialog-close" aria-label="Close dialog" onClick={onClose}>×</button>
        <h2 id={headingId} tabIndex={-1}>{title}</h2>
        {children}
      </div>
    </div>
  )
}

function readProgress() {
  try {
    const parsed = JSON.parse(sessionStorage.getItem(PROGRESS_KEY) || '[]') as string[]
    return Array.isArray(parsed) ? parsed.filter((item) => typeof item === 'string') : []
  } catch {
    return []
  }
}

