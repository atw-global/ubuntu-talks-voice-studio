import assert from 'node:assert/strict'
import { activeCueIndex } from '../src/cueSync.ts'

const cues = [
  { start: 0, end: 0.5 },
  { start: 0.3, end: 0.9 },
  { start: 1.2, end: 1.6 },
]

assert.equal(activeCueIndex(cues, 0.2), 0)
assert.equal(activeCueIndex(cues, 0.4), 0, 'an early next start does not steal the current line')
assert.equal(activeCueIndex(cues, 0.7), 1)
assert.equal(activeCueIndex(cues, 1.0), 1, 'the pause keeps the line that just finished')
assert.equal(activeCueIndex(cues, 1.25), 2)
console.log('cue sync ok')
