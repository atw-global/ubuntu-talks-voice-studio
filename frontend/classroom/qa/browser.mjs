import { chromium } from 'playwright'
import { mkdir, writeFile } from 'node:fs/promises'

const out = '/opt/cursor/artifacts/classroom'
const base = 'http://127.0.0.1:4177/ubuntu-isizulu-beginner-i-classroom.html'
const results = []
await mkdir(out, { recursive: true })

function record(name, ok, detail) {
  results.push({ name, ok, detail })
  console.log(`${ok ? 'PASS' : 'FAIL'} ${name} — ${detail}`)
}

const browser = await chromium.launch({ headless: true })
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const pageErrors = []
const consoleErrors = []
page.on('pageerror', (error) => pageErrors.push(String(error)))
page.on('console', (msg) => {
  if (msg.type() === 'error') consoleErrors.push(msg.text())
})

await page.goto(base, { waitUntil: 'domcontentloaded' })
await page.locator('.hero-banner').waitFor()
await page.getByRole('heading', { name: "Greetings & Respect" }).waitFor()
record('mount', true, 'classroom shell mounted')

const hero = await page.evaluate(() => {
  const banner = document.querySelector('.hero-banner')
  const writing = document.querySelector('.hero-writing')
  const image = document.querySelector('.hero-visual img')
  const columns = getComputedStyle(banner).gridTemplateColumns.split(' ').map(parseFloat)
  const writingBox = writing.getBoundingClientRect()
  const bannerBox = banner.getBoundingClientRect()
  const textMid = writingBox.top + writingBox.height / 2
  const bannerMid = bannerBox.top + bannerBox.height / 2
  const fit = getComputedStyle(image)
  const css = [...document.styleSheets].flatMap((sheet) => {
    try { return [...sheet.cssRules].map((rule) => rule.cssText) } catch { return [] }
  }).join('\n')
  return {
    columns,
    ratio: columns[1] / columns[0],
    centered: Math.abs(textMid - bannerMid),
    writingHeight: writingBox.height,
    objectFit: fit.objectFit,
    objectPosition: fit.objectPosition,
    stripe: css.includes('repeating-linear-gradient'),
    kicker: document.querySelector('.hero-kicker')?.textContent,
    lead: document.querySelector('.hero-lead')?.textContent,
    overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
  }
})
record('banner-ratio', hero.ratio > 1.45 && hero.ratio < 1.85, `artwork/green ${hero.ratio.toFixed(2)} columns ${hero.columns.map((n) => Math.round(n)).join(' ')}`)
record('banner-center', hero.centered < hero.writingHeight * 0.08, `text block offset ${hero.centered.toFixed(1)}px`)
record('banner-copy', hero.kicker === 'Ubuntu Talks · Everyday isiZulu' && hero.lead?.includes('Language connects us'), hero.kicker + ' | ' + hero.lead)
record('banner-image', hero.objectFit === 'cover' && !hero.stripe, `${hero.objectFit} ${hero.objectPosition} stripe=${hero.stripe}`)
record('no-page-overflow-1440', hero.overflow <= 1, `overflow ${hero.overflow}px`)
await page.screenshot({ path: `${out}/hero-1440.png` })
await page.setViewportSize({ width: 390, height: 844 })
await page.screenshot({ path: `${out}/hero-390.png` })
await page.setViewportSize({ width: 768, height: 900 })
await page.screenshot({ path: `${out}/hero-768.png` })
await page.setViewportSize({ width: 1440, height: 900 })

await page.getByRole('button', { name: 'Play lesson audio' }).click()
await page.waitForTimeout(700)
const playing = await page.evaluate(() => {
  const audio = document.querySelector('audio')
  return { paused: audio.paused, time: audio.currentTime, error: audio.error && audio.error.code }
})
record('audio-play', playing.paused === false && playing.time > 0 && !playing.error, JSON.stringify(playing))

