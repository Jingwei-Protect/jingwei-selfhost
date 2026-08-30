/**
 * Self-test for session visit gate.
 * Run: npx tsx src/utils/sessionVisit.test.ts
 */
import assert from 'node:assert/strict'
import {
  SESSION_VISIT_KEY,
  shouldRecordVisit,
  markVisitRecorded,
} from './sessionVisit.ts'

class MemoryStorage {
  private map = new Map<string, string>()
  getItem(key: string): string | null {
    return this.map.has(key) ? this.map.get(key)! : null
  }
  setItem(key: string, value: string): void {
    this.map.set(key, value)
  }
  removeItem(key: string): void {
    this.map.delete(key)
  }
}

const storage = new MemoryStorage()
assert.equal(shouldRecordVisit(storage), true)
markVisitRecorded(storage)
assert.equal(storage.getItem(SESSION_VISIT_KEY), '1')
assert.equal(shouldRecordVisit(storage), false)

console.log('sessionVisit.test.ts: ok')
