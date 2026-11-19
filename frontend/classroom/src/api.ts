import type { Access, LockedStage, Manifest, StagePayload } from './types'

export const SITE = 'https://ubuntu-talks.whop.site'
export const SAMPLE = '/api/ubuntu/azure/lesson1/sample'
export const CLASSROOM = '/api/ubuntu/azure/lesson1/classroom'
export const HERO = '/curriculum/lesson1-hero-hut.jpg'
export const LINKS = {
  home: SITE + '/',
  dashboard: SITE + '/dashboard',
  courses: SITE + '/my-courses',
  lessons: SITE + '/my-lessons',
  help: SITE + '/help',
  languages: SITE + '/#languages',
  about: SITE + '/about',
  contact: SITE + '/contact',
  shop: SITE + '/shop',
  signin: SITE + '/signin',
}

const MEMBERSHIP_KEY = 'ubuntu-lesson1-membership'

export function membershipId(): string {
  const stored = sessionStorage.getItem(MEMBERSHIP_KEY) || ''
  if (/^mem_[A-Za-z0-9]+$/.test(stored)) return stored
  const fromUrl = new URLSearchParams(location.search).get('membership') || ''
  if (/^mem_[A-Za-z0-9]+$/.test(fromUrl)) {
    sessionStorage.setItem(MEMBERSHIP_KEY, fromUrl)
    return fromUrl
  }
  return ''
}

function headers(): HeadersInit {
  const id = membershipId()
  return id ? { 'X-Ubuntu-Membership-Id': id } : {}
}

export function validManifest(value: Manifest): boolean {
  return value?.version === 'native-greeting-lesson01-v1'
    && value.instructor_english_audio === false
    && value.commercial_release === false
    && Array.isArray(value.cues)
    && value.cues.length >= 14
    && value.cues.every((cue) => cue.speaker === 'Thando' || cue.speaker === 'Themba')
}

export async function loadManifest(): Promise<Manifest> {
  const response = await fetch(SAMPLE + '/synced-dialogue', { credentials: 'same-origin', cache: 'no-store' })
  if (!response.ok) throw new Error('media-' + response.status)
  const body = await response.json() as Manifest
  if (!validManifest(body)) throw new Error('manifest')
  return body
}

export async function loadAccess(): Promise<Access> {
  const response = await fetch(CLASSROOM + '/access', { credentials: 'same-origin', cache: 'no-store', headers: headers() })
  if (!response.ok) throw new Error('access-' + response.status)
  return response.json() as Promise<Access>
}

export async function loadStage(id: string): Promise<StagePayload | LockedStage> {
  const response = await fetch(CLASSROOM + '/stages/' + id, { credentials: 'same-origin', cache: 'no-store', headers: headers() })
  const body = await response.json() as StagePayload | LockedStage
  if (response.status === 403) return body as LockedStage
  if (!response.ok) throw new Error('stage-' + response.status)
  return body as StagePayload
}

export function isLocked(value: StagePayload | LockedStage): value is LockedStage {
  return 'error' in value && value.error === 'enrollment_required'
}
