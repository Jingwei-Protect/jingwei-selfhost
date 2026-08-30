/**
 * Memory-budget helpers for Protect placement / preview.
 * Run: npx tsx src/lib/protectMemory.test.ts
 */
import assert from 'node:assert/strict'
import {
  COMPARISON_MAX_EDGE,
  EDITOR_HISTORY_MAX,
  EDITOR_MASK_MAX_EDGE,
  isRevocableObjectUrl,
  placementOnlySnapshot,
  pushCappedHistory,
  shouldSnapshotMasks,
  workingCanvasSize,
} from './protectMemory.ts'

assert.equal(EDITOR_MASK_MAX_EDGE, 1024)
assert.equal(EDITOR_HISTORY_MAX, 20)
assert.equal(COMPARISON_MAX_EDGE, 960)

assert.deepEqual(workingCanvasSize(2560, 2560), { w: 1024, h: 1024 })
assert.deepEqual(workingCanvasSize(2560, 1440), { w: 1024, h: 576 })
assert.deepEqual(workingCanvasSize(800, 600), { w: 800, h: 600 })
assert.deepEqual(workingCanvasSize(0, 10), { w: 0, h: 0 })

assert.equal(shouldSnapshotMasks('move'), false)
assert.equal(shouldSnapshotMasks('add'), false)
assert.equal(shouldSnapshotMasks('delete'), false)
assert.equal(shouldSnapshotMasks('resize'), false)
assert.equal(shouldSnapshotMasks('erase'), true)
assert.equal(shouldSnapshotMasks('blur'), true)

const place = placementOnlySnapshot([{ x: 0.5, y: 0.5 }])
assert.equal(place.mask, null)
assert.equal(place.blur, null)
assert.equal(place.eraseExport, null)

const first = pushCappedHistory([], -1, placementOnlySnapshot(['a']), 3)
assert.equal(first.index, 0)
assert.equal(first.history.length, 1)
const second = pushCappedHistory(first.history, first.index, placementOnlySnapshot(['b']), 3)
const third = pushCappedHistory(second.history, second.index, placementOnlySnapshot(['c']), 3)
const fourth = pushCappedHistory(third.history, third.index, placementOnlySnapshot(['d']), 3)
assert.equal(fourth.history.length, 3)
assert.deepEqual(fourth.history.map(e => e.placements), [['b'], ['c'], ['d']])
assert.equal(fourth.index, 2)

assert.equal(isRevocableObjectUrl('blob:http://127.0.0.1/abc'), true)
assert.equal(isRevocableObjectUrl('data:image/png;base64,xx'), false)
assert.equal(isRevocableObjectUrl(null), false)

console.log('protectMemory.test.ts: ok')
