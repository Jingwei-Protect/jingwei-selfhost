/**
 * Reliable browser downloads for protected images.
 *
 * Principle: Chrome (and some Safari builds) silently ignore
 * ``<a download href="data:...">`` when the data URL is large. Converting to a
 * Blob + object URL restores the download attribute behavior that used to work
 * for smaller outputs.
 */

export type ParsedDataUrl = {
  mime: string
  bytes: Uint8Array
}

/** Map MIME type to a short file extension. */
export function extensionFromMime(mime: string): string {
  const base = mime.toLowerCase().split(';')[0]?.trim() ?? ''
  if (base === 'image/jpeg' || base === 'image/jpg') return 'jpg'
  if (base === 'image/webp') return 'webp'
  if (base === 'image/png') return 'png'
  if (base.startsWith('image/')) return base.slice('image/'.length) || 'bin'
  return 'bin'
}

/**
 * Decode a ``data:`` URL into mime + raw bytes.
 * Supports ``;base64`` and URL-encoded payloads.
 */
export function dataUrlToUint8(dataUrl: string): ParsedDataUrl {
  const comma = dataUrl.indexOf(',')
  if (!dataUrl.startsWith('data:') || comma < 0) {
    throw new Error('Invalid data URL')
  }
  const header = dataUrl.slice(5, comma)
  const payload = dataUrl.slice(comma + 1)
  const parts = header.split(';')
  const mime = parts[0]?.trim() || 'application/octet-stream'
  const isBase64 = parts.some((p) => p.trim().toLowerCase() === 'base64')
  if (isBase64) {
    const bin = atob(payload)
    const bytes = new Uint8Array(bin.length)
    for (let i = 0; i < bin.length; i += 1) {
      bytes[i] = bin.charCodeAt(i)
    }
    return { mime, bytes }
  }
  const decoded = decodeURIComponent(payload)
  return { mime, bytes: new TextEncoder().encode(decoded) }
}

/**
 * Prefer the real image MIME over the UI format picker so a renamed
 * ``.jpg`` that is still PNG bytes does not confuse OS viewers.
 */
export function resolveDownloadFilename(
  baseName: string,
  preferredExt: string,
  mime: string,
): string {
  const safeBase = (baseName || 'protected').replace(/[\\/:*?"<>|]+/g, '_')
  const actual = extensionFromMime(mime)
  const preferred = (preferredExt || '').toLowerCase().replace(/^\./, '')
  const ext = actual !== 'bin' ? actual : preferred || 'png'
  return `${safeBase}_protected.${ext}`
}

function triggerAnchorDownload(href: string, filename: string, revoke?: string): void {
  const a = document.createElement('a')
  a.href = href
  a.download = filename
  a.rel = 'noopener'
  a.style.display = 'none'
  document.body.appendChild(a)
  a.click()
  a.remove()
  if (revoke) {
    // Defer revoke so the browser can start the download stream.
    window.setTimeout(() => URL.revokeObjectURL(revoke), 1_000)
  }
}

/**
 * Download ``url`` (data URL, blob URL, or same-origin URL) as ``filename``.
 */
export function downloadUrl(url: string, filename: string): void {
  if (url.startsWith('data:')) {
    const { mime, bytes } = dataUrlToUint8(url)
    const blob = uint8ToBlob(bytes, mime)
    const objectUrl = URL.createObjectURL(blob)
    triggerAnchorDownload(objectUrl, filename, objectUrl)
    return
  }
  triggerAnchorDownload(url, filename)
}

function uint8ToBlob(bytes: Uint8Array, mime: string): Blob {
  const copy = new Uint8Array(bytes.byteLength)
  copy.set(bytes)
  return new Blob([copy.buffer], { type: mime })
}

/**
 * Download a protected result image. Filename extension follows image MIME.
 */
export function downloadProtectedImage(
  imageUrl: string,
  baseName: string,
  preferredExt = 'png',
): void {
  if (imageUrl.startsWith('data:')) {
    const { mime, bytes } = dataUrlToUint8(imageUrl)
    const filename = resolveDownloadFilename(baseName, preferredExt, mime)
    const blob = uint8ToBlob(bytes, mime)
    const objectUrl = URL.createObjectURL(blob)
    triggerAnchorDownload(objectUrl, filename, objectUrl)
    return
  }
  const filename = resolveDownloadFilename(baseName, preferredExt, 'image/png')
  downloadUrl(imageUrl, filename)
}
