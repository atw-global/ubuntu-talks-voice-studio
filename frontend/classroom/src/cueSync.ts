export type TimedCue = { start: number; end: number }

/** Highlight the line being spoken. A following timestamp that lands early does not take the card. */
export function activeCueIndex(cues: TimedCue[], time: number): number {
  if (!cues.length || time < cues[0].start) return 0
  let index = 0
  for (let i = 0; i < cues.length; i++) {
    if (time < cues[i].start) break
    index = i
  }
  const previous = cues[index - 1]
  if (previous && previous.end > previous.start && time < previous.end) return index - 1
  return index
}
