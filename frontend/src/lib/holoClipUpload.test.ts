/**
 * Flash-card upload must not fetch(blob:) — production CSP used to block it.
 * Run: npx tsx src/lib/holoClipUpload.test.ts
 */
import assert from 'node:assert/strict'
import { fileForHoloClip, HOLO_UPLOAD_MAX_BYTES } from './holoClipUpload.ts'

const pngB64 = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='
const dataUrl = `data:image/png;base64,${pngB64}`

const stored = new Blob([Uint8Array.from([0x89, 0x50, 0x4e, 0x47])], { type: 'image/png' })

let fetchCalls = 0
const bannedFetch: typeof fetch = (async () => {
  fetchCalls += 1
  throw new Error('fetch must not run for blob: result images')
}) as typeof fetch

const fromStored = await fileForHoloClip(
  { storedBlob: stored, displayUrl: 'blob:https://jwprotect.com/abc' },
  { fetchImpl: bannedFetch },
)
assert.equal(fetchCalls, 0)
assert.equal(fromStored.type, 'image/png')
assert.ok(fromStored.size > 0)

const fromData = await fileForHoloClip(
  { storedBlob: null, displayUrl: dataUrl },
  { fetchImpl: bannedFetch },
)
assert.equal(fetchCalls, 0)
assert.equal(fromData.type, 'image/png')
assert.ok(fromData.size > 20)
const dataBytes = new Uint8Array(await fromData.arrayBuffer())
assert.equal(dataBytes[0], 0x89)
assert.equal(dataBytes[1], 0x50)

await assert.rejects(
  () => fileForHoloClip(
    { storedBlob: null, displayUrl: 'blob:https://jwprotect.com/missing' },
    { fetchImpl: bannedFetch },
  ),
  (err: unknown) => err instanceof Error && err.message === 'client:holo_result_expired',
)
assert.equal(fetchCalls, 0)

const huge = new Blob([new Uint8Array(HOLO_UPLOAD_MAX_BYTES + 1)], { type: 'image/png' })
let compressed = 0
const shrunk = await fileForHoloClip(
  { storedBlob: huge, displayUrl: 'blob:https://jwprotect.com/huge' },
  {
    fetchImpl: bannedFetch,
    compress: async () => {
      compressed += 1
      return new Blob([Uint8Array.from([0xff, 0xd8, 0xff])], { type: 'image/jpeg' })
    },
  },
)
assert.equal(fetchCalls, 0)
assert.equal(compressed, 1)
assert.equal(shrunk.type, 'image/jpeg')

console.log('holoClipUpload.test.ts ok')
