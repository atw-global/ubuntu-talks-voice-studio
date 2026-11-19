export type Cue = {
  cue: number
  speaker: string
  text: string
  meaning?: string
  start: number
  end: number
}

export type Manifest = {
  version: string
  duration_seconds: number
  cue_count?: number
  instructor_english_audio: boolean
  commercial_release: boolean
  cues: Cue[]
}

export type Activity = {
  id: string
  type: 'choice' | 'match' | 'order' | 'self_check'
  prompt: string
  choices?: string[]
  correct?: number
  pairs?: { zu: string; en: string }[]
  items?: string[]
  success?: string
  retry?: string
  note?: string
  replay_text?: string
  pronunciation_graded?: boolean
}

export type StagePayload = {
  id: string
  title: string
  intent: string
  free: boolean
  activities: Activity[]
  pronunciation_graded?: boolean
}

export type StageInfo = {
  id: string
  index: number
  title: string
  free: boolean
  intent: string
}

export type LessonInfo = {
  id: string
  title: string
  state: 'open' | 'not_authored'
}

export type Access = {
  enrolled: boolean
  commercial_release: boolean
  price_usd: string
  checkout_url: string
  course_id: string
  lesson_id: string
  product_id: string
  plan_id: string
  audio_kind: 'mp3'
  instructor_audio: boolean
  lessons: LessonInfo[]
  stages: StageInfo[]
}

export type LockedStage = {
  error: 'enrollment_required'
  stage: string
  checkout_url: string
  price_usd: string
  plan_id: string
  commercial_release: boolean
  message: string
}