await page.getByRole('button', { name: 'Pause audio' }).click()
const pausedAt = await page.evaluate(() => document.querySelector('audio').currentTime)
await page.getByRole('button', { name: 'Play lesson audio' }).click()
await page.waitForTimeout(300)
const resumed = await page.evaluate(() => {
  const audio = document.querySelector('audio')
  return { paused: audio.paused, time: audio.currentTime }
})
record('audio-resume', resumed.paused === false && resumed.time + 0.05 >= pausedAt, JSON.stringify({ pausedAt, resumed }))

await page.locator('.dialogue-card', { hasText: 'Sanibonani.' }).first().click()
await page.waitForTimeout(250)
const sought = await page.evaluate(() => document.querySelector('audio').currentTime)
record('dialogue-seek', sought > 0.4, `currentTime ${sought.toFixed(2)}`)
const active = await page.locator('.dialogue-card.is-active strong').innerText()
record('dialogue-highlight', active === 'Sanibonani.', active)

await page.locator('.choice', { hasText: 'Sawubona.' }).click()
await page.getByRole('button', { name: 'Check answer' }).click()
await page.getByText('Sawubona greets one person. Listen again for the group form.').waitFor()
record('wrong-answer-feedback', true, 'group question explains the one-person form')
await page.locator('.choice', { hasText: 'Sanibonani.' }).click()
await page.getByRole('button', { name: 'Check answer' }).click()
await page.getByRole('button', { name: 'Next' }).click()
await page.locator('.choice', { hasText: 'Sawubona.' }).click()
await page.getByRole('button', { name: 'Check answer' }).click()
await page.getByRole('button', { name: 'Next' }).click()
await page.locator('.choice', { hasText: 'Ngiyaphila.' }).click()
await page.getByRole('button', { name: 'Check answer' }).click()
await page.getByRole('button', { name: 'See what to practise' }).click()
await page.getByRole('button', { name: 'Save this stage on this device' }).click()
await page.getByText('1 of 7 saved on this device').waitFor()
record('free-activity', true, 'three checks saved Hear on this device')

await page.getByRole('button', { name: /Understand/ }).click()
await page.getByRole('dialog', { name: 'Continue with enrollment' }).waitFor()
const checkout = await page.getByRole('link', { name: /checkout/ }).getAttribute('href')
record('locked-stage', checkout === 'https://whop.com/checkout/plan_KhrZ8JGb2YWRt', checkout)
await page.screenshot({ path: `${out}/enrollment-1440.png` })
await page.getByRole('button', { name: 'Stay in the lesson' }).click()

const shots = [
  [1440, 900, 'desktop-1440.png'],
  [1024, 800, 'tablet-1024.png'],
  [768, 900, 'tablet-768.png'],
  [390, 844, 'phone-390.png'],
  [360, 740, 'phone-360.png'],
]
for (const [width, height, name] of shots) {
  await page.setViewportSize({ width, height })
  await page.waitForTimeout(150)
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
  record(`overflow-${width}`, overflow <= 1, `overflow ${overflow}px`)
  await page.screenshot({ path: `${out}/${name}`, fullPage: false })
}
await page.setViewportSize({ width: 390, height: 844 })
await page.evaluate(() => window.scrollTo(0, 0))
await page.locator('.menu-button').click()
await page.waitForFunction(() => document.querySelector('.sidebar')?.classList.contains('sidebar-open'))
await page.waitForTimeout(250)
const drawer = await page.locator('.sidebar').boundingBox()
await page.screenshot({ path: `${out}/mobile-menu-390.png` })
record('mobile-menu', !!drawer && drawer.x >= -1 && drawer.x < 30, JSON.stringify(drawer))

const banned = await page.evaluate(() => document.body.innerText.toLowerCase())
record('no-banned-words', !/excerpt|trial|demo|experience the first/.test(banned), 'learner-visible copy checked')
record('mrs-ubuntu', banned.includes("i'm mrs ubuntu"), 'guide copy is present')
const unexpected = consoleErrors.filter((line) => !line.includes('403'))
record('console', pageErrors.length === 0 && unexpected.length === 0, JSON.stringify({ pageErrors, consoleErrors }))

await writeFile(`${out}/results.json`, JSON.stringify({ hero, results }, null, 2))
await browser.close()
if (results.some((item) => !item.ok)) process.exit(1)
