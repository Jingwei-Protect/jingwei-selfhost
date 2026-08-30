/** Long-edge limit for uploads — keeps backend numpy/OpenBLAS memory in check. */
export const MAX_UPLOAD_EDGE = 2560

const HEIC_TYPES = new Set([
  'image/heic',
  'image/heif',
  'image/heic-sequence',
  'image/heif-sequence',
])

export type ImageUploadCopy = {
  errors: {
    heic: string
    decode: string
    preprocessFailed: string
    canvasFailed: string
    compressFailed: string
  }
  resizeNotice: {
    joiner: string
    normalized: string
    resized: string
  }
}

function looksLikeHeic(file: File): boolean {
  const t = file.type.toLowerCase()
  if (HEIC_TYPES.has(t)) return true
  const name = file.name.toLowerCase()
  return name.endsWith('.heic') || name.endsWith('.heif')
}

function fmt(template: string, vars: Record<string, string | number>) {
  return Object.entries(vars).reduce((s, [k, v]) => s.replace(`{${k}}`, String(v)), template)
}

/** Map browser decode failures (createImageBitmap) to actionable copy. */
export function formatImageDecodeError(file: File, err: unknown, copy: ImageUploadCopy): string {
  if (looksLikeHeic(file)) {
    return copy.errors.heic
  }
  const msg = err instanceof Error ? err.message : ''
  if (/could not be decoded|decode/i.test(msg)) {
    return copy.errors.decode
  }
  return msg || copy.errors.preprocessFailed
}

export interface PreparedImage {
  file: File
  resized: boolean
  originalWidth: number
  originalHeight: number
  width: number
  height: number
  /** True when the file was re-encoded via canvas (fixes some mobile JPEG decode issues). */
  normalized: boolean
}

function outputType(file: File): { mime: string; ext: string } {
  if (file.type === 'image/png') return { mime: 'image/png', ext: 'png' }
  if (file.type === 'image/webp') return { mime: 'image/webp', ext: 'webp' }
  return { mime: 'image/jpeg', ext: 'jpg' }
}

/** Decode via <img> + canvas when createImageBitmap fails (common on mobile JPEG). */
async function decodeViaCanvas(file: File): Promise<{
  width: number
  height: number
  draw: (ctx: CanvasRenderingContext2D, w: number, h: number) => void
}> {
  const url = URL.createObjectURL(file)
  try {
    const img = await new Promise<HTMLImageElement>((resolve, reject) => {
      const el = new Image()
      el.onload = () => resolve(el)
      el.onerror = () => reject(new Error('The source image could not be decoded.'))
      el.src = url
    })
    const width = img.naturalWidth
    const height = img.naturalHeight
    if (!width || !height) {
      throw new Error('The source image could not be decoded.')
    }
    return {
      width,
      height,
      draw: (ctx, w, h) => {
        ctx.drawImage(img, 0, 0, w, h)
      },
    }
  } finally {
    URL.revokeObjectURL(url)
  }
}

async function loadDrawSource(file: File, copy: ImageUploadCopy): Promise<{
  width: number
  height: number
  draw: (ctx: CanvasRenderingContext2D, w: number, h: number) => void
  close: () => void
  normalized: boolean
}> {
  try {
    const bitmap = await createImageBitmap(file)
    return {
      width: bitmap.width,
      height: bitmap.height,
      draw: (ctx, w, h) => ctx.drawImage(bitmap, 0, 0, w, h),
      close: () => bitmap.close(),
      normalized: false,
    }
  } catch (primaryErr) {
    try {
      const via = await decodeViaCanvas(file)
      return { ...via, close: () => {}, normalized: true }
    } catch {
      throw new Error(formatImageDecodeError(file, primaryErr, copy))
    }
  }
}

async function canvasToFile(
  file: File,
  width: number,
  height: number,
  draw: (ctx: CanvasRenderingContext2D, w: number, h: number) => void,
  copy: ImageUploadCopy,
): Promise<File> {
  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error(copy.errors.canvasFailed)
  draw(ctx, width, height)

  const { mime, ext } = outputType(file)
  const quality = mime === 'image/jpeg' ? 0.92 : undefined
  const blob = await new Promise<Blob>((resolve, reject) => {
    canvas.toBlob(
      b => (b ? resolve(b) : reject(new Error(copy.errors.compressFailed))),
      mime,
      quality,
    )
  })
  const baseName = file.name.replace(/\.[^.]+$/, '') || 'upload'
  return new File([blob], `${baseName}.${ext}`, { type: mime })
}

/** Downscale large images before API upload; re-encodes when browser cannot decode in-place. */
export async function prepareImageForUpload(
  file: File,
  copy: ImageUploadCopy,
  maxEdge = MAX_UPLOAD_EDGE,
): Promise<PreparedImage> {
  const src = await loadDrawSource(file, copy)
  try {
    const originalWidth = src.width
    const originalHeight = src.height
    const longEdge = Math.max(originalWidth, originalHeight)
    const needsResize = longEdge > maxEdge
    const needsNormalize = src.normalized

    if (!needsResize && !needsNormalize) {
      return {
        file,
        resized: false,
        normalized: false,
        originalWidth,
        originalHeight,
        width: originalWidth,
        height: originalHeight,
      }
    }

    const scale = needsResize ? maxEdge / longEdge : 1
    const width = Math.round(originalWidth * scale)
    const height = Math.round(originalHeight * scale)
    const uploadFile = await canvasToFile(file, width, height, src.draw, copy)

    return {
      file: uploadFile,
      resized: needsResize,
      normalized: needsNormalize,
      originalWidth,
      originalHeight,
      width,
      height,
    }
  } finally {
    src.close()
  }
}

export function formatResizeNotice(prepared: PreparedImage, copy: ImageUploadCopy): string {
  const parts: string[] = []
  if (prepared.normalized) {
    parts.push(copy.resizeNotice.normalized)
  }
  if (prepared.resized) {
    parts.push(fmt(copy.resizeNotice.resized, {
      ow: prepared.originalWidth,
      oh: prepared.originalHeight,
      w: prepared.width,
      h: prepared.height,
    }))
  }
  return parts.join(copy.resizeNotice.joiner)
}
