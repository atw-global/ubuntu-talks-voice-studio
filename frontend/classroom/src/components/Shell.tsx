import type { Access } from '../types'
import { HERO, LINKS, SITE } from '../api'

const FALLBACK_LESSONS = [
  { id: 'lesson-01', title: 'Sounds, Greetings & Respect', state: 'open' as const },
]

export function LearnerHeader({
  enrolled,
  onMenu,
  onEnroll,
}: {
  enrolled: boolean
  onMenu: () => void
  onEnroll: () => void
}) {
  return (
    <header className="topbar">
      <button type="button" className="menu-button" aria-label="Open lesson menu" onClick={onMenu}>☰</button>
      <a className="brand" href={LINKS.home}>Ubuntu Talks</a>
      <a className="help-link" href={LINKS.help}>Help</a>
      <nav className="site-links" aria-label="Ubuntu Talks">
        <a href={LINKS.dashboard}>My Dashboard</a>
        <a href={LINKS.courses}>My Courses</a>
        <a href="#lesson">Lesson</a>
        <a href={LINKS.help}>Help</a>
        <details className="more">
          <summary>More</summary>
          <div>
            <a href={LINKS.home}>Home</a>
            <a href={LINKS.languages}>Languages</a>
            <a href={LINKS.lessons}>My lessons</a>
            <a href={LINKS.about}>About</a>
            <a href={LINKS.contact}>Contact</a>
            <a href={LINKS.shop}>Shop</a>
            <a href={LINKS.signin}>Sign in</a>
          </div>
        </details>
      </nav>
      <button type="button" className="enroll-button" onClick={onEnroll}>
        {enrolled ? 'Enrolled' : 'Enrollment'}
      </button>
    </header>
  )
}

export function CourseSidebar({
  open,
  access,
  onClose,
  onLessonNote,
}: {
  open: boolean
  access: Access | null
  onClose: () => void
  onLessonNote: (title: string) => void
}) {
  const lessons = access?.lessons?.length ? access.lessons : FALLBACK_LESSONS
  return (
    <aside className={open ? 'sidebar sidebar-open' : 'sidebar'} aria-label="Course">
      <div className="side-brand">
        <a href={SITE + '/'} aria-label="Ubuntu Talks home">UT</a>
        <div>
          <strong>Ubuntu Talks</strong>
          <small>Everyday isiZulu</small>
        </div>
        <button type="button" className="drawer-close" aria-label="Close lesson menu" onClick={onClose}>×</button>
      </div>
      <nav className="drawer-links" aria-label="Site">
        <a href={LINKS.dashboard} onClick={onClose}>My Dashboard</a>
        <a href={LINKS.courses} onClick={onClose}>My Courses</a>
        <a href={LINKS.help} onClick={onClose}>Help</a>
        <a href={LINKS.home} onClick={onClose}>Home</a>
      </nav>
      <figure className="course-thumb">
        <img src={HERO} alt="Painted round hut with a thatched roof" />
        <figcaption><span>Beginner I</span>Everyday isiZulu</figcaption>
      </figure>
      <p className="side-kicker">Lessons</p>
      <nav className="lesson-nav" aria-label="Lessons">
        {lessons.map((lesson, index) => (
          <button
            key={lesson.id}
            type="button"
            className={lesson.state === 'open' ? 'lesson-link current' : 'lesson-link'}
            onClick={() => {
              onClose()
              if (lesson.state === 'open') document.getElementById('lesson')?.scrollIntoView({ block: 'start' })
              else onLessonNote(lesson.title)
            }}
          >
            <span>{String(index + 1).padStart(2, '0')}</span>
            <span>{lesson.title}</span>
            <span className="lesson-state">{lesson.state === 'open' ? 'Open' : 'Later'}</span>
          </button>
        ))}
      </nav>
    </aside>
  )
}
