/**
 * Build the flash-card upload without fetch(blob:).
 *
 * Production CSP historically used ``connect-src 'self'``, which blocks
 * fetching object URLs. The protect result is already in memory as a Blob.
 */
import { dataUrlToUint8 } from '../utils/downloadDataUrl'

/** Stay under nginx 15m / app 12 MiB upload caps. */
export const HOLO_UPLOAD_MAX_BYTES = 10 * 1024 * 1024
export const HOLO_UPLOAD_MAX_EDGE = 1600

export type HoloClipSource = {
  storedBlob?: Blob | null
  displayUrl: string
}

export type HoloClipUploadOpts = {
  fetchImpl?: typeof fetch
  compress?: (blob: Blob) => Promise<Blob>
}

export function blobFromDataUrl(dataUrl: string): Blob {
  const { mime, bytes } = dataUrlToUint8(dataUrl)
  const copy = new Uint8Array(bytes.byteLength)
  copy.set(bytes)
  return new Blob([copy.buffer], { type: mime || 'image/png' })
}

export function objectUrlFromResultImage(raw: string): { url: string; blob: Blob | null } {
  if (raw.startsWith('blob:') || !raw.startsWith('data:')) {
    return { url: raw, blob: null }
  }
  const blob = blobFromDataUrl(raw)
  return { url: URL.createObjectURL(blob), blob }
}

function fileFromBlob(blob: Blob): File {
  const type = blob.type || 'image/png'
  const name = type.includes('jpeg') || type.includes('jpg') ? 'protected.jpg' : 'protected.png'
  return new File([blob], name, { type })
}

export async function fileForHoloClip(
  source: HoloClipSource,
  opts: HoloClipUploadOpts = {},
): Promise<File> {
  let blob: Blob
  if (source.storedBlob && source.storedBlob.size > 0) {
    blob = source.storedBlob
  } else if (source.displayUrl.startsWith('data:')) {
    blob = blobFromDataUrl(source.displayUrl)
  } else if (source.displayUrl.startsWith('blob:')) {
    throw new Error('client:holo_result_expired')
  } else {
    const fetchFn = opts.fetchImpl ?? fetch
    const res = await fetchFn(source.displayUrl)
    if (!res.ok) throw new Error('client:holo_result_expired')
    blob = await res.blob()
  }

  if (blob.size > HOLO_UPLOAD_MAX_BYTES) {
    if (!opts.compress) throw new Error('client:holo_too_large')
    blob = await opts.compress(blob)
  }

  return fileFromBlob(blob)
}

/** Downscale + JPEG so a huge PNG result still fits the upload cap. */
export async function jpegForHoloUpload(
  blob: Blob,
  maxEdge: number = HOLO_UPLOAD_MAX_EDGE,
): Promise<Blob> {
  const bitmap = await createImageBitmap(blob)
  try {
    const long = Math.max(bitmap.width, bitmap.height)
    const scale = long > maxEdge ? maxEdge / long : 1
    const width = Math.max(2, Math.round(bitmap.width * scale))
    const height = Math.max(2, Math.round(bitmap.height * scale))
    const canvas = document.createElement('canvas')
    canvas.width = width
    canvas.height = height
    const ctx = canvas.getContext('2d')
    if (!ctx) throw new Error('client:holo_too_large')
    ctx.drawImage(bitmap, 0, 0, width, height)
    const out = await new Promise<Blob>((resolve, reject) => {
      canvas.toBlob(
        (next) => (next ? resolve(next) : reject(new Error('client:holo_too_large'))),
        'image/jpeg',
        0.92,
      )
    })
    return out
  } finally {
    bitmap.close()
  }
}
