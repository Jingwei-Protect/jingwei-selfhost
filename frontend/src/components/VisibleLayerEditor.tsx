import { Fragment, forwardRef, useCallback, useEffect, useImperativeHandle, useMemo, useRef, useState } from 'react'
import { useLocale } from '../i18n/LocaleContext'
import RadioPills from './RadioPills'
import { halftoneAuthorFontPxDisplay } from '../lib/halftonePreview'
import {
  placementOnlySnapshot,
  pushCappedHistory,
  shouldSnapshotMasks,
  workingCanvasSize,
} from '../lib/protectMemory'

function fmt(template: string, vars: Record<string, string | number>) {
  return Object.entries(vars).reduce((s, [k, v]) => s.replace(`{${k}}`, String(v)), template)
}

export type VisibleAddLayer = 'displacement' | 'blur_bar' | 'emboss' | 'face_emboss' | 'halftone_signature' | 'logo'

export type VisibleAddPlacement = {
  layer: VisibleAddLayer
  x: number
  y: number
  w?: number
  h?: number
}

export type AvailableLayer = {
  id: VisibleAddLayer
  label: string
  enabled: boolean
}

export type SelectedBlur = { w: number; h: number }

export type VisibleLayerExport = {
  mask: Blob | null
  placements: VisibleAddPlacement[]
  blurMask: Blob | null
}

export interface VisibleLayerEditorHandle {
  /** Resize the currently-selected blur bar (driven by the left-panel sliders). */
  resizeSelected: (w: number, h: number) => void
  /** Current dashed-box / signature placements (authoritative for preview submit). */
  getPlacements: () => VisibleAddPlacement[]
  /** True when canvas/placement edits exist since the last apply/save. */
  hasUnsavedChanges: () => boolean
  /** Export current editor state (same payload as the apply button). */
  exportEdits: () => Promise<VisibleLayerExport>
  /** Revert canvas and placements to the last applied/saved snapshot. */
  revertToSaved: () => void
  /** Mark the current history entry as saved (called after parent commits edits). */
  markSaved: () => void
}

/** What a click does in the placement phase. 'blurbrush' freehand-paints a blur mask. */
type PlaceTool = VisibleAddLayer | 'blurbrush'

interface Props {
  imageSrc: string
  processing: boolean
  availableLayers: AvailableLayer[]
  onApply: (
    mask: Blob | null,
    placements: VisibleAddPlacement[],
    blurMask: Blob | null,
  ) => void
  /** Preview-only refresh when eraser/blur strokes changed (no invisible watermark write). */
  onUpdatePreview?: (
    mask: Blob | null,
    placements: VisibleAddPlacement[],
    blurMask: Blob | null,
  ) => void
  updatePreviewLabel?: string
  onClear: () => void
  applyLabel?: string
  previewMode?: boolean
  displacementText?: string
  displacementFontRatio?: number
  onPlacementsChange?: (placements: VisibleAddPlacement[]) => void
  seed?: { key: number; placements: VisibleAddPlacement[] }
  /** True once a real rendered preview/result exists. Drives the phase:
   *  false = 摆放 (place marks / paint blur, no eraser); true = 微调 (eraser only). */
  hasPreview?: boolean
  /** Return from 微调 back to 摆放 (parent drops the preview so the clean image
   *  with editable marks comes back). */
  onBackToPlace?: () => void
  /** Notifies the parent which blur bar is selected (so the left panel can show
   *  width/height sliders), or null when nothing/again a non-bar is selected. */
  onSelectedChange?: (sel: SelectedBlur | null) => void
  /** Offer a freehand 模糊画笔 tool in the placement phase (blur brush mode). */
  allowBlurBrush?: boolean
  /** Clean (un-watermarked) image. In the eraser phase, painting reveals these
   *  pixels through the watermarked preview so you see the erased result live. */
  originalSrc?: string
  /** ASCII watermark dot style: signature label on placement marks. */
  halftoneText?: string
  /** 0–100; scales placement mark to match rendered signature size. */
  halftoneSignatureSize?: number
  /** Logo longest-side fraction of the host short edge (matches ``logo_scale``). */
  logoScale?: number
  /** Parent card already shows a section title — hide the in-editor duplicate. */
  hideTitle?: boolean
}

const BLUR_DEFAULT_W = 0.6
const BLUR_DEFAULT_H = 0.07
const EMBOSS_PATCH_RATIO = 0.22
const FACE_EMBOSS_PATCH_RATIO = 0.28
const DISPLACEMENT_BAND_H_FACTOR = 1.4

const DRAG_THRESHOLD_PX = 6
const MAX_BLUR_BARS = 5

const ERASE_COLOR = 'rgba(255, 72, 72, 0.55)'
const BLUR_PAINT_COLOR = 'rgba(59, 130, 246, 0.5)'

type Snapshot = {
  placements: VisibleAddPlacement[]
  mask: ImageData | null
  blur: ImageData | null
  /** Pure binary erase mask for export (independent of preview overlay pixels). */
  eraseExport: ImageData | null
}

/** Place / size / delete visible-layer marks, paint blur, then refine with an
 *  eraser — all with a single undo/redo history. */
