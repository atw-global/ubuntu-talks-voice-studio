import { useEffect, useRef, useState } from 'react'
import { SAMPLE, loadManifest } from './api'
import { activeCueIndex } from './cueSync'
import type { Manifest } from './types'

export function useLessonAudio(retryToken: number) {
  const audioRef = useRef<HTMLAudioElement>(null)
  const railRef = useRef<HTMLDivElement>(null)
  const cardRefs = useRef<Array<HTMLButtonElement | null>>([])
  const [manifest, setManifest] = useState<Manifest | null>(null)
  const [status, setStatus] = useState('Loading the lesson audio…')
  const [error, setError] = useState(false)
  const [playing, setPlaying] = useState(false)
  const [ended, setEnded] = useState(false)
  const [time, setTime] = useState(0)
  const [active, setActive] = useState(0)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    let cancel = false
    async function load(attempt: number) {
      try {
        const body = await loadManifest()
        if (cancel) return
        setManifest(body)
        setReady(true)
        setError(false)
        setStatus('Ready. The highlighted line follows the recording.')
      } catch {
        if (cancel) return
        if (attempt < 1) {
          setStatus('The lesson service is waking. Trying once more…')
          await new Promise((resolve) => setTimeout(resolve, 2500))
          if (!cancel) await load(1)
          return
        }
        setReady(false)
        setError(true)
        setStatus('The lesson audio did not load. Try again.')
      }
    }
    setReady(false)
    setManifest(null)
    void load(0)
    return () => { cancel = true }
  }, [retryToken])

  useEffect(() => {
    if (!manifest) return
    const next = activeCueIndex(manifest.cues, time)
    if (next !== active) setActive(next)
  }, [time, manifest, active])

  useEffect(() => {
    const rail = railRef.current
    const card = cardRefs.current[active]
    if (!rail || !card) return
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const target = card.offsetLeft - (rail.clientWidth - card.offsetWidth) / 2
    rail.scrollTo({ left: Math.max(0, target), behavior: reduce || !playing ? 'auto' : 'smooth' })
  }, [active, playing])

  useEffect(() => {
    const rail = railRef.current
    if (!rail) return
    const onWheel = (event: WheelEvent) => {
      if (rail.scrollWidth <= rail.clientWidth) return
      if (Math.abs(event.deltaY) <= Math.abs(event.deltaX)) return
      event.preventDefault()
      rail.scrollLeft += event.deltaY
    }
    rail.addEventListener('wheel', onWheel, { passive: false })
    return () => rail.removeEventListener('wheel', onWheel)
  }, [ready])

  useEffect(() => {
    if (!playing) return
    let frame = 0
    const tick = () => {
      const node = audioRef.current
      if (node) setTime(node.currentTime)
      frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [playing])

  async function toggle() {
    const audio = audioRef.current
    if (!audio) return
    if (!audio.paused) {
      audio.pause()
      return
    }
    try {
      setError(false)
      setEnded(false)
      setStatus('Playing the greetings.')
      await audio.play()
    } catch {
      setError(true)
      setStatus('Press play again once the recording is ready.')
    }
  }

  async function jump(start: number, index: number) {
    const audio = audioRef.current
    if (!audio) return
    audio.currentTime = start
    setEnded(false)
    setTime(start)
    setActive(index)
    try {
      await audio.play()
    } catch {
      setStatus('Press play to start the selected phrase.')
    }
  }

  function seek(value: number) {
    const audio = audioRef.current
    if (audio) audio.currentTime = value
    setTime(value)
  }

  function replayText(text: string) {
    if (!manifest) return
    const index = manifest.cues.findIndex((cue) => cue.text === text)
    if (index < 0) return
    void jump(manifest.cues[index].start, index)
  }

  const events = {
    onTimeUpdate: (event: React.SyntheticEvent<HTMLAudioElement>) => setTime(event.currentTarget.currentTime),
    onPlay: () => { setPlaying(true); setEnded(false) },
    onPause: () => setPlaying(false),
    onEnded: () => {
      setPlaying(false)
      setEnded(true)
      setStatus('You have heard the greetings. Try them yourself.')
    },
    onError: () => {
      setError(true)
      setPlaying(false)
      setStatus('The recording stopped. Press play to try again.')
    },
  }

  return {
    audioRef,
    railRef,
    cardRefs,
    manifest,
    status,
    error,
    playing,
    ended,
    time,
    active,
    ready,
    src: ready ? SAMPLE + '/native-only.mp3' : undefined,
    toggle,
    jump,
    seek,
    replayText,
    events,
  }
}
