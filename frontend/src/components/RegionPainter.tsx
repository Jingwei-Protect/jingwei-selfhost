import { useCallback, useEffect, useRef, useState } from 'react'
import { useLocale } from '../i18n/LocaleContext'

export type RegionPaintMode = 'brush' | 'rect'

interface Props {
  imageSrc: string
  mode: RegionPaintMode
  brushSize?: number
  strokeColor?: string
  onMaskChange?: (hasStroke: boolean) => void
  exportRef?: React.MutableRefObject<(() => Promise<Blob | null>) | null>
}

type Rect = { x: number; y: number; w: number; h: number }

const MAX_RECTS = 5

/** Paint a binary mask: brush strokes, or up to 5 confirmable rectangles. */
export default function RegionPainter({
  imageSrc,
  mode,
  brushSize = 28,
  strokeColor = 'rgba(59, 130, 246, 0.45)',
  onMaskChange,
  exportRef,
}: Props) {
  const { messages: m } = useLocale()
  const delLabel = m.components.regionPainter.deleteBar
  const wrapRef = useRef<HTMLDivElement>(null)
  const imgRef = useRef<HTMLImageElement>(null)
  const maskRef = useRef<HTMLCanvasElement>(null)
  const [imgSize, setImgSize] = useState({ w: 0, h: 0 })
  const drawing = useRef(false)
  const rectStart = useRef<{ x: number; y: number } | null>(null)
  // Committed rectangles (normalized 0–1) and the in-progress draft.
  const [rects, setRects] = useState<Rect[]>([])
  const [draft, setDraft] = useState<Rect | null>(null)

  const syncCanvasSize = useCallback(() => {
    const img = imgRef.current
    const mask = maskRef.current
    if (!img || !mask || !img.naturalWidth) return
    setImgSize({ w: img.naturalWidth, h: img.naturalHeight })
    mask.width = img.naturalWidth
    mask.height = img.naturalHeight
  }, [])

  useEffect(() => {
    syncCanvasSize()
  }, [imageSrc, syncCanvasSize])

  // Switching modes starts a clean slate so the two methods never mix.
  useEffect(() => {
    const mask = maskRef.current
    mask?.getContext('2d')?.clearRect(0, 0, mask.width, mask.height)
    setRects([])
    setDraft(null)
    onMaskChange?.(false)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode])

  useEffect(() => {
    onMaskChange?.(mode === 'rect' ? rects.length > 0 : false)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rects, mode])

  const toCanvas = useCallback((clientX: number, clientY: number) => {
    const wrap = wrapRef.current
    if (!wrap || !imgSize.w) return null
    const rect = wrap.getBoundingClientRect()
    return {
      x: ((clientX - rect.left) / rect.width) * imgSize.w,
      y: ((clientY - rect.top) / rect.height) * imgSize.h,
    }
  }, [imgSize.w])

  const toNorm = useCallback((clientX: number, clientY: number) => {
    const wrap = wrapRef.current
    if (!wrap) return null
    const rect = wrap.getBoundingClientRect()
    return {
      x: (clientX - rect.left) / rect.width,
      y: (clientY - rect.top) / rect.height,
    }
  }, [])

  const renderRectsToMask = useCallback((list: Rect[]) => {
    const mask = maskRef.current
    const ctx = mask?.getContext('2d')
    if (!mask || !ctx) return
    ctx.clearRect(0, 0, mask.width, mask.height)
    ctx.fillStyle = strokeColor
    for (const r of list) {
      ctx.fillRect(r.x * mask.width, r.y * mask.height, r.w * mask.width, r.h * mask.height)
    }
  }, [strokeColor])

  useEffect(() => {
    if (mode === 'rect') renderRectsToMask(rects)
  }, [rects, mode, renderRectsToMask])

  const exportMask = useCallback(async (): Promise<Blob | null> => {
    const mask = maskRef.current
    if (!mask || !imgSize.w) return null
    if (mode === 'rect') {
      if (rects.length === 0) return null
      const out = document.createElement('canvas')
      out.width = mask.width
      out.height = mask.height
      const octx = out.getContext('2d')
      if (!octx) return null
      octx.fillStyle = '#000000'
      octx.fillRect(0, 0, out.width, out.height)
      octx.fillStyle = '#ffffff'
      for (const r of rects) {
        octx.fillRect(r.x * out.width, r.y * out.height, r.w * out.width, r.h * out.height)
      }
      return new Promise(resolve => out.toBlob(b => resolve(b), 'image/png'))
    }
    const ctx = mask.getContext('2d')
    if (!ctx) return null
    const src = ctx.getImageData(0, 0, mask.width, mask.height)
    let hasStroke = false
    for (let i = 3; i < src.data.length; i += 4) {
      if (src.data[i] > 0) {
        hasStroke = true
        break
      }
    }
    if (!hasStroke) return null
    const out = document.createElement('canvas')
    out.width = mask.width
    out.height = mask.height
    const octx = out.getContext('2d')
    if (!octx) return null
    octx.fillStyle = '#000000'
    octx.fillRect(0, 0, out.width, out.height)
    const bin = octx.createImageData(out.width, out.height)
    for (let i = 0; i < src.data.length; i += 4) {
      const v = src.data[i + 3] > 0 ? 255 : 0
      bin.data[i] = v
      bin.data[i + 1] = v
      bin.data[i + 2] = v
      bin.data[i + 3] = 255
    }
    octx.putImageData(bin, 0, 0)
    return new Promise(resolve => out.toBlob(b => resolve(b), 'image/png'))
  }, [imgSize.w, mode, rects])

  useEffect(() => {
    if (exportRef) exportRef.current = exportMask
  }, [exportRef, exportMask])

  const clearAll = () => {
    const mask = maskRef.current
    mask?.getContext('2d')?.clearRect(0, 0, mask.width, mask.height)
    setRects([])
    setDraft(null)
    onMaskChange?.(false)
  }

  const paintBrush = (clientX: number, clientY: number) => {
    const mask = maskRef.current
    const wrap = wrapRef.current
    const pt = toCanvas(clientX, clientY)
    if (!mask || !wrap || !pt) return
    const rect = wrap.getBoundingClientRect()
    const ctx = mask.getContext('2d')
    if (!ctx) return
    ctx.fillStyle = strokeColor
    ctx.beginPath()
    ctx.arc(pt.x, pt.y, (brushSize / 2) * (imgSize.w / rect.width), 0, Math.PI * 2)
    ctx.fill()
    onMaskChange?.(true)
  }

  const onPointerDown = (e: React.PointerEvent) => {
    e.preventDefault()
    if (mode === 'brush') {
      drawing.current = true
      ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
      paintBrush(e.clientX, e.clientY)
      return
    }
    // rect mode: ignore if at the cap or already drafting an unsaved rect.
    if (rects.length >= MAX_RECTS || draft) return
    const pt = toNorm(e.clientX, e.clientY)
    if (!pt) return
    drawing.current = true
    ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
    rectStart.current = pt
    setDraft({ x: pt.x, y: pt.y, w: 0, h: 0 })
  }

  const onPointerMove = (e: React.PointerEvent) => {
    if (!drawing.current) return
    if (mode === 'brush') {
      paintBrush(e.clientX, e.clientY)
      return
    }
    const start = rectStart.current
    const pt = toNorm(e.clientX, e.clientY)
    if (!start || !pt) return
    const x = Math.max(0, Math.min(start.x, pt.x))
    const y = Math.max(0, Math.min(start.y, pt.y))
    const x2 = Math.min(1, Math.max(start.x, pt.x))
    const y2 = Math.min(1, Math.max(start.y, pt.y))
    setDraft({ x, y, w: x2 - x, h: y2 - y })
  }

  const onPointerUp = () => {
    drawing.current = false
    rectStart.current = null
    if (mode === 'rect' && draft && (draft.w < 0.01 || draft.h < 0.01)) {
      // Too small to be intentional — discard.
      setDraft(null)
    }
  }

  const confirmDraft = () => {
    if (!draft) return
    setRects(prev => [...prev, draft].slice(0, MAX_RECTS))
    setDraft(null)
  }

  const discardDraft = () => setDraft(null)

  const removeRect = (index: number) => {
    setRects(prev => prev.filter((_, i) => i !== index))
  }

  const pct = (v: number) => `${v * 100}%`

  return (
    <div className="region-painter">
      <div
        ref={wrapRef}
        className={`region-painter-stage region-painter-stage--${mode}`}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerLeave={onPointerUp}
        onContextMenu={e => e.preventDefault()}
      >
        <img ref={imgRef} src={imageSrc} alt="" className="region-painter-img" onLoad={syncCanvasSize} draggable={false} />
        <canvas ref={maskRef} className="region-painter-mask" aria-hidden="true" />
        {mode === 'rect' && rects.map((r, i) => (
          <div
            key={i}
            className="region-painter-rect"
            style={{ left: pct(r.x), top: pct(r.y), width: pct(r.w), height: pct(r.h) }}
          >
            <span className="region-painter-rect-no">{i + 1}</span>
            <button
              type="button"
              className="visible-layer-editor-occ-del"
              title={delLabel}
              aria-label={delLabel}
              onPointerDown={e => { e.preventDefault(); e.stopPropagation() }}
              onClick={e => { e.preventDefault(); e.stopPropagation(); removeRect(i) }}
            >
              ✕
            </button>
          </div>
        ))}
        {mode === 'rect' && draft && (draft.w > 0 || draft.h > 0) && (
          <div
            className="region-painter-rect region-painter-rect--draft"
            style={{ left: pct(draft.x), top: pct(draft.y), width: pct(draft.w), height: pct(draft.h) }}
          >
            {!drawing.current && (
              <div className="region-painter-draft-actions">
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  onPointerDown={e => { e.preventDefault(); e.stopPropagation() }}
                  onClick={e => { e.preventDefault(); e.stopPropagation(); confirmDraft() }}
                >
                  ✓ 保留
                </button>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onPointerDown={e => { e.preventDefault(); e.stopPropagation() }}
                  onClick={e => { e.preventDefault(); e.stopPropagation(); discardDraft() }}
                >
                  ✕ 重画
                </button>
              </div>
            )}
          </div>
        )}
      </div>
      {mode === 'rect' && (
        <p className="form-hint" style={{ marginTop: 6 }}>
          按住拖出一个矩形，松手后点「✓ 保留」存为一条、「✕ 重画」放弃；每条右上角的红色 ✕ 可单独删除（最多 {MAX_RECTS} 条，已画 {rects.length} 条）。
        </p>
      )}
      <button type="button" className="btn btn-secondary btn-sm" onClick={clearAll} style={{ marginTop: 8 }}>
        清除全部
      </button>
    </div>
  )
}