const VisibleLayerEditor = forwardRef<VisibleLayerEditorHandle, Props>(function VisibleLayerEditor({
  imageSrc,
  processing,
  availableLayers,
  onApply,
  onUpdatePreview,
  updatePreviewLabel,
  onClear,
  applyLabel,
  previewMode = false,
  displacementText = '',
  displacementFontRatio = 0.15,
  onPlacementsChange,
  seed,
  hasPreview = false,
  onBackToPlace,
  onSelectedChange,
  allowBlurBrush = false,
  originalSrc,
  halftoneText = '',
  halftoneSignatureSize = 50,
  logoScale = 0.18,
  hideTitle = false,
}, ref) {
  const { messages: m } = useLocale()
  const v = m.components.visibleLayerEditor
  const wrapRef = useRef<HTMLDivElement>(null)
  const imgRef = useRef<HTMLImageElement>(null)
  const originalImgRef = useRef<HTMLImageElement | null>(null)
  const maskRef = useRef<HTMLCanvasElement>(null)
  const eraseExportRef = useRef<HTMLCanvasElement>(null)
  const blurRef = useRef<HTMLCanvasElement>(null)
  const [brush, setBrush] = useState(28)
  const [addLayer, setAddLayer] = useState<PlaceTool>('displacement')
  const [placements, setPlacements] = useState<VisibleAddPlacement[]>([])
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null)
  const [imgSize, setImgSize] = useState({ w: 0, h: 0 })
  const [renderSize, setRenderSize] = useState({ w: 0, h: 0 })
  const drawing = useRef(false)
  const drawTarget = useRef<'erase' | 'blur' | null>(null)
  const dragIndex = useRef<number | null>(null)
  const dragMoved = useRef(false)
  const dragLast = useRef<{ x: number; y: number } | null>(null)
  // Phase is derived from hasPreview: place/paint first, then refine (eraser).
  const phase: 'place' | 'refine' = hasPreview ? 'refine' : 'place'

  const placementsRef = useRef(placements)
  placementsRef.current = placements

  // ---- Undo / redo history (placements + erase mask + blur mask) ----
  const historyRef = useRef<Snapshot[]>([])
  const histIndexRef = useRef(-1)
  const applyBaselineIndexRef = useRef(0)
  const lastOpRef = useRef<string | null>(null)
  const lastMaskSnapRef = useRef<Pick<Snapshot, 'mask' | 'blur' | 'eraseExport'>>({
    mask: null,
    blur: null,
    eraseExport: null,
  })
  const draggingPlacement = useRef(false)
  const dragRafRef = useRef(0)
  const [histVersion, setHistVersion] = useState(0)

  const getCtx = useCallback((canvas: HTMLCanvasElement | null): CanvasRenderingContext2D | null => {
    return canvas?.getContext('2d', { willReadFrequently: true }) ?? null
  }, [])

  const grab = useCallback((canvas: HTMLCanvasElement | null): ImageData | null => {
    const ctx = getCtx(canvas)
    if (!canvas || !ctx || !canvas.width) return null
    return ctx.getImageData(0, 0, canvas.width, canvas.height)
  }, [getCtx])

  const restore = useCallback((canvas: HTMLCanvasElement | null, data: ImageData | null) => {
    if (!canvas) return
    if (data && (canvas.width !== data.width || canvas.height !== data.height)) {
      canvas.width = data.width
      canvas.height = data.height
    }
    const ctx = getCtx(canvas)
    if (!ctx) return
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    if (data && data.width === canvas.width && data.height === canvas.height) {
      ctx.putImageData(data, 0, 0)
    }
  }, [getCtx])

  const snapshotNow = useCallback((p: VisibleAddPlacement[], opType?: string): Snapshot => {
    if (opType && shouldSnapshotMasks(opType)) {
      lastMaskSnapRef.current = {
        mask: grab(maskRef.current),
        blur: grab(blurRef.current),
        eraseExport: grab(eraseExportRef.current),
      }
    }
    if (!opType || !shouldSnapshotMasks(opType)) {
      return {
        ...placementOnlySnapshot(p),
        ...lastMaskSnapRef.current,
      }
    }
    return { placements: p, ...lastMaskSnapRef.current }
  }, [grab])

  const resetHistory = useCallback((initial: VisibleAddPlacement[]) => {
    lastMaskSnapRef.current = { mask: null, blur: null, eraseExport: null }
    historyRef.current = [placementOnlySnapshot(initial)]
    histIndexRef.current = 0
    applyBaselineIndexRef.current = 0
    lastOpRef.current = null
    setHistVersion(v => v + 1)
  }, [])

  const markSaved = useCallback(() => {
    applyBaselineIndexRef.current = histIndexRef.current
    setHistVersion(v => v + 1)
  }, [])

  const pushHistory = useCallback((nextPlacements: VisibleAddPlacement[], opType: string) => {
    const snap = snapshotNow(nextPlacements, opType)
    if (opType === 'resize' && lastOpRef.current === 'resize' && historyRef.current.length > 0) {
      historyRef.current[historyRef.current.length - 1] = snap
      histIndexRef.current = historyRef.current.length - 1
    } else {
      const next = pushCappedHistory(historyRef.current, histIndexRef.current, snap)
      historyRef.current = next.history
      histIndexRef.current = next.index
    }
    lastOpRef.current = opType
    setHistVersion(v => v + 1)
  }, [snapshotNow])

  const applySnapshot = useCallback((snap: Snapshot) => {
    setPlacements(snap.placements)
    setSelectedIndex(null)
    restore(maskRef.current, snap.mask)
    restore(blurRef.current, snap.blur)
    restore(eraseExportRef.current, snap.eraseExport)
    lastMaskSnapRef.current = {
      mask: snap.mask,
      blur: snap.blur,
      eraseExport: snap.eraseExport,
    }
  }, [restore])

  const undo = useCallback(() => {
    if (histIndexRef.current <= 0) return
    histIndexRef.current -= 1
    lastOpRef.current = null
    applySnapshot(historyRef.current[histIndexRef.current])
    setHistVersion(v => v + 1)
  }, [applySnapshot])

  const redo = useCallback(() => {
    if (histIndexRef.current >= historyRef.current.length - 1) return
    histIndexRef.current += 1
    lastOpRef.current = null
    applySnapshot(historyRef.current[histIndexRef.current])
    setHistVersion(v => v + 1)
  }, [applySnapshot])

  const canUndo = histIndexRef.current > 0
  const canRedo = histIndexRef.current < historyRef.current.length - 1
  const hasUnsavedEdits = histIndexRef.current !== applyBaselineIndexRef.current
  void histVersion

  useEffect(() => {
    if (draggingPlacement.current) return
    onPlacementsChange?.(placements)
  }, [placements, onPlacementsChange])

  const seedRef = useRef(seed)
  seedRef.current = seed
  const seedKey = seed?.key
  useEffect(() => {
    if (seedKey === undefined) return
    const next = seedRef.current?.placements ?? []
    setPlacements(next)
    setSelectedIndex(null)
    // A fresh seed means a clean canvas for masks too.
    restore(maskRef.current, null)
    restore(eraseExportRef.current, null)
    restore(blurRef.current, null)
    resetHistory(next)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [seedKey])

  const enabledLayers = useMemo(
    () => availableLayers.filter(l => l.enabled),
    [availableLayers],
  )

  const placeOptions = useMemo(() => {
    const opts: { label: string; value: PlaceTool }[] = enabledLayers.map(l => ({ label: l.label, value: l.id }))
    if (allowBlurBrush) opts.push({ label: v.blurBrush, value: 'blurbrush' })
    return opts
  }, [enabledLayers, allowBlurBrush, v.blurBrush])

  useEffect(() => {
    if (placeOptions.length === 0) return
    if (!placeOptions.some(o => o.value === addLayer)) {
      const prefer = allowBlurBrush ? 'blurbrush' : placeOptions[0].value
      setAddLayer(prefer as PlaceTool)
    }
  }, [placeOptions, addLayer, allowBlurBrush])

  // When the user switches the blur mode to 画笔涂抹, make the brush the active
  // tool immediately (rather than leaving a box tool selected).
  const prevAllowBrush = useRef(allowBlurBrush)
  useEffect(() => {
    if (allowBlurBrush && !prevAllowBrush.current) setAddLayer('blurbrush')
    prevAllowBrush.current = allowBlurBrush
  }, [allowBlurBrush])

  const tool: 'eraser' | 'blurbrush' | 'add' =
    phase === 'refine' ? 'eraser' : addLayer === 'blurbrush' ? 'blurbrush' : 'add'

  useEffect(() => {
    const sel = selectedIndex !== null ? placements[selectedIndex] : null
    if (sel && sel.layer === 'blur_bar') {
      onSelectedChange?.({ w: sel.w ?? BLUR_DEFAULT_W, h: sel.h ?? BLUR_DEFAULT_H })
    } else {
      onSelectedChange?.(null)
    }
  }, [selectedIndex, placements, onSelectedChange])

  const ensureMaskCanvases = useCallback((): { w: number; h: number } => {
    const img = imgRef.current
    if (!img || !img.naturalWidth) return { w: 0, h: 0 }
    const size = workingCanvasSize(img.naturalWidth, img.naturalHeight)
    for (const c of [maskRef.current, eraseExportRef.current, blurRef.current]) {
      if (!c) continue
      if (c.width === size.w && c.height === size.h) continue
      const ctx = getCtx(c)
      if (!ctx) continue
      let prev: ImageData | null = null
      if (c.width > 0 && c.height > 0) {
        try {
          prev = ctx.getImageData(0, 0, c.width, c.height)
        } catch {
          prev = null
        }
      }
      c.width = size.w
      c.height = size.h
      if (prev && prev.width === size.w && prev.height === size.h) {
        ctx.putImageData(prev, 0, 0)
      } else if (prev && prev.width > 0 && prev.height > 0) {
        const tmp = document.createElement('canvas')
        tmp.width = prev.width
        tmp.height = prev.height
        tmp.getContext('2d')!.putImageData(prev, 0, 0)
        ctx.drawImage(tmp, 0, 0, size.w, size.h)
      }
    }
    return size
  }, [getCtx])

  const syncCanvasSize = useCallback(() => {
    const img = imgRef.current
    if (!img || !img.naturalWidth) return
    setImgSize({ w: img.naturalWidth, h: img.naturalHeight })
    const r = img.getBoundingClientRect()
    setRenderSize({ w: r.width, h: r.height })
    const alreadyAllocated = [maskRef.current, eraseExportRef.current, blurRef.current]
      .some(c => Boolean(c && c.width > 0 && c.height > 0))
    if (alreadyAllocated) ensureMaskCanvases()
  }, [ensureMaskCanvases])

  useEffect(() => {
    syncCanvasSize()
  }, [imageSrc, syncCanvasSize])

  useEffect(() => {
    const img = imgRef.current
    if (!img || typeof ResizeObserver === 'undefined') return
    const ro = new ResizeObserver(() => {
      const r = img.getBoundingClientRect()
      setRenderSize({ w: r.width, h: r.height })
    })
    ro.observe(img)
    return () => ro.disconnect()
  }, [])

  useEffect(() => {
    if (historyRef.current.length === 0) resetHistory(placementsRef.current)
  }, [resetHistory])

  const toNorm = useCallback((clientX: number, clientY: number) => {
    const wrap = wrapRef.current
    if (!wrap || !imgSize.w) return null
    const rect = wrap.getBoundingClientRect()
    const x = (clientX - rect.left) / rect.width
    const y = (clientY - rect.top) / rect.height
    if (x < 0 || x > 1 || y < 0 || y > 1) return null
    return { x, y }
  }, [imgSize.w])

  const paintBlur = useCallback((clientX: number, clientY: number) => {
    const size = ensureMaskCanvases()
    const canvas = blurRef.current
    const wrap = wrapRef.current
    const ctx = getCtx(canvas)
    if (!canvas || !wrap || !ctx || !size.w) return
    const rect = wrap.getBoundingClientRect()
    const px = ((clientX - rect.left) / rect.width) * size.w
    const py = ((clientY - rect.top) / rect.height) * size.h
    ctx.fillStyle = BLUR_PAINT_COLOR
    ctx.beginPath()
    ctx.arc(px, py, (brush / 2) * (size.w / rect.width), 0, Math.PI * 2)
    ctx.fill()
  }, [brush, ensureMaskCanvases, getCtx])

  const stampEraseExport = useCallback((px: number, py: number, r: number) => {
    const canvas = eraseExportRef.current
    const ctx = getCtx(canvas)
    if (!canvas || !ctx) return
    ctx.fillStyle = '#ffffff'
    ctx.beginPath()
    ctx.arc(px, py, r, 0, Math.PI * 2)
    ctx.fill()
  }, [getCtx])

  // Preview overlay shows the clean original; eraseExportRef holds the binary mask.
  const paintErase = useCallback((clientX: number, clientY: number) => {
    const size = ensureMaskCanvases()
    const canvas = maskRef.current
    const wrap = wrapRef.current
    const ctx = getCtx(canvas)
    if (!canvas || !wrap || !ctx || !size.w) return
    const rect = wrap.getBoundingClientRect()
    const px = ((clientX - rect.left) / rect.width) * size.w
    const py = ((clientY - rect.top) / rect.height) * size.h
    const r = (brush / 2) * (size.w / rect.width)
    const orig = originalImgRef.current
    if (orig && orig.complete && orig.naturalWidth) {
      const srcScaleX = orig.naturalWidth / size.w
      const srcScaleY = orig.naturalHeight / size.h
      const destX = px - r
      const destY = py - r
      const destS = r * 2
      ctx.save()
      ctx.beginPath()
      ctx.arc(px, py, r, 0, Math.PI * 2)
      ctx.clip()
      ctx.drawImage(
        orig,
        destX * srcScaleX,
        destY * srcScaleY,
        destS * srcScaleX,
        destS * srcScaleY,
        destX,
        destY,
        destS,
        destS,
      )
      ctx.restore()
    } else {
      ctx.fillStyle = ERASE_COLOR
      ctx.beginPath()
      ctx.arc(px, py, r, 0, Math.PI * 2)
      ctx.fill()
    }
    stampEraseExport(px, py, r)
  }, [brush, ensureMaskCanvases, getCtx, stampEraseExport])

  const makePlacement = useCallback((layer: VisibleAddLayer, cx: number, cy: number): VisibleAddPlacement => {
    if (layer === 'blur_bar') {
      const w = BLUR_DEFAULT_W
      const h = BLUR_DEFAULT_H
      return {
        layer,
        x: Math.max(0, Math.min(1 - w, cx - w / 2)),
        y: Math.max(0, Math.min(1 - h, cy - h / 2)),
        w,
        h,
      }
    }
    return { layer, x: cx, y: cy }
  }, [])

  const onPointerDown = (e: React.PointerEvent) => {
    e.preventDefault()
    if (processing) return
    if (tool === 'add') {
      if (placeOptions.length === 0) return
      const layer = addLayer as VisibleAddLayer
      if (layer === 'blur_bar' && placements.filter(p => p.layer === 'blur_bar').length >= MAX_BLUR_BARS) return
      if (layer === 'halftone_signature' && placementsRef.current.some(p => p.layer === 'halftone_signature')) return
      if (layer === 'logo' && placementsRef.current.some(p => p.layer === 'logo')) return
      const p = toNorm(e.clientX, e.clientY)
      if (p) {
        const next = [...placementsRef.current, makePlacement(layer, p.x, p.y)]
        setPlacements(next)
        setSelectedIndex(next.length - 1)
        pushHistory(next, 'add')
      }
      return
    }
    drawing.current = true
    drawTarget.current = tool === 'eraser' ? 'erase' : 'blur'
    ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
    if (drawTarget.current === 'erase') paintErase(e.clientX, e.clientY)
    else paintBlur(e.clientX, e.clientY)
  }

  const onPointerMove = (e: React.PointerEvent) => {
    if (!drawing.current) return
    if (drawTarget.current === 'erase') paintErase(e.clientX, e.clientY)
    else if (drawTarget.current === 'blur') paintBlur(e.clientX, e.clientY)
  }

  const finishDraw = () => {
    if (drawing.current && drawTarget.current) {
      pushHistory(placementsRef.current, drawTarget.current === 'erase' ? 'erase' : 'blur')
    }
    drawing.current = false
    drawTarget.current = null
  }

  const removePlacement = (index: number) => {
    const next = placementsRef.current.filter((_, idx) => idx !== index)
    setPlacements(next)
    setSelectedIndex(prev => (prev === index ? null : prev !== null && prev > index ? prev - 1 : prev))
    pushHistory(next, 'delete')
  }

  const placementBox = useCallback((p: VisibleAddPlacement) => {
    if (p.layer === 'blur_bar' && p.w && p.h) {
      return { left: p.x, top: p.y, width: p.w, height: p.h }
    }
    const w = imgSize.w || 1
    const h = imgSize.h || 1
    let ow = 0.2
    let oh = 0.2
    if (p.layer === 'emboss' || p.layer === 'face_emboss') {
      const ratio = p.layer === 'emboss' ? EMBOSS_PATCH_RATIO : FACE_EMBOSS_PATCH_RATIO
      const sq = ratio * Math.min(w, h)
      ow = sq / w
      oh = sq / h
    } else if (p.layer === 'displacement') {
      const bandPx = displacementFontRatio * Math.min(w, h) * DISPLACEMENT_BAND_H_FACTOR
      oh = Math.min(0.4, bandPx / h)
      ow = oh
    } else if (p.layer === 'logo') {
      const side = Math.max(0.06, Math.min(0.55, logoScale)) * Math.min(w, h)
      ow = side / w
      oh = side / h
    }
    return {
      left: Math.max(0, Math.min(1 - ow, p.x - ow / 2)),
      top: Math.max(0, Math.min(1 - oh, p.y - oh / 2)),
      width: ow,
      height: oh,
    }
  }, [imgSize.w, imgSize.h, displacementFontRatio, logoScale])

  const startDragPlacement = (index: number, e: React.PointerEvent) => {
    const layer = placementsRef.current[index]?.layer
    if (processing) return
    if (tool !== 'add' && layer !== 'logo') return
    e.preventDefault()
    e.stopPropagation()
    ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
    draggingPlacement.current = true
    dragIndex.current = index
    dragMoved.current = false
    dragLast.current = { x: e.clientX, y: e.clientY }
  }

  const onDragPlacement = (e: React.PointerEvent) => {
    if (dragIndex.current === null || dragLast.current === null) return
    e.preventDefault()
    e.stopPropagation()
    const wrap = wrapRef.current
    if (!wrap) return
    const rect = wrap.getBoundingClientRect()
    const dxPx = e.clientX - dragLast.current.x
    const dyPx = e.clientY - dragLast.current.y
    if (Math.abs(dxPx) + Math.abs(dyPx) > DRAG_THRESHOLD_PX) dragMoved.current = true
    dragLast.current = { x: e.clientX, y: e.clientY }
    const dxNorm = dxPx / rect.width
    const dyNorm = dyPx / rect.height
    const idx = dragIndex.current
    placementsRef.current = placementsRef.current.map((p, i) => {
      if (i !== idx) return p
      if (p.layer === 'blur_bar' && p.w && p.h) {
        return {
          ...p,
          x: Math.max(0, Math.min(1 - p.w, p.x + dxNorm)),
          y: Math.max(0, Math.min(1 - p.h, p.y + dyNorm)),
        }
      }
      return {
        ...p,
        x: Math.max(0, Math.min(1, p.x + dxNorm)),
        y: Math.max(0, Math.min(1, p.y + dyNorm)),
      }
    })
    if (dragRafRef.current) return
    dragRafRef.current = window.requestAnimationFrame(() => {
      dragRafRef.current = 0
      setPlacements(placementsRef.current)
    })
  }

  const endDragPlacement = (index: number, e: React.PointerEvent) => {
    if (dragIndex.current === null) return
    e.preventDefault()
    e.stopPropagation()
    const moved = dragMoved.current
    dragIndex.current = null
    dragLast.current = null
    dragMoved.current = false
    if (dragRafRef.current) {
      window.cancelAnimationFrame(dragRafRef.current)
      dragRafRef.current = 0
    }
    setPlacements(placementsRef.current)
    draggingPlacement.current = false
    onPlacementsChange?.(placementsRef.current)
    if (moved) {
      pushHistory(placementsRef.current, 'move')
    } else {
      setSelectedIndex(index)
    }
  }

  const clampSize = (p: VisibleAddPlacement): VisibleAddPlacement => {
    const next = { ...p }
    if (next.w) next.x = Math.max(0, Math.min(1 - next.w, next.x))
    if (next.h) next.y = Math.max(0, Math.min(1 - next.h, next.y))
    return next
  }

  const exportBinaryMask = async (canvas: HTMLCanvasElement | null): Promise<Blob | null> => {
    if (!canvas || !imgSize.w) return null
    const ctx = getCtx(canvas)
    if (!ctx || !canvas.width || !canvas.height) return null
    const src = ctx.getImageData(0, 0, canvas.width, canvas.height)
    let hasStroke = false
    for (let i = 0; i < src.data.length; i += 4) {
      const a = src.data[i + 3]
      const lum = src.data[i] + src.data[i + 1] + src.data[i + 2]
      if (a > 8 || lum > 24) { hasStroke = true; break }
    }
    if (!hasStroke) return null
    const out = document.createElement('canvas')
    out.width = canvas.width
    out.height = canvas.height
    const octx = out.getContext('2d')
    if (!octx) return null
    octx.fillStyle = '#000000'
    octx.fillRect(0, 0, out.width, out.height)
    const bin = octx.createImageData(out.width, out.height)
    for (let i = 0; i < src.data.length; i += 4) {
      const a = src.data[i + 3]
      const lum = src.data[i] + src.data[i + 1] + src.data[i + 2]
      const v = (a > 8 || lum > 24) ? 255 : 0
      bin.data[i] = v
      bin.data[i + 1] = v
      bin.data[i + 2] = v
      bin.data[i + 3] = 255
    }
    octx.putImageData(bin, 0, 0)
    return new Promise(resolve => out.toBlob(b => resolve(b), 'image/png'))
  }

  const exportBinaryMaskFromImageData = async (data: ImageData | null): Promise<Blob | null> => {
    if (!data || !data.width || !data.height) return null
    const tmp = document.createElement('canvas')
    tmp.width = data.width
    tmp.height = data.height
    tmp.getContext('2d')!.putImageData(data, 0, 0)
    return exportBinaryMask(tmp)
  }

  const exportEraseMaskBlob = async (): Promise<Blob | null> => {
    let maskBlob = await exportBinaryMask(eraseExportRef.current ?? maskRef.current)
    if (maskBlob) return maskBlob
    const snap = historyRef.current[histIndexRef.current]
    if (snap?.eraseExport) {
      maskBlob = await exportBinaryMaskFromImageData(snap.eraseExport)
    }
    if (maskBlob) return maskBlob
    if (snap?.mask) {
      maskBlob = await exportBinaryMaskFromImageData(snap.mask)
    }
    return maskBlob
  }

  useImperativeHandle(ref, () => ({
    resizeSelected: (w: number, h: number) => {
      if (selectedIndex === null) return
      const next = placementsRef.current.map((p, i) =>
        i === selectedIndex && p.layer === 'blur_bar' ? clampSize({ ...p, w, h }) : p,
      )
      setPlacements(next)
      pushHistory(next, 'resize')
    },
    getPlacements: () => placementsRef.current,
    hasUnsavedChanges: () => histIndexRef.current !== applyBaselineIndexRef.current,
    exportEdits: async () => {
      const maskBlob = await exportEraseMaskBlob()
      const blurBlob = await exportBinaryMask(blurRef.current)
      return { mask: maskBlob, placements: placementsRef.current, blurMask: blurBlob }
    },
    revertToSaved: () => {
      const baseline = historyRef.current[applyBaselineIndexRef.current]
      if (!baseline) return
      applySnapshot(baseline)
      histIndexRef.current = applyBaselineIndexRef.current
      lastOpRef.current = null
      setHistVersion(v => v + 1)
    },
    markSaved,
  }), [selectedIndex, pushHistory, markSaved, applySnapshot])

  const clearAll = () => {
    restore(maskRef.current, null)
    restore(eraseExportRef.current, null)
    restore(blurRef.current, null)
    lastMaskSnapRef.current = { mask: null, blur: null, eraseExport: null }
    setPlacements([])
    setSelectedIndex(null)
    pushHistory([], 'clear')
    onClear()
  }

  const handleApply = async () => {
    const maskBlob = await exportEraseMaskBlob()
    const blurBlob = await exportBinaryMask(blurRef.current)
    markSaved()
    onApply(maskBlob, placements, blurBlob)
  }

  const handleUpdatePreview = async () => {
    if (!onUpdatePreview) return
    const maskBlob = await exportEraseMaskBlob()
    const blurBlob = await exportBinaryMask(blurRef.current)
    onUpdatePreview(maskBlob, placements, blurBlob)
  }

  const stageClass = tool === 'add' ? ' is-add' : ' is-eraser'
  const blurCount = placements.filter(p => p.layer === 'blur_bar').length
  const placingOnly = previewMode && !hasPreview
  // 生成预览：尚未渲染预览帧（摆放阶段）→ 仅刷新可见层预览
  // 保存修改：已有预览/结果帧 → 完整保护；有未保存擦除时另显示「更新预览」
  const primaryLabel = placingOnly ? v.generatePreview : (applyLabel ?? v.save)
  const showUpdatePreview = Boolean(
    previewMode && hasPreview && hasUnsavedEdits && onUpdatePreview,
  )

  const steps: { label: string; active: boolean }[] = previewMode
    ? (hasPreview
      ? [
          { label: v.stepsPreviewRefine.refine, active: phase === 'refine' },
          { label: v.stepsPreviewRefine.save, active: false },
          { label: v.stepsPreviewRefine.protect, active: false },
        ]
      : [
          { label: v.steps.place, active: phase === 'place' },
          { label: v.steps.generate, active: false },
          { label: v.steps.refine, active: false },
          { label: v.steps.download, active: false },
        ])
    : [
        { label: v.stepsRefine.refine, active: phase === 'refine' },
        { label: v.stepsRefine.save, active: false },
        { label: v.stepsRefine.download, active: false },
      ]
  const stepsNote = previewMode
    ? (hasPreview ? v.refineHintPreview : v.generatePreviewHint)
    : v.refineHintFull

  const showBrushSlider = phase === 'refine' || (phase === 'place' && addLayer === 'blurbrush')

  const addHint = (() => {
    if (placeOptions.length === 0) return v.noLayersHint
    if (addLayer === 'blurbrush') return v.blurBrushHint
    const layerLabel = placeOptions.find(o => o.value === addLayer)?.label ?? ''
    if (addLayer === 'displacement') {
      return fmt(v.placeDisplacementHint, { layer: layerLabel })
    }
    if (addLayer === 'halftone_signature') {
      return v.placeHalftoneHint
    }
    if (addLayer === 'logo') {
      return v.placeLogoHint
    }
    if (addLayer === 'blur_bar') return fmt(v.placeBlurBarHint, { layer: layerLabel, max: MAX_BLUR_BARS })
    return fmt(v.placeGenericHint, { layer: layerLabel })
  })()

  const historyTools = (
    <div className="visible-layer-editor-tools">
      <button type="button" className="btn btn-secondary btn-sm" onClick={undo} disabled={processing || !canUndo} title={v.undoTitle}>
        ↶ {v.undo}
      </button>
      <button type="button" className="btn btn-secondary btn-sm" onClick={redo} disabled={processing || !canRedo} title={v.redoTitle}>
        ↷ {v.redo}
      </button>
      {phase === 'refine' && onBackToPlace && (
        <button type="button" className="btn btn-secondary btn-sm" onClick={onBackToPlace} disabled={processing} title={v.backToPlaceTitle}>
          {v.returnToPlace}
        </button>
      )}
    </div>
  )

  const stepsBlock = placeOptions.length > 0 ? (
    <div className="visible-layer-editor-steps-block">
      <div className="visible-layer-editor-steps">
        {steps.map((s, i) => (
          <Fragment key={i}>
            {i > 0 && <span className="visible-layer-editor-steps-arrow">→</span>}
            <span className={`visible-layer-editor-steps-item${s.active ? ' is-active' : ''}`}>{s.label}</span>
          </Fragment>
        ))}
      </div>
      <p className="form-hint visible-layer-editor-steps-note">{stepsNote}</p>
    </div>
  ) : null

  return (
    <div className="visible-layer-editor">
      {!hideTitle && (
        <div className="visible-layer-editor-toolbar">
          <span className="text-sm text-secondary">{v.title}</span>
        </div>
      )}

      {placeOptions.length > 1 && (
        <div className="form-group" style={{ marginBottom: 0 }}>
          <label className="form-label">
            {phase === 'refine' ? v.placeToolRefine : v.placeToolPlace}
          </label>
          <RadioPills
            options={placeOptions}
            value={addLayer}
            onChange={v => {
              setAddLayer(v as PlaceTool)
              setSelectedIndex(null)
              // In the eraser/refine phase the placement marks are hidden. Picking
              // a type here means "I want to place this", so jump back to the
              // 摆放 phase (keeping existing marks) and let the click drop it.
              if (phase === 'refine') onBackToPlace?.()
            }}
          />
        </div>
      )}

      {phase === 'refine' && (
        <div className="visible-layer-editor-mode-banner">
{v.eraseMode}
        </div>
      )}

      {showBrushSlider && (
        <div className="form-group" style={{ marginBottom: 8 }}>
          <label className="form-label">{fmt(v.brushSize, { tool: phase === 'refine' ? v.brushEraser : v.brushPaint, px: brush })}</label>
          <input type="range" min={8} max={80} value={brush} onChange={e => setBrush(Number(e.target.value))} disabled={processing} />
        </div>
      )}

      {originalSrc && originalSrc !== imageSrc && (
        <img
          ref={originalImgRef}
          src={originalSrc}
          alt=""
          aria-hidden="true"
          draggable={false}
          style={{ display: 'none' }}
        />
      )}
      <canvas ref={eraseExportRef} width={0} height={0} aria-hidden="true" style={{ display: 'none' }} />

      <div className="visible-layer-editor-actions">
        {showUpdatePreview && (
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => { void handleUpdatePreview() }}
            disabled={processing}
          >
            {updatePreviewLabel ?? v.updatePreview}
          </button>
        )}
        <button type="button" className="btn btn-primary" onClick={() => { void handleApply() }} disabled={processing}>
          {processing ? m.components.imageUpload.processing : primaryLabel}
        </button>
        <button type="button" className="btn btn-secondary" onClick={clearAll} disabled={processing} title={v.clearHint}>
          {v.clear}
        </button>
      </div>

      <div className="visible-layer-editor-preview-block">
        <div className="visible-layer-editor-stage-wrap">
          <div
            ref={wrapRef}
            className={`visible-layer-editor-stage${stageClass}`}
            onPointerDown={onPointerDown}
            onPointerMove={onPointerMove}
            onPointerUp={finishDraw}
            onPointerLeave={finishDraw}
            onContextMenu={e => e.preventDefault()}
          >
        <img
          ref={imgRef}
          src={imageSrc}
          alt=""
          className="visible-layer-editor-img"
          onLoad={syncCanvasSize}
          draggable={false}
        />
        <canvas
          ref={blurRef}
          className="visible-layer-editor-mask"
          width={0}
          height={0}
          aria-hidden="true"
          style={{ display: phase === 'place' ? 'block' : 'none' }}
        />
        <canvas
          ref={maskRef}
          className="visible-layer-editor-mask"
          width={0}
          height={0}
          aria-hidden="true"
          style={{ display: phase === 'refine' ? 'block' : 'none' }}
        />
        {placements.map((p, i) => {
          if (phase !== 'place' && p.layer !== 'logo') return null
          const canDrag = !processing
          const isSelected = i === selectedIndex
          const showDelete = p.layer !== 'logo'
          const dispFontPx = displacementFontRatio * Math.min(renderSize.w, renderSize.h)
          if (p.layer === 'displacement' || p.layer === 'halftone_signature') {
            const isHalftone = p.layer === 'halftone_signature'
            const markText = isHalftone ? halftoneText.trim() : displacementText.trim()
            const markFontPx = isHalftone
              ? halftoneAuthorFontPxDisplay(imgSize, renderSize, halftoneSignatureSize)
              : dispFontPx
            const markClass = isHalftone
              ? 'visible-layer-editor-mark visible-layer-editor-mark--halftone'
              : 'visible-layer-editor-mark visible-layer-editor-mark--displacement'
            return (
              <div
                key={`${i}-${p.layer}`}
                className={`${markClass}${isSelected ? ' is-selected' : ''}`}
                style={{
                  left: `${p.x * 100}%`,
                  top: `${p.y * 100}%`,
                  transform: 'translate(-50%, -50%)',
                  pointerEvents: canDrag ? 'auto' : 'none',
                  cursor: canDrag ? 'grab' : 'default',
                  touchAction: 'none',
                }}
                onPointerDown={e => startDragPlacement(i, e)}
                onPointerMove={onDragPlacement}
                onPointerUp={e => endDragPlacement(i, e)}
                onPointerCancel={e => endDragPlacement(i, e)}
              >
                {markText && markFontPx > 0 && (
                  <span className="visible-layer-editor-mark-text" style={{ fontSize: `${markFontPx}px`, lineHeight: 1 }}>
                    {markText}
                  </span>
                )}
                {showDelete && (
                <button
                  type="button"
                  className="visible-layer-editor-occ-del"
                  title={v.deleteMark}
                  aria-label={v.deleteMark}
                  onPointerDown={e => { e.preventDefault(); e.stopPropagation() }}
                  onClick={e => { e.preventDefault(); e.stopPropagation(); removePlacement(i) }}
                >
                  ✕
                </button>
                )}
              </div>
            )
          }
          const box = placementBox(p)
          return (
            <div
              key={`${i}-${p.layer}`}
              className={`visible-layer-editor-occ visible-layer-editor-occ--${p.layer}${isSelected ? ' is-selected' : ''}`}
              title={canDrag ? v.markDragHint : undefined}
              style={{
                left: `${box.left * 100}%`,
                top: `${box.top * 100}%`,
                width: `${box.width * 100}%`,
                height: `${box.height * 100}%`,
                pointerEvents: canDrag ? 'auto' : 'none',
                cursor: canDrag ? 'grab' : 'default',
                touchAction: 'none',
              }}
              onPointerDown={e => startDragPlacement(i, e)}
              onPointerMove={onDragPlacement}
              onPointerUp={e => endDragPlacement(i, e)}
              onPointerCancel={e => endDragPlacement(i, e)}
            >
              {showDelete && (
              <button
                type="button"
                className="visible-layer-editor-occ-del"
                title={v.deleteMark}
                aria-label={v.deleteMark}
                onPointerDown={e => { e.preventDefault(); e.stopPropagation() }}
                onClick={e => { e.preventDefault(); e.stopPropagation(); removePlacement(i) }}
              >
                ✕
              </button>
              )}
            </div>
          )
        })}
          </div>
          <div className="visible-layer-editor-tools-rail">
            {historyTools}
          </div>
        </div>

        {stepsBlock}

        <p className="form-hint visible-layer-editor-context-hint">
          {phase === 'refine'
            ? (previewMode ? v.refineHintPreview : v.refineHintFull)
            : addHint}
          {phase === 'place' && addLayer === 'blur_bar' && blurCount >= MAX_BLUR_BARS && fmt(v.maxBlurBars, { max: MAX_BLUR_BARS })}
        </p>
      </div>
    </div>
  )
})

export default VisibleLayerEditor
