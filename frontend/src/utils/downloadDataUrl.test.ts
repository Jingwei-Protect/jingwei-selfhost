/**
 * Self-test for downloadDataUrl helpers.
 * Run: npx tsx src/utils/downloadDataUrl.test.ts
 */
import assert from 'node:assert/strict'
import {
  dataUrlToUint8,
  extensionFromMime,
  resolveDownloadFilename,
} from './downloadDataUrl.ts'

assert.equal(extensionFromMime('image/png'), 'png')
assert.equal(extensionFromMime('image/jpeg'), 'jpg')
assert.equal(extensionFromMime('image/jpg'), 'jpg')
assert.equal(extensionFromMime('image/webp'), 'webp')
assert.equal(extensionFromMime('image/png;charset=utf-8'), 'png')
assert.equal(extensionFromMime('application/octet-stream'), 'bin')

const pngB64 = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='
const dataUrl = `data:image/png;base64,${pngB64}`
const parsed = dataUrlToUint8(dataUrl)
assert.equal(parsed.mime, 'image/png')
assert.ok(parsed.bytes.length > 20)
assert.equal(parsed.bytes[0], 0x89)
assert.equal(parsed.bytes[1], 0x50) // P

assert.equal(
  resolveDownloadFilename('art', 'jpg', 'image/png'),
  'art_protected.png',
  'filename must follow actual MIME, not UI format picker',
)
assert.equal(resolveDownloadFilename('art', 'png', 'image/png'), 'art_protected.png')
assert.equal(resolveDownloadFilename('my.file', 'webp', 'image/webp'), 'my.file_protected.webp')

console.log('downloadDataUrl.test.ts: ok')
