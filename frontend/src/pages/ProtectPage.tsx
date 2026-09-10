import { useState, useCallback, useEffect, useMemo, useRef, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import {
  type JwCreationType,
  type JwWriteHint,
} from '../content/jingweiProtocol'
import ImageUpload from '../components/ImageUpload'
// DisplacementAnchor removed — seed-based repositioning used instead
import Accordion from '../components/Accordion'
import RadioPills, { HelpTip } from '../components/RadioPills'
import Slider from '../components/Slider'
import ImageLightbox from '../components/ImageLightbox'
import FeedbackHelpLink from '../components/FeedbackHelpLink'
import { JwIcon } from '../components/jw/JwIcon'
import JingweiMiniIcon from '../components/JingweiMiniIcon'
import { prepareImageForUpload, formatResizeNotice, type ImageUploadCopy, type PreparedImage } from '../utils/imageResize'
import { dataUrlToUint8, downloadProtectedImage, downloadUrl } from '../utils/downloadDataUrl'
import { isRevocableObjectUrl } from '../lib/protectMemory'
import { HoloCard } from '../holo-card/HoloCard'
import { translateApiError } from '../lib/apiErrors'
import { formatClientError } from '../lib/clientErrors'
import jingweiBird from '../assets/jingwei-bird.png'
import VisibleLayerEditor, {
  type VisibleAddPlacement,
  type AvailableLayer,
  type VisibleLayerEditorHandle,
  type SelectedBlur,
} from '../components/VisibleLayerEditor'
import ProtectUnsavedDialog from '../components/ProtectUnsavedDialog'
import ProtectMaskRetainDialog, { type MaskRetainReason } from '../components/ProtectMaskRetainDialog'
import LegalConsentGate, { useLegalAccepted } from '../components/LegalConsentGate'
import { usePageSeo } from '../hooks/usePageSeo'
import { localeUsesLatinJwFields } from '../i18n/types'
import { useLocale } from '../i18n/LocaleContext'
import { getToken } from '../lib/auth'
import {
  CREDIT_DISP_FONT_RATIO,
  CREDIT_DISP_SHADOW_STRENGTH,
  CREDIT_DISP_SHIFT,
  creditUsesAscii as creditMarkUsesAscii,
  nextCreditVisibleLayers,
  creditVisibleName,
  stripCreditDispPlacements,
  type CreditVisibleMark,
} from '../lib/creditVisibleLayers'
import { PROTECT_PAGE_CANONICAL, SITE_NAME } from '../lib/site'

function MaybeAccordion({
  wrap,
  title,
  children,
}: {
  wrap: boolean
  title: string
  children: ReactNode
}) {
  if (!wrap) return <>{children}</>
  return (
    <Accordion title={title} defaultOpen={false}>
      {children}
    </Accordion>
  )
}

interface Metrics {
  psnr: number | null
  ssim: number
  max_diff: number
  mean_diff: number
}

type JwVisibleMode = 'none' | 'badge' | 'footer'

interface PendingVisibleEdits {
  eraseMask: Blob | null
  placements: VisibleAddPlacement[]
  blurMask: Blob | null
}

interface ProcessOverrides {
  dispSeed?: number
  feSeed?: number
  dispAnchor?: { x: number; y: number } | null
  visibleEraseMask?: Blob | null
  visibleAddPlacements?: VisibleAddPlacement[]
  visibleAddBlurMask?: Blob | null
  blurRegionMask?: Blob | null
  /** Use only the explicit visible-edit fields below — never merge editor/pending fallbacks. */
  forceCommittedVisibleEdits?: boolean
  /** Always append visible-edit fields from overrides (save-then-protect). */
  commitVisibleEdits?: boolean
  halftoneAnchor?: { x: number; y: number } | null
}


type HalftoneStyle = 'ascii_chars' | 'halftone_dots'

const DEFAULT_HALFTONE_ANCHOR = { x: 0.5, y: 0.54 }

/** 字符风格固定开启：背景字母链 + 轮廓错位（与 core/halftone_protect 对齐，不可 UI 调节）。 */
const HALFTONE_ASCII_BACKGROUND_CHAIN = 78
const HALFTONE_ASCII_CONTOUR_WARP = 70

function halftoneAnchorFromPlacements(
  placements: VisibleAddPlacement[] | undefined,
): { x: number; y: number } | null {
  const p = placements?.find(item => item.layer === 'halftone_signature')
  return p ? { x: p.x, y: p.y } : null
}

function resolveHalftoneAnchor(
  placements: VisibleAddPlacement[] | undefined,
  halftoneOn: boolean,
): { x: number; y: number } | null {
  if (!halftoneOn) return null
  return halftoneAnchorFromPlacements(placements) ?? DEFAULT_HALFTONE_ANCHOR
}

function logoAnchorFromPosition(pos: LogoPosition): { x: number; y: number } {
  switch (pos) {
    case 'bottom_left':
      return { x: 0.18, y: 0.82 }
    case 'top_right':
      return { x: 0.82, y: 0.18 }
    case 'top_left':
      return { x: 0.18, y: 0.18 }
    case 'center':
      return { x: 0.5, y: 0.5 }
    default:
      return { x: 0.82, y: 0.82 }
  }
}

/** 浅字符「居中」对齐现有 center_low（水平居中、约 54% 高），角落与 Logo 同一套。 */
function asciiAnchorFromPosition(pos: LogoPosition): { x: number; y: number } {
  if (pos === 'center') return { ...DEFAULT_HALFTONE_ANCHOR }
  return logoAnchorFromPosition(pos)
}

function resolveLogoAnchor(
  placements: VisibleAddPlacement[] | undefined,
  logoOn: boolean,
): { x: number; y: number } | null {
  if (!logoOn) return null
  const p = placements?.find(item => item.layer === 'logo')
  return p ? { x: p.x, y: p.y } : null
}

function appendHalftoneFields(
  fd: FormData,
  opts: {
    enabled: boolean
    text: string
    style: HalftoneStyle
    size: number
    density: number
    visibility: number
    anchor: { x: number; y: number } | null
    signature: number
    signatureSize: number
    dotTexture: number
  },
) {
  fd.append('halftone_enabled', String(opts.enabled && Boolean(opts.text.trim())))
  fd.append('halftone_style', opts.style)
  fd.append('halftone_text', opts.text)
  fd.append('halftone_size', String(opts.size))
  fd.append('halftone_density', String(opts.density))
  fd.append('halftone_visibility', String(opts.visibility))
  fd.append('halftone_anchor_x', opts.anchor ? String(opts.anchor.x) : '-1')
  fd.append('halftone_anchor_y', opts.anchor ? String(opts.anchor.y) : '-1')
  fd.append('halftone_signature', String(opts.signature))
  fd.append('halftone_signature_size', String(opts.signatureSize))
  fd.append('halftone_dot_texture', String(opts.dotTexture))
  fd.append('halftone_background_chain', String(HALFTONE_ASCII_BACKGROUND_CHAIN))
  fd.append('halftone_contour_warp', String(HALFTONE_ASCII_CONTOUR_WARP))
}

type LogoTint = 'original' | 'gray' | 'white'
type LogoPosition = 'bottom_right' | 'bottom_left' | 'top_right' | 'top_left' | 'center'

function appendLogoFields(
  fd: FormData,
  opts: {
    enabled: boolean
    file: File | null
    opacity: number
    scale: number
    position: LogoPosition
    tint: LogoTint
    anchor?: { x: number; y: number } | null
  },
) {
  const on = opts.enabled && Boolean(opts.file)
  fd.append('logo_enabled', String(on))
  if (on && opts.file) fd.append('logo_image', opts.file)
  fd.append('logo_opacity', String(opts.opacity))
  fd.append('logo_scale', String(opts.scale))
  fd.append('logo_position', opts.position)
  fd.append('logo_anchor_x', opts.anchor ? String(opts.anchor.x) : '-1')
  fd.append('logo_anchor_y', opts.anchor ? String(opts.anchor.y) : '-1')
  fd.append('logo_tint', opts.tint)
}


function revokeObjectUrlIfNeeded(url: string | null | undefined): void {
  if (isRevocableObjectUrl(url)) URL.revokeObjectURL(url)
}

function adoptObjectUrl(next: string | null, slot: { current: string | null }): string | null {
  if (slot.current && slot.current !== next) revokeObjectUrlIfNeeded(slot.current)
  slot.current = next
  return next
}

function dataUrlToDisplayUrl(raw: string): string {
  if (raw.startsWith('blob:') || !raw.startsWith('data:')) return raw
  const { mime, bytes } = dataUrlToUint8(raw)
  const copy = new Uint8Array(bytes.byteLength)
  copy.set(bytes)
  return URL.createObjectURL(new Blob([copy.buffer], { type: mime || 'image/jpeg' }))
}

async function resultImageToFile(resultImg: string): Promise<File> {
  if (resultImg.startsWith('data:')) {
    const { mime, bytes } = dataUrlToUint8(resultImg)
    const copy = new Uint8Array(bytes.byteLength)
    copy.set(bytes)
    return new File([copy], 'protected.png', { type: mime || 'image/png' })
  }
  const res = await fetch(resultImg)
  const blob = await res.blob()
  return new File([blob], 'protected.png', { type: blob.type || 'image/png' })
}


function pendingVisibleEditPayload(edits: PendingVisibleEdits | null | undefined): boolean {
  return Boolean(
    edits?.eraseMask
    || edits?.blurMask
    || (edits?.placements?.length ?? 0) > 0,
  )
}

function commitOverridesFromEdits(edits: PendingVisibleEdits): ProcessOverrides {
  return {
    commitVisibleEdits: true,
    visibleEraseMask: edits.eraseMask,
    visibleAddPlacements: edits.placements,
    visibleAddBlurMask: edits.blurMask,
  }
}

function blobToUploadFile(blob: Blob | null | undefined, filename: string): File | null {
  if (!blob) return null
  if (blob instanceof File && blob.name) return blob
  return new File([blob], filename, { type: blob.type || 'image/png' })
}

export default function ProtectPage() {
  return (
    <LegalConsentGate>
      <ProtectPageInner />
    </LegalConsentGate>
  )
}

function fmt(template: string, vars: Record<string, string | number>) {
  return Object.entries(vars).reduce((s, [k, v]) => s.replace(`{${k}}`, String(v)), template)
}

function ProtectPageInner() {
  const { messages: m, jw, locale } = useLocale()
  const t = m.protect
  const f = t.form
  const uploadCopy = m.components.imageUpload as ImageUploadCopy
  const o = t.modeOptions
  const apiErr = useCallback((data: { error_code?: string; error?: string }, fallback: string) => {
    const translated = translateApiError(locale, data.error_code, data.error)
    return translated || data.error || fallback
  }, [locale])
  const modeOptions = useMemo(() => [
    { label: o.credit, value: 'credit', hint: f.modeHelpCredit },
    { label: o.stealth, value: 'stealth', hint: f.modeHelpStealth },
  ], [o, f.modeHelpCredit, f.modeHelpStealth])
  const creditMarkOptions = useMemo(() => [
    { label: f.visibleMarkAuto, value: 'auto', hint: f.visibleMarkAutoHint },
    { label: f.visibleMarkAscii, value: 'ascii', hint: f.visibleMarkAsciiHint },
    { label: f.visibleMarkDisplacement, value: 'displacement', hint: f.visibleMarkDispHint },
  ], [f.visibleMarkAuto, f.visibleMarkAscii, f.visibleMarkDisplacement, f.visibleMarkAutoHint, f.visibleMarkAsciiHint, f.visibleMarkDispHint])
  const dispModeOptions = useMemo(() => [
    { label: o.band, value: 'band' },
    { label: o.scatter, value: 'scatter' },
    { label: o.tile, value: 'tile' },
  ], [o])
  const dispDensityOptions = useMemo(() => [
    { label: o.sparse, value: 'sparse' },
    { label: o.normal, value: 'normal' },
    { label: o.dense, value: 'dense' },
  ], [o])
  const logoPositionOptions = useMemo(() => [
    { label: f.logoPosBr, value: 'bottom_right' },
    { label: f.logoPosBl, value: 'bottom_left' },
    { label: f.logoPosTr, value: 'top_right' },
    { label: f.logoPosTl, value: 'top_left' },
    { label: f.logoPosCenter, value: 'center' },
  ], [f])
  const embossPatternOptions = useMemo(() => [
    { label: o.diagonal, value: 'diagonal' },
    { label: o.halftone, value: 'halftone' },
    { label: o.crosshatch, value: 'crosshatch' },
  ], [o])
  const embossStrengthOptions = useMemo(() => [
    { label: o.light, value: 'light' },
    { label: o.medium, value: 'medium' },
    { label: o.strong, value: 'strong' },
  ], [o])
  const formatOptions = useMemo(() => [
    { label: t.labels.outputPng, value: 'png' },
    { label: t.labels.outputJpg, value: 'jpg' },
  ], [t.labels])
  const sigPosOptions = useMemo(() => [
    { label: o.bottomRight, value: 'bottom_right' },
    { label: o.bottomLeft, value: 'bottom_left' },
    { label: o.topRight, value: 'top_right' },
    { label: o.topLeft, value: 'top_left' },
  ], [o])
  const blurRegionOptions = useMemo(() => [
    { label: o.blurBar, value: 'bar' },
    { label: o.blurBrush, value: 'brush' },
  ], [o])
  const describePreviewHttpError = useCallback((status: number) => {
    if (status === 429) return t.errors.rateLimited
    if (status === 413) return t.errors.imageTooLargePreview
    if (status >= 500) return t.errors.previewBusy
    return t.errors.previewRetry
  }, [t.errors])
  const {
    JW_PROTECT_INTRO,
    JW_PROTECT_PIXEL_REWARD,
    JW_PNG_HINT,
    JW_PROTECT_LIMITS,
    JW_CORE_BELIEF_SUMMARY,
    JW_DWT_RELATION,
    JW_INVISIBLE_INTRO,
    JW_EMBED_METHOD_LABEL,
    JW_CREATION_OPTIONS,
    JW_RESTRICTION_FLAGS,
    formatBadgePreview,
  } = jw
  usePageSeo({
    title: `${t.pageTitle} · ${SITE_NAME}`,
    description: t.metaDescription,
    canonical: PROTECT_PAGE_CANONICAL,
  })
  const accepted = useLegalAccepted()
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [processing, setProcessing] = useState(false)
  const [unsavedProtectDialogOpen, setUnsavedProtectDialogOpen] = useState(false)
  const [maskRetainDialogOpen, setMaskRetainDialogOpen] = useState(false)
  const [maskRetainReason, setMaskRetainReason] = useState<MaskRetainReason>('backToPlace')

  // Results
  const [resultImg, setResultImg] = useState<string | null>(null)
  const [holoLoading, setHoloLoading] = useState(false)
  const [holoError, setHoloError] = useState('')
  const [comparison, setComparison] = useState<string | null>(null)
  const [lightboxSrc, setLightboxSrc] = useState<string | null>(null)
  const [lightboxAlt, setLightboxAlt] = useState<string>('')

  const openLightbox = useCallback((src: string, alt: string) => {
    setLightboxSrc(src)
    setLightboxAlt(alt)
  }, [])
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [qualityLabel, setQualityLabel] = useState('')
  const [qualityText, setQualityText] = useState('')
  const [status, setStatus] = useState('')
  const [resizeNotice, setResizeNotice] = useState('')
  const [uploadDims, setUploadDims] = useState<{ w: number; h: number } | null>(null)
  const anchorMinEdge = 128
  const uploadTooSmallForAnchor = uploadDims != null && Math.min(uploadDims.w, uploadDims.h) < anchorMinEdge
  const [error, setError] = useState('')
  const [jwQuotaNotice, setJwQuotaNotice] = useState<string | null>(null)
  const [layersApplied, setLayersApplied] = useState<{
    jw: boolean
    dwt: boolean
    lsb: boolean
    track: boolean
    jwEmbedTier: string | null
    jwEmbedMethod: string | null
  } | null>(null)
  const [hasAlpha, setHasAlpha] = useState(false)
  const [visibleEditorKey, setVisibleEditorKey] = useState(0)
  // Bumped to push parent-computed default boxes into the editor (e.g. enabling
  // 位移整词 seeds 3 dashed boxes, 模糊条 seeds N boxes).
  const [placementSeedKey, setPlacementSeedKey] = useState(0)
  // Imperative handle + selected-bar size, so the LEFT panel sliders can resize
  // whichever blur bar is selected on the right canvas.
  const visibleEditorRef = useRef<VisibleLayerEditorHandle>(null)
  const [selectedBlur, setSelectedBlur] = useState<SelectedBlur | null>(null)

  // Settings
  const [mode, setMode] = useState('credit')
  const [creditMark, setCreditMark] = useState<CreditVisibleMark>('auto')
  const [autoTimestamp, setAutoTimestamp] = useState(true)
  const [dwtPayload, setDwtPayload] = useState('')
  const [watermarkText, setWatermarkText] = useState('')
  const [signatureText, setSignatureText] = useState('')
  const [signaturePos, setSignaturePos] = useState('bottom_right')
  const [artist, setArtist] = useState('')
  const [embedMeta, setEmbedMeta] = useState(true)
  const [deliveryText] = useState('')
  const [outputFormat, setOutputFormat] = useState('png')

  // Displacement
  const [dispEnabled, setDispEnabled] = useState(false)
  const [dispText, setDispText] = useState('')
  const [dispMode, setDispMode] = useState('band')
  const [dispFontRatio, setDispFontRatio] = useState(0.15)
  const [dispShift, setDispShift] = useState(10)
  const [dispShadowStrength, setDispShadowStrength] = useState(0.35)
  const [dispDensity, setDispDensity] = useState('normal')
  const [dispSeed, setDispSeed] = useState(42)
  const [dispShadow, setDispShadow] = useState(true)
  const [dispAnchor, setDispAnchor] = useState<{ x: number; y: number } | null>(null)

  // Face emboss
  const [feEnabled, setFeEnabled] = useState(false)
  const [feText, setFeText] = useState('')
  const [feCopies, setFeCopies] = useState(3)
  const [feShift, setFeShift] = useState(12)
  const [feOpacity, setFeOpacity] = useState(0.25)
  const [fePatchRatio, setFePatchRatio] = useState(0.30)
  const [feSeed] = useState(42)

  // Emboss texture
  const [embossEnabled, setEmbossEnabled] = useState(false)
  const [embossPattern, setEmbossPattern] = useState('diagonal')
  const [embossStrength, setEmbossStrength] = useState('medium')
  const [embossText, setEmbossText] = useState('')
  const [embossTextDensity] = useState('dense')

  // Blur bar
  const [blurEnabled, setBlurEnabled] = useState(false)
  const [blurY] = useState(0.5)
  const [blurCount, setBlurCount] = useState(1)
  const [blurSigma, setBlurSigma] = useState(12)
  const [blurText, setBlurText] = useState('')
  const [blurRegionMode, setBlurRegionMode] = useState<'bar' | 'brush'>('bar')
  const blurRegionExportRef = useRef<(() => Promise<Blob | null>) | null>(null)

  // Displacement logo (silhouette pushes host pixels)
  const [logoEnabled, setLogoEnabled] = useState(false)
  const [logoFile, setLogoFile] = useState<File | null>(null)
  const [logoTint] = useState<LogoTint>('gray')
  const [logoPosition, setLogoPosition] = useState<LogoPosition>('bottom_right')
  const [asciiPosition, setAsciiPosition] = useState<LogoPosition>('center')
  const [logoOpacityPct, setLogoOpacityPct] = useState(40)
  const [logoSizePct, setLogoSizePct] = useState(18)

  // ASCII watermark (characters / halftone dots)
  const [halftoneEnabled, setHalftoneEnabled] = useState(false)
  const [halftoneStyle, setHalftoneStyle] = useState<HalftoneStyle>('ascii_chars')
  const [halftoneText, setHalftoneText] = useState('')
  const [halftoneSize, setHalftoneSize] = useState(50)
  const [halftoneDensity, setHalftoneDensity] = useState(50)
  const [halftoneVisibility, setHalftoneVisibility] = useState(50)
  const [halftoneSignature, setHalftoneSignature] = useState(50)
  const [halftoneSignatureSize, setHalftoneSignatureSize] = useState(50)
  const [halftoneDotTexture, setHalftoneDotTexture] = useState(0)
  const [livePreviewImg, setLivePreviewImg] = useState<string | null>(null)
  const [livePreviewLoading, setLivePreviewLoading] = useState(false)
  const [livePreviewError, setLivePreviewError] = useState('')
  const [pendingVisibleEdits, setPendingVisibleEdits] = useState<PendingVisibleEdits | null>(null)
  const previewRequestIdRef = useRef(0)
  const previewAbortRef = useRef<AbortController | null>(null)
  /** 参数变更且存在擦除/涂抹时，先弹窗再刷新预览（见 previewConfig effect）。 */
  const pendingParamPreviewRef = useRef<PendingVisibleEdits | null | undefined>(undefined)
  const pendingVisibleEditsRef = useRef<PendingVisibleEdits | null>(null)
  pendingVisibleEditsRef.current = pendingVisibleEdits
  const lastAppliedVisibleEditsRef = useRef<PendingVisibleEdits | null>(null)
  const placementsSyncRef = useRef<VisibleAddPlacement[] | null>(null)

  // Traceability anchor (追踪巩固) — survives social-media screenshots
  const [trackEnabled, setTrackEnabled] = useState(false)

  // Jingwei Protocol
  const [jwEnabled, setJwEnabled] = useState(false)
  const [jwWriteHint, setJwWriteHint] = useState<JwWriteHint | null>(null)
  const [jwCreation, setJwCreation] = useState<JwCreationType>('OC')
  const [jwRestrictions, setJwRestrictions] = useState<string[]>(['NO-TR', 'NO-ED'])
  const [jwVisibleMode, setJwVisibleMode] = useState<JwVisibleMode>('none')

  const previewUrlRef = useRef<string | null>(null)
  const resultUrlRef = useRef<string | null>(null)
  const comparisonUrlRef = useRef<string | null>(null)
  const livePreviewUrlRef = useRef<string | null>(null)
  const preparedUploadRef = useRef<{ key: string; prepared: PreparedImage } | null>(null)
  const revokePreviewUrl = useCallback(() => {
    if (previewUrlRef.current) {
      URL.revokeObjectURL(previewUrlRef.current)
      previewUrlRef.current = null
    }
  }, [])
  const clearResultDisplay = useCallback(() => {
    adoptObjectUrl(null, resultUrlRef)
    adoptObjectUrl(null, comparisonUrlRef)
    setResultImg(null)
    setComparison(null)
    setLightboxSrc(null)
  }, [])
  const clearLivePreviewDisplay = useCallback(() => {
    adoptObjectUrl(null, livePreviewUrlRef)
    setLivePreviewImg(null)
  }, [])
  const invalidatePreviewRequest = useCallback(() => {
    previewAbortRef.current?.abort()
    previewAbortRef.current = null
    previewRequestIdRef.current += 1
    setLivePreviewLoading(false)
  }, [])
  const fileCacheKey = (f: File) => `${f.name}:${f.size}:${f.lastModified}`
  const ensurePreparedUpload = useCallback(async (f: File): Promise<PreparedImage> => {
    const key = fileCacheKey(f)
    if (preparedUploadRef.current?.key === key) return preparedUploadRef.current.prepared
    const prepared = await prepareImageForUpload(f, uploadCopy)
    preparedUploadRef.current = { key: fileCacheKey(prepared.file), prepared }
    return prepared
  }, [uploadCopy])

  const toggleJwRestriction = (id: string) => {
    setJwRestrictions(prev =>
      prev.includes(id) ? prev.filter(r => r !== id) : [...prev, id]
    )
  }

  useEffect(() => {
    if (jwEnabled) setDwtPayload('')
  }, [jwEnabled])

  useEffect(() => () => { revokePreviewUrl() }, [revokePreviewUrl])

  const fetchJwWriteHint = useCallback(async (f: File, stampText?: string) => {
    const fd = new FormData()
    fd.append('image', f)
    if (stampText?.trim()) fd.append('displacement_text', stampText.trim())
    try {
      const res = await fetch('/api/protect/jw-hint', { method: 'POST', body: fd })
      const data = await res.json()
      if (data.ok) {
        setJwWriteHint({
          kind: data.kind,
          flat_ratio: data.flat_ratio,
          texture_ratio: data.texture_ratio,
          summary: data.summary,
          suggest: data.suggest,
          credit_disp_x: data.credit_disp_x,
          credit_disp_y: data.credit_disp_y,
          credit_disp_w: data.credit_disp_w,
          credit_disp_h: data.credit_disp_h,
        })
      } else {
        setJwWriteHint(null)
      }
    } catch {
      setJwWriteHint(null)
    }
  }, [])

  const isCredit = mode === 'credit'
  const creditLogoScale = isCredit ? 0.08 : logoSizePct / 100

  useEffect(() => {
    if (isCredit) {
      setJwEnabled(true)
      setEmbedMeta(true)
      setDispMode('band')
      setDispFontRatio(CREDIT_DISP_FONT_RATIO)
      setDispShift(CREDIT_DISP_SHIFT)
      setDispShadow(true)
      setDispShadowStrength(CREDIT_DISP_SHADOW_STRENGTH)
    }
  }, [isCredit])

  useEffect(() => {
    if (file && (jwEnabled || isCredit)) {
      void fetchJwWriteHint(file)
    } else {
      setJwWriteHint(null)
    }
  }, [file, jwEnabled, isCredit, fetchJwWriteHint])

  const creditRecipeKeyRef = useRef('')
  useEffect(() => {
    if (!isCredit || !file || !jwWriteHint) return
    const key = `${file.name}:${file.size}:${file.lastModified}:${jwWriteHint.kind}:${creditMark}`
    if (creditRecipeKeyRef.current === key) return
    creditRecipeKeyRef.current = key
    const layers = nextCreditVisibleLayers(creditMark, jwWriteHint.kind)
    if (layers.asciiEnabled) {
      setHalftoneEnabled(true)
      setHalftoneStyle('ascii_chars')
      setHalftoneVisibility(8)
      setHalftoneSignature(0)
      setDispEnabled(false)
    } else {
      setHalftoneEnabled(false)
      setDispEnabled(true)
      setDispMode('band')
      setDispFontRatio(layers.dispFontRatio)
      setDispShift(layers.dispShift)
      setDispShadow(layers.dispShadow)
      setDispShadowStrength(layers.dispShadowStrength)
    }
  }, [isCredit, file, jwWriteHint, creditMark])

  const creditUsesAscii = isCredit && creditMarkUsesAscii(creditMark, jwWriteHint?.kind)
  const creditUsesDisp = isCredit && !creditUsesAscii && (
    creditMark === 'displacement' || (creditMark === 'auto' && jwWriteHint?.kind !== 'flat')
  )
  const creditStampText = creditVisibleName(dispText, artist)

  useEffect(() => {
    if (!creditUsesDisp) return
    setDispEnabled(true)
    setHalftoneEnabled(false)
    setDispFontRatio(CREDIT_DISP_FONT_RATIO)
    setDispShift(CREDIT_DISP_SHIFT)
    setDispShadow(true)
    setDispShadowStrength(CREDIT_DISP_SHADOW_STRENGTH)
  }, [creditUsesDisp])

  const onLogoFileChange = (next: File | null) => {
    setLogoFile(next)
    if (next) setLogoEnabled(true)
  }

  const handleFile = useCallback(async (f: File) => {
    if (!accepted) return
    revokePreviewUrl()
    invalidatePreviewRequest()
    clearLivePreviewDisplay()
    clearResultDisplay()
    preparedUploadRef.current = null
    setFile(null)
    setMetrics(null)
    setDispAnchor(null)
    setResizeNotice('')
    setUploadDims(null)
    setError('')
    setLayersApplied(null)
    setJwWriteHint(null)
    try {
      const prepared = await ensurePreparedUpload(f)
      const url = URL.createObjectURL(prepared.file)
      previewUrlRef.current = url
      setFile(prepared.file)
      setPreview(url)
      setUploadDims({ w: prepared.width, h: prepared.height })
      setResizeNotice(formatResizeNotice(prepared, uploadCopy))
      setError('')
    } catch (e: unknown) {
      setFile(null)
      setPreview(null)
      setUploadDims(null)
      setError(formatClientError(locale, e, t.errors.preprocessFailed))
    }
    const isPng = f.type === 'image/png'
    if (isPng) {
      const img = new window.Image()
      img.onload = () => {
        const cvs = document.createElement('canvas')
        cvs.width = Math.min(img.width, 64)
        cvs.height = Math.min(img.height, 64)
        const ctx = cvs.getContext('2d')!
        ctx.drawImage(img, 0, 0, cvs.width, cvs.height)
        const data = ctx.getImageData(0, 0, cvs.width, cvs.height).data
        let transparent = false
        for (let i = 3; i < data.length; i += 4) {
          if (data[i] < 250) { transparent = true; break }
        }
        setHasAlpha(transparent)
      }
      img.src = previewUrlRef.current ?? ''
    } else {
      setHasAlpha(false)
    }
  }, [
    accepted, revokePreviewUrl, uploadCopy, locale, t.errors.preprocessFailed,
    ensurePreparedUpload, invalidatePreviewRequest, clearLivePreviewDisplay, clearResultDisplay,
  ])

  const clearFile = useCallback(() => {
    invalidatePreviewRequest()
    revokePreviewUrl()
    clearLivePreviewDisplay()
    clearResultDisplay()
    preparedUploadRef.current = null
    setFile(null)
    setPreview(null)
    setMetrics(null)
    setDispAnchor(null)
    setResizeNotice('')
    setUploadDims(null)
    setPendingVisibleEdits(null)
    lastAppliedVisibleEditsRef.current = null
    placementsSyncRef.current = null
    creditRecipeKeyRef.current = ''
  }, [revokePreviewUrl, invalidatePreviewRequest, clearLivePreviewDisplay, clearResultDisplay])

  const halftoneOn = halftoneEnabled && Boolean(halftoneText.trim())
  /** 波点须摆锚点；满屏字符织入网格，不挡 Logo / 署名预览。 */
  const halftonePlacementEnabled = halftoneOn
  const halftoneDotsFullTexture = halftoneDotTexture >= 50

  const halftoneStyleOptions = useMemo(() => [
    { value: 'ascii_chars' as HalftoneStyle, title: f.halftoneStyleAscii, desc: f.halftoneStyleAsciiDesc },
    { value: 'halftone_dots' as HalftoneStyle, title: f.halftoneStyleDots, desc: f.halftoneStyleDotsDesc },
  ], [f])

  const halftoneDensityLabel = useMemo(() => {
    if (halftoneStyle === 'ascii_chars') return f.halftoneDensityAscii
    if (halftoneDotsFullTexture) return f.halftoneDensityFine
    return f.halftoneDensityDots
  }, [halftoneStyle, halftoneDotsFullTexture, f])

  const halftoneSizeLabel = useMemo(() => {
    if (halftoneStyle === 'ascii_chars') return f.halftoneSizeAscii
    if (halftoneDotsFullTexture) return f.halftoneSizeFine
    return f.halftoneSizeDots
  }, [halftoneStyle, halftoneDotsFullTexture, f])

  const halftoneSizeHint = useMemo(() => {
    if (halftoneStyle === 'ascii_chars') return f.halftoneSizeAsciiHint
    if (halftoneDotsFullTexture) return f.halftoneSizeFineHint
    return f.halftoneSizeDotsHint
  }, [halftoneStyle, halftoneDotsFullTexture, f])

  const halftoneDensityHint = useMemo(() => {
    if (halftoneStyle === 'ascii_chars') return f.halftoneDensityAsciiHint
    if (halftoneDotsFullTexture) return f.halftoneDensityFineHint
    return f.halftoneDensityDotsHint
  }, [halftoneStyle, halftoneDotsFullTexture, f])

  const halftoneSignatureHint = useMemo(() => {
    if (halftoneStyle === 'ascii_chars') return f.halftoneSignatureHintAscii
    if (halftoneDotsFullTexture) return f.halftoneSignatureHintFine
    return f.halftoneSignatureHintDots
  }, [halftoneStyle, halftoneDotsFullTexture, f])

  const hasVisibleLayers = useMemo(
    () =>
      (dispEnabled && Boolean(isCredit ? creditStampText : dispText.trim()))
      || halftoneOn
      || blurEnabled
      || embossEnabled
      || (feEnabled && Boolean(feText.trim()))
      || Boolean(signatureText.trim()),
    [dispEnabled, dispText, creditStampText, isCredit, halftoneOn, blurEnabled, embossEnabled, feEnabled, feText, signatureText],
  )

  const trackArtist = useMemo(() => {
    const s = t.trackSources
    const candidates = [
      { value: artist.trim(), source: s.artist },
      { value: dwtPayload.trim(), source: s.dwt },
      { value: watermarkText.trim(), source: s.lsb },
      { value: signatureText.trim(), source: s.signature },
      ...(halftoneOn ? [{ value: halftoneText.trim(), source: s.halftone }] : []),
    ]
    return candidates.find(c => c.value) ?? null
  }, [artist, dwtPayload, watermarkText, signatureText, halftoneOn, halftoneText, t.trackSources])

  const hasTrackPreview = trackEnabled && Boolean(trackArtist?.value)
  const logoOn = logoEnabled && Boolean(logoFile)
  const needsLivePreview = hasVisibleLayers || hasTrackPreview || logoOn

  // Box-flow layers are "drag-first": the user places dashed boxes on the clean
  // image and only then clicks 生成预览. When one is active we must NOT let the
  // anchor live-preview auto-render immediately — that would yank the user out
  // of the placement step. (集中整词 / 模糊整条 / 脸部浮雕.)
  const hasPendingBoxFlow = useMemo(
    () =>
      (!isCredit && dispEnabled && Boolean(dispText.trim()) && dispMode === 'band')
      || (blurEnabled && blurRegionMode === 'bar')
      || (feEnabled && Boolean(feText.trim()))
      || halftonePlacementEnabled,
    [dispEnabled, dispText, dispMode, blurEnabled, blurRegionMode, feEnabled, feText, halftonePlacementEnabled, isCredit],
  )

  const handleProcess = useCallback(async (overrides?: ProcessOverrides) => {
    if (!file || !accepted) return
    if (dispEnabled && !(isCredit ? creditStampText : dispText.trim())) {
      setError(t.errors.visibleTextRequired)
      return
    }
    if (halftoneEnabled && !(isCredit ? creditStampText : halftoneText.trim())) {
      setError(t.errors.halftoneTextRequired)
      return
    }
    if (logoEnabled && !logoFile) {
      setError(t.errors.logoFileRequired)
      return
    }
    const sentVisibleEdits = Boolean(
      overrides?.commitVisibleEdits
      || overrides?.forceCommittedVisibleEdits
      || pendingVisibleEditPayload({
        eraseMask: overrides?.visibleEraseMask ?? pendingVisibleEditsRef.current?.eraseMask ?? null,
        placements: overrides?.visibleAddPlacements ?? pendingVisibleEditsRef.current?.placements ?? [],
        blurMask: overrides?.visibleAddBlurMask ?? pendingVisibleEditsRef.current?.blurMask ?? null,
      }),
    )
    setProcessing(true)
    setError('')
    invalidatePreviewRequest()

    const seed = overrides?.dispSeed ?? dispSeed
    const feS = overrides?.feSeed ?? feSeed
    const anchor = overrides?.dispAnchor !== undefined ? overrides.dispAnchor : dispAnchor
    const htAnchor = overrides?.halftoneAnchor !== undefined
      ? overrides.halftoneAnchor
      : resolveHalftoneAnchor(
        overrides?.visibleAddPlacements ?? pendingVisibleEdits?.placements,
        halftoneOn,
      )
    const logoAnchor = resolveLogoAnchor(
      overrides?.visibleAddPlacements ?? pendingVisibleEdits?.placements,
      logoEnabled && Boolean(logoFile),
    )

    let uploadFile: File
    try {
      const prepared = await ensurePreparedUpload(file)
      uploadFile = prepared.file
      setResizeNotice(formatResizeNotice(prepared, uploadCopy))
    } catch (e: any) {
      setError(e.message || t.errors.preprocessFailed)
      setProcessing(false)
      return
    }

    const fd = new FormData()
    fd.append('image', uploadFile)
    fd.append('mode', mode)
    fd.append('visible_mark', isCredit ? creditMark : 'auto')
    fd.append('auto_timestamp', String(autoTimestamp))
    if (!jwEnabled) {
      fd.append('dwt_payload', dwtPayload)
    }
    fd.append('watermark_text', watermarkText.trim() || (isCredit ? artist.trim() : ''))
    fd.append('signature_text', signatureText)
    fd.append('signature_position', signaturePos)
    fd.append('artist', artist)
    fd.append('embed_metadata', String(embedMeta))
    fd.append('delivery_text', deliveryText)
    fd.append('output_format', outputFormat)
    fd.append('displacement_enabled', String(dispEnabled && Boolean(isCredit ? creditStampText : dispText.trim())))
    fd.append('displacement_text', isCredit ? creditStampText : dispText)
    fd.append('displacement_mode', dispMode)
    fd.append('displacement_font_ratio', String(dispFontRatio))
    fd.append('displacement_shift', String(dispShift))
    fd.append('displacement_density', dispDensity)
    fd.append('displacement_seed', String(seed))
    fd.append('displacement_shadow', String(dispShadow))
    fd.append('displacement_shadow_strength', String(dispShadowStrength))
    fd.append('displacement_anchor_x', anchor ? String(anchor.x) : '-1')
    fd.append('displacement_anchor_y', anchor ? String(anchor.y) : '-1')
    fd.append('face_emboss_enabled', String(feEnabled && Boolean(feText.trim())))
    fd.append('face_emboss_text', feText)
    fd.append('face_emboss_copies', String(feCopies))
    fd.append('face_emboss_shift', String(feShift))
    fd.append('face_emboss_opacity', String(feOpacity))
    fd.append('face_emboss_patch_ratio', String(fePatchRatio))
    fd.append('face_emboss_seed', String(feS))
    fd.append('emboss_enabled', String(embossEnabled))
    fd.append('emboss_pattern', embossPattern)
    fd.append('emboss_strength', embossStrength)
    fd.append('emboss_text', embossText)
    fd.append('emboss_text_density', embossTextDensity)
    fd.append('blur_bar_enabled', String(blurEnabled))
    fd.append('blur_bar_y_ratio', String(blurY))
    fd.append('blur_bar_count', String(blurCount))
    fd.append('blur_bar_sigma', String(blurSigma))
    fd.append('blur_bar_text', blurText)
    appendHalftoneFields(fd, {
      enabled: halftoneEnabled,
      text: isCredit ? creditStampText : halftoneText,
      style: halftoneStyle,
      size: halftoneSize,
      density: halftoneDensity,
      visibility: halftoneVisibility,
      anchor: htAnchor,
      signature: halftoneSignature,
      signatureSize: halftoneSignatureSize,
      dotTexture: halftoneDotTexture,
    })
    appendLogoFields(fd, {
      enabled: logoEnabled,
      file: logoFile,
      opacity: logoOpacityPct / 100,
      scale: creditLogoScale,
      position: logoPosition,
      tint: logoTint,
      anchor: logoAnchor,
    })

    // Jingwei Protocol
    fd.append('jw_enabled', String(jwEnabled))
    fd.append('track_enabled', String(trackEnabled))
    fd.append('track_artist', trackArtist?.value ?? '')
    fd.append('jw_embed_priority', 'auto')
    fd.append('jw_creation', jwCreation)
    fd.append('jw_restrictions', jwRestrictions.join(','))
    fd.append('jw_badge', String(jwVisibleMode === 'badge'))
    fd.append('jw_footer_strip', String(jwVisibleMode === 'footer'))

    if (overrides?.commitVisibleEdits) {
      fd.append('visible_edits_requested', 'true')
      const eraseFile = blobToUploadFile(overrides.visibleEraseMask, 'visible-erase.png')
      if (eraseFile) fd.append('visible_erase_mask', eraseFile)
      fd.append('visible_add_points', JSON.stringify(stripCreditDispPlacements(isCredit, overrides.visibleAddPlacements ?? [])))
      const blurFile = blobToUploadFile(overrides.visibleAddBlurMask, 'visible-add-blur.png')
      if (blurFile) fd.append('visible_add_blur_mask', blurFile)
    } else if (overrides?.forceCommittedVisibleEdits) {
      fd.append('visible_edits_requested', 'true')
      const eraseFile = blobToUploadFile(overrides.visibleEraseMask, 'visible-erase.png')
      if (eraseFile) fd.append('visible_erase_mask', eraseFile)
      fd.append('visible_add_points', JSON.stringify(stripCreditDispPlacements(isCredit, overrides.visibleAddPlacements ?? [])))
      const blurFile = blobToUploadFile(overrides.visibleAddBlurMask, 'visible-add-blur.png')
      if (blurFile) fd.append('visible_add_blur_mask', blurFile)
    } else {
      const eraseBlob = overrides?.visibleEraseMask ?? pendingVisibleEdits?.eraseMask ?? null
      const eraseFile = blobToUploadFile(eraseBlob, 'visible-erase.png')
      if (eraseFile) fd.append('visible_erase_mask', eraseFile)
      if (overrides?.visibleAddPlacements?.length) {
        fd.append('visible_add_points', JSON.stringify(stripCreditDispPlacements(isCredit, overrides.visibleAddPlacements)))
      } else if (pendingVisibleEdits?.placements.length) {
        fd.append('visible_add_points', JSON.stringify(stripCreditDispPlacements(isCredit, pendingVisibleEdits.placements)))
      }
      const blurBlob = overrides?.visibleAddBlurMask ?? pendingVisibleEdits?.blurMask ?? null
      const blurFile = blobToUploadFile(blurBlob, 'visible-add-blur.png')
      if (blurFile) fd.append('visible_add_blur_mask', blurFile)
    }
    if (overrides?.blurRegionMask) {
      fd.append('blur_region_mask', overrides.blurRegionMask, 'blur-region.png')
    } else if (
      blurEnabled
      && blurRegionMode !== 'bar'
      && blurRegionExportRef.current
      && !overrides?.commitVisibleEdits
      && !overrides?.visibleEraseMask
      && !overrides?.visibleAddPlacements?.length
    ) {
      const regionBlob = await blurRegionExportRef.current()
      if (regionBlob) {
        fd.append('blur_region_mask', regionBlob, 'blur-region.png')
      }
    }

    try {
      const headers: HeadersInit = {}
      const token = getToken()
      if (token) headers['Authorization'] = `Bearer ${token}`
      const res = await fetch('/api/protect', { method: 'POST', body: fd, headers })
      const contentType = res.headers.get('content-type') || ''
      if (!contentType.includes('application/json')) {
        const text = await res.text()
        throw new Error(text.slice(0, 200) || `HTTP ${res.status}`)
      }
      const data = await res.json()
      if (data.ok) {
        clearLivePreviewDisplay()
        const nextResult = typeof data.image === 'string' ? dataUrlToDisplayUrl(data.image) : null
        const nextComparison = typeof data.comparison === 'string' ? dataUrlToDisplayUrl(data.comparison) : null
        setResultImg(adoptObjectUrl(nextResult, resultUrlRef))
        setComparison(adoptObjectUrl(nextComparison, comparisonUrlRef))
        setMetrics(data.metrics)
        setQualityLabel(data.quality_label)
        setQualityText(data.quality_text)
        setStatus(data.status || '')
        setLayersApplied({
          jw: Boolean(data.jw_applied),
          dwt: Boolean(data.dwt_applied),
          lsb: Boolean(data.lsb_applied),
          track: Boolean(data.track_applied),
          jwEmbedTier: data.jw_embed_tier ?? null,
          jwEmbedMethod: data.jw_embed_method ?? null,
        })
        if (data.jw_quota?.jw_works_incremented) {
          setJwQuotaNotice(
            fmt(t.jwQuota.recorded, { allowance: data.jw_quota.daily_allowance }),
          )
        } else if (data.jw_applied && !getToken()) {
          setJwQuotaNotice(t.jwQuota.loginHint)
        } else {
          setJwQuotaNotice(null)
        }
        if (sentVisibleEdits) {
          // Erase/blur strokes are baked into the new frame; drop masks so a later
          // protect pass does not re-apply them on top of the committed output.
          setPendingVisibleEdits(prev => {
            const next = prev && prev.placements.length
              ? { eraseMask: null, placements: prev.placements, blurMask: null }
              : null
            lastAppliedVisibleEditsRef.current = next
            return next
          })
          visibleEditorRef.current?.markSaved()
          setVisibleEditorKey(k => k + 1)
        } else {
          // A non-visible-edit reprocess (e.g. 开始保护) remounts the editor with
          // an empty canvas. Drop only the stale erase/blur brush strokes (which
          // are tied to the old frame) but KEEP the dashed-box placements, so the
          // result editor still shows them and 保存修改 re-renders from the same
          // boxes — they are the watermark, not throwaway state.
          setVisibleEditorKey(k => k + 1)
          setPendingVisibleEdits(prev =>
            prev && (prev.placements.length || prev.blurMask)
              ? { eraseMask: null, placements: prev.placements, blurMask: prev.blurMask }
              : null,
          )
        }
      } else {
        setError(apiErr(data, t.errors.processFailed))
      }
    } catch (e: any) {
      setError(formatClientError(locale, e, t.errors.networkError))
    } finally {
      setProcessing(false)
    }
  }, [file, accepted, mode, autoTimestamp, dwtPayload, watermarkText, signatureText, signaturePos,
      artist, embedMeta, deliveryText, outputFormat, dispEnabled, dispText, dispMode,
      dispFontRatio, dispShift, dispDensity, dispSeed, dispShadow, dispShadowStrength, dispAnchor,
      halftoneEnabled, halftoneText, halftoneStyle, halftoneOn, halftoneSize, halftoneDensity,
      halftoneVisibility, halftoneSignature, halftoneSignatureSize, halftoneDotTexture,
      feEnabled, feText, feCopies,
      feShift, feOpacity, fePatchRatio, feSeed, embossEnabled, embossPattern,
      embossStrength, embossText, embossTextDensity, blurEnabled, blurY, blurCount,
      blurSigma, blurText, blurRegionMode, jwEnabled, trackEnabled, trackArtist, jwCreation, jwRestrictions, jwVisibleMode, pendingVisibleEdits,
      logoEnabled, logoFile, logoTint, logoPosition, logoOpacityPct, logoSizePct,
      creditMark, isCredit, creditStampText,
      uploadCopy, apiErr, locale, t.errors, ensurePreparedUpload,
      invalidatePreviewRequest, clearLivePreviewDisplay])

  const visibleLayers = useMemo((): AvailableLayer[] => [
    // Adding a displacement stamp on the right always renders as "band" (multi
    // strip) on the server, so only offer it when the left mode is band too —
    // in scatter mode it would be misleading, hence no placeholder box there.
    { id: 'displacement', label: t.labels.displacement, enabled: !isCredit && dispEnabled && Boolean(dispText.trim()) && dispMode === 'band' },
    { id: 'blur_bar', label: t.labels.blurBar, enabled: blurEnabled && blurRegionMode === 'bar' },
    { id: 'emboss', label: t.labels.emboss, enabled: embossEnabled },
    { id: 'face_emboss', label: t.labels.faceEmboss, enabled: feEnabled && Boolean(feText.trim()) },
    { id: 'halftone_signature', label: m.components.visibleLayerEditor.halftoneSignature, enabled: halftonePlacementEnabled },
    { id: 'logo', label: m.components.visibleLayerEditor.logoMark, enabled: logoOn },
  ], [dispEnabled, dispText, dispMode, isCredit, blurEnabled, blurRegionMode, embossEnabled, feEnabled, feText, halftonePlacementEnabled, logoOn, m.components.visibleLayerEditor.halftoneSignature, m.components.visibleLayerEditor.logoMark, t.labels])

  const appendVisiblePreviewFields = useCallback((
    fd: FormData,
    uploadFile: File,
    dispSeedOverride?: number,
    anchorPlacements?: VisibleAddPlacement[],
  ) => {
    fd.append('image', uploadFile)
    fd.append('mode', mode)
    fd.append('visible_mark', isCredit ? creditMark : 'auto')
    fd.append('signature_text', signatureText)
    fd.append('signature_position', signaturePos)
    fd.append('displacement_enabled', String(dispEnabled && Boolean(isCredit ? creditStampText : dispText.trim())))
    fd.append('displacement_text', isCredit ? creditStampText : dispText)
    fd.append('displacement_mode', dispMode)
    fd.append('displacement_font_ratio', String(dispFontRatio))
    fd.append('displacement_shift', String(dispShift))
    fd.append('displacement_density', dispDensity)
    fd.append('displacement_seed', String(dispSeedOverride ?? dispSeed))
    fd.append('displacement_shadow', String(dispShadow))
    fd.append('displacement_shadow_strength', String(dispShadowStrength))
    fd.append('displacement_anchor_x', dispAnchor ? String(dispAnchor.x) : '-1')
    fd.append('displacement_anchor_y', dispAnchor ? String(dispAnchor.y) : '-1')
    fd.append('face_emboss_enabled', String(feEnabled && Boolean(feText.trim())))
    fd.append('face_emboss_text', feText)
    fd.append('face_emboss_copies', String(feCopies))
    fd.append('face_emboss_shift', String(feShift))
    fd.append('face_emboss_opacity', String(feOpacity))
    fd.append('face_emboss_patch_ratio', String(fePatchRatio))
    fd.append('face_emboss_seed', String(feSeed))
    fd.append('emboss_enabled', String(embossEnabled))
    fd.append('emboss_pattern', embossPattern)
    fd.append('emboss_strength', embossStrength)
    fd.append('emboss_text', embossText)
    fd.append('emboss_text_density', embossTextDensity)
    fd.append('blur_bar_enabled', String(blurEnabled))
    fd.append('blur_bar_y_ratio', String(blurY))
    fd.append('blur_bar_count', String(blurCount))
    fd.append('blur_bar_sigma', String(blurSigma))
    fd.append('blur_bar_text', blurText)
    fd.append('jw_footer_preview', String(jwEnabled && jwVisibleMode === 'footer'))
    fd.append('jw_creation', jwCreation)
    fd.append('jw_restrictions', jwRestrictions.join(','))
    fd.append('jw_footer_artist', artist)
    fd.append('track_enabled', String(trackEnabled))
    fd.append('track_artist', trackArtist?.value ?? '')
    fd.append('artist', artist)
    fd.append('dwt_payload', dwtPayload)
    fd.append('watermark_text', watermarkText)
    fd.append('signature_text', signatureText)
    fd.append('auto_timestamp', String(autoTimestamp))
    appendHalftoneFields(fd, {
      enabled: halftoneEnabled,
      text: isCredit ? creditStampText : halftoneText,
      style: halftoneStyle,
      size: halftoneSize,
      density: halftoneDensity,
      visibility: halftoneVisibility,
      anchor: resolveHalftoneAnchor(
        anchorPlacements ?? pendingVisibleEditsRef.current?.placements,
        halftoneOn,
      ),
      signature: halftoneSignature,
      signatureSize: halftoneSignatureSize,
      dotTexture: halftoneDotTexture,
    })
    appendLogoFields(fd, {
      enabled: logoEnabled,
      file: logoFile,
      opacity: logoOpacityPct / 100,
      scale: creditLogoScale,
      position: logoPosition,
      tint: logoTint,
      anchor: resolveLogoAnchor(
        anchorPlacements ?? pendingVisibleEditsRef.current?.placements,
        logoEnabled && Boolean(logoFile),
      ),
    })
  }, [
    mode, signatureText, signaturePos, dispEnabled, dispText, dispMode, dispFontRatio,
    dispShift, dispDensity, dispSeed, dispShadow, dispShadowStrength, dispAnchor, feEnabled, feText, feCopies,
    feShift, feOpacity, fePatchRatio, feSeed, embossEnabled, embossPattern, embossStrength,
    embossText, embossTextDensity, blurEnabled, blurY, blurCount, blurSigma, blurText,
    jwEnabled, jwVisibleMode, jwCreation, jwRestrictions, artist, trackEnabled, trackArtist,
    dwtPayload, watermarkText, signatureText, autoTimestamp,
    halftoneEnabled, halftoneText, halftoneStyle, halftoneOn, halftoneSize, halftoneDensity,
    halftoneVisibility, halftoneSignature, halftoneSignatureSize, halftoneDotTexture,
    logoEnabled, logoFile, logoTint, logoPosition, logoOpacityPct, logoSizePct,
    creditMark, isCredit, creditStampText,
  ])

  const appendVisibleEditFields = useCallback((
    fd: FormData,
    edits: PendingVisibleEdits | null | undefined,
  ) => {
    if (!edits) return
    if (pendingVisibleEditPayload(edits)) {
      fd.append('visible_edits_requested', 'true')
    }
    const eraseFile = blobToUploadFile(edits.eraseMask, 'visible-erase.png')
    if (eraseFile) fd.append('visible_erase_mask', eraseFile)
    fd.append('visible_add_points', JSON.stringify(stripCreditDispPlacements(isCredit, edits.placements ?? [])))
    const blurFile = blobToUploadFile(edits.blurMask, 'visible-add-blur.png')
    if (blurFile) fd.append('visible_add_blur_mask', blurFile)
  }, [isCredit])

  const fetchLivePreview = useCallback(async (editOverride?: PendingVisibleEdits | null, dispSeedOverride?: number) => {
    if (!file || !needsLivePreview) return
    previewAbortRef.current?.abort()
    const requestId = ++previewRequestIdRef.current
    const controller = new AbortController()
    previewAbortRef.current = controller
    setLivePreviewLoading(true)
    setLivePreviewError('')
    try {
      const prepared = await ensurePreparedUpload(file)
      const fd = new FormData()
      const edits = editOverride === null
        ? null
        : (editOverride ?? pendingVisibleEditsRef.current)
      appendVisiblePreviewFields(fd, prepared.file, dispSeedOverride, edits?.placements)
      if (blurEnabled && blurRegionMode !== 'bar' && blurRegionExportRef.current) {
        const regionBlob = await blurRegionExportRef.current()
        if (regionBlob) {
          fd.append('blur_region_mask', regionBlob, 'blur-region.png')
        }
      }
      appendVisibleEditFields(fd, edits)
      const res = await fetch('/api/protect/preview', {
        method: 'POST',
        body: fd,
        signal: controller.signal,
      })
      if (requestId !== previewRequestIdRef.current) return

      const contentType = res.headers.get('content-type') || ''
      const isJson = contentType.includes('application/json')
      if (isJson) {
        const data = await res.json() as { ok?: boolean; error?: string; error_code?: string; preview?: string }
        if (requestId !== previewRequestIdRef.current) return
        if (res.ok && data.ok && data.preview) {
          const previewUrl = dataUrlToDisplayUrl(data.preview)
          if (requestId !== previewRequestIdRef.current) {
            revokeObjectUrlIfNeeded(previewUrl)
            return
          }
          setLivePreviewImg(adoptObjectUrl(previewUrl, livePreviewUrlRef))
          setLivePreviewError('')
          if (edits && (edits.eraseMask || edits.blurMask)) {
            visibleEditorRef.current?.markSaved()
            setVisibleEditorKey(k => k + 1)
          }
          return
        }
        setLivePreviewError(
          apiErr(data, t.errors.previewFailed) || data.error || describePreviewHttpError(res.status),
        )
        return
      }

      if (!res.ok) {
        setLivePreviewError(describePreviewHttpError(res.status))
      }
    } catch (e: unknown) {
      if (e instanceof DOMException && e.name === 'AbortError') return
      if (requestId !== previewRequestIdRef.current) return
      const isNetwork = e instanceof TypeError
        || (e instanceof Error && /failed to fetch|networkerror|load failed|econnrefused|connection refused/i.test(e.message))
      setLivePreviewError(isNetwork ? m.clientErrors.networkFailed : formatClientError(locale, e, t.errors.previewRetry))
    } finally {
      if (requestId === previewRequestIdRef.current) {
        setLivePreviewLoading(false)
      }
    }
  }, [
    file, needsLivePreview, appendVisiblePreviewFields, appendVisibleEditFields,
    blurEnabled, blurRegionMode, ensurePreparedUpload, apiErr, t.errors, m.clientErrors,
    locale, describePreviewHttpError,
    halftoneEnabled, halftoneText,
  ])

  // 换一组位置 (scatter displacement only): reshuffle the random seed AND show the
  // result right away — re-protect if a result exists, else refresh the live
  // preview with the new seed so the user never has to click 生成预览 a second time.
  const bumpDispSeed = useCallback(() => {
    const next = dispSeed + 1
    setDispSeed(next)
    if (!file) return
    if (resultImg) {
      handleProcess({ dispSeed: next })
    } else {
      void fetchLivePreview(undefined, next)
    }
  }, [dispSeed, file, resultImg, handleProcess, fetchLivePreview])

  const syncVisibleEdits = useCallback((
    mask: Blob | null,
    placements: VisibleAddPlacement[],
    blurMask: Blob | null,
  ): PendingVisibleEdits => {
    const keptBlur = blurMask ?? pendingVisibleEditsRef.current?.blurMask ?? null
    const edits: PendingVisibleEdits = { eraseMask: mask, placements, blurMask: keptBlur }
    placementsSyncRef.current = placements
    lastAppliedVisibleEditsRef.current = edits
    setPendingVisibleEdits(edits)
    return edits
  }, [])

  const handleVisibleEditUpdatePreview = useCallback(
    (mask: Blob | null, placements: VisibleAddPlacement[], blurMask: Blob | null) => {
      if (!file) return
      const edits = syncVisibleEdits(mask, placements, blurMask)
      void fetchLivePreview(edits)
    },
    [file, syncVisibleEdits, fetchLivePreview],
  )

  const handleVisibleEditApply = useCallback(
    (mask: Blob | null, placements: VisibleAddPlacement[], blurMask: Blob | null) => {
      if (!file) return
      const edits = syncVisibleEdits(mask, placements, blurMask)
      visibleEditorRef.current?.markSaved()
      // Placement stage (no baked preview yet): generate visible preview only.
      // After preview exists or on the result frame: commit edits via full protect.
      if (!resultImg && !livePreviewImg) {
        void fetchLivePreview(edits)
      } else {
        void handleProcess(commitOverridesFromEdits(edits))
      }
    },
    [file, resultImg, livePreviewImg, syncVisibleEdits, handleProcess, fetchLivePreview],
  )



  const hasStoredVisibleMasks = useCallback((): boolean => {
    const pending = pendingVisibleEditsRef.current
    return Boolean(pending?.eraseMask || pending?.blurMask)
  }, [])

  const mergeUnsavedEditsIntoPending = useCallback(async (): Promise<void> => {
    if (!visibleEditorRef.current?.hasUnsavedChanges()) return
    const exported = await visibleEditorRef.current.exportEdits()
    if (!exported) return
    const keptBlur = exported.blurMask ?? pendingVisibleEditsRef.current?.blurMask ?? null
    const edits: PendingVisibleEdits = {
      eraseMask: exported.mask,
      placements: exported.placements,
      blurMask: keptBlur,
    }
    placementsSyncRef.current = edits.placements
    lastAppliedVisibleEditsRef.current = edits
    setPendingVisibleEdits(edits)
    visibleEditorRef.current?.markSaved()
  }, [])

  const clearStoredVisibleMasks = useCallback(() => {
    setPendingVisibleEdits(prev => {
      if (!prev) return null
      const next = prev.placements.length
        ? { eraseMask: null, placements: prev.placements, blurMask: null }
        : null
      lastAppliedVisibleEditsRef.current = next
      return next
    })
    visibleEditorRef.current?.revertToSaved()
    setVisibleEditorKey(k => k + 1)
  }, [])

  const hasVisibleMaskEditsPending = useCallback((): boolean => {
    if (hasStoredVisibleMasks()) return true
    return visibleEditorRef.current?.hasUnsavedChanges() ?? false
  }, [hasStoredVisibleMasks])

  const previewEditorActive = Boolean(file && preview && (hasVisibleLayers || logoOn)) || Boolean(resultImg)

  const hasUnsavedPreviewEdits = useCallback((): boolean => {
    if (!previewEditorActive) return false
    return visibleEditorRef.current?.hasUnsavedChanges() ?? false
  }, [previewEditorActive])

  const buildDiscardVisibleOverrides = useCallback((): ProcessOverrides => {
    visibleEditorRef.current?.revertToSaved()
    const saved = lastAppliedVisibleEditsRef.current
    return {
      forceCommittedVisibleEdits: true,
      visibleEraseMask: saved?.eraseMask ?? null,
      visibleAddPlacements: visibleEditorRef.current?.getPlacements() ?? saved?.placements ?? [],
      visibleAddBlurMask: saved?.blurMask ?? null,
    }
  }, [])

  const buildProtectVisibleOverrides = useCallback(async (): Promise<ProcessOverrides | undefined> => {
    if (visibleEditorRef.current?.hasUnsavedChanges()) {
      const exported = await visibleEditorRef.current.exportEdits()
      if (exported) {
        const keptBlur = exported.blurMask ?? pendingVisibleEditsRef.current?.blurMask ?? null
        const edits: PendingVisibleEdits = {
          eraseMask: exported.mask,
          placements: exported.placements,
          blurMask: keptBlur,
        }
        placementsSyncRef.current = edits.placements
        lastAppliedVisibleEditsRef.current = edits
        setPendingVisibleEdits(edits)
        visibleEditorRef.current?.markSaved()
        return commitOverridesFromEdits(edits)
      }
    }
    const pending = pendingVisibleEditsRef.current
    if (pendingVisibleEditPayload(pending)) {
      return commitOverridesFromEdits(pending!)
    }
    return undefined
  }, [])

  const handleStartProtectClick = useCallback(async () => {
    if (hasUnsavedPreviewEdits()) {
      setUnsavedProtectDialogOpen(true)
      return
    }
    const overrides = await buildProtectVisibleOverrides()
    void handleProcess(overrides)
  }, [hasUnsavedPreviewEdits, handleProcess, buildProtectVisibleOverrides])

  const handleUnsavedSaveAndProtect = useCallback(async () => {
    setUnsavedProtectDialogOpen(false)
    const exported = await visibleEditorRef.current?.exportEdits()
    if (!exported) {
      await handleProcess()
      return
    }
    const keptBlur = exported.blurMask ?? pendingVisibleEditsRef.current?.blurMask ?? null
    const edits: PendingVisibleEdits = {
      eraseMask: exported.mask,
      placements: exported.placements,
      blurMask: keptBlur,
    }
    placementsSyncRef.current = edits.placements
    lastAppliedVisibleEditsRef.current = edits
    setPendingVisibleEdits(edits)
    visibleEditorRef.current?.markSaved()
    await handleProcess(commitOverridesFromEdits(edits))
  }, [handleProcess])

  const handleUnsavedDiscardAndProtect = useCallback(() => {
    setUnsavedProtectDialogOpen(false)
    void handleProcess(buildDiscardVisibleOverrides())
  }, [handleProcess, buildDiscardVisibleOverrides])

  const handleUnsavedProtectCancel = useCallback(() => {
    setUnsavedProtectDialogOpen(false)
  }, [])

  const handleVisibleEditClear = useCallback(() => {
    const htKeep = halftonePlacementEnabled
      ? [{ layer: 'halftone_signature' as const, ...asciiAnchorFromPosition(asciiPosition) }]
      : []
    const logoKeep = logoOn
      ? [{ layer: 'logo' as const, ...logoAnchorFromPosition(logoPosition) }]
      : []
    const keep = [...htKeep, ...logoKeep]
    const next = keep.length
      ? { eraseMask: null, placements: keep, blurMask: null }
      : null
    setPendingVisibleEdits(next)
    lastAppliedVisibleEditsRef.current = next
    setPlacementSeedKey(k => k + 1)
    setSelectedBlur(null)
    if (!resultImg) {
      void fetchLivePreview(next)
    }
  }, [resultImg, fetchLivePreview, logoOn, logoPosition, halftonePlacementEnabled, asciiPosition])

  // 返回摆放: drop the rendered preview/result so the clean image with editable
  // marks comes back (placements are kept in pendingVisibleEdits).
  const resetPreviewStage = useCallback((opts?: { keepPending?: boolean }) => {
    invalidatePreviewRequest()
    clearResultDisplay()
    clearLivePreviewDisplay()
    setLivePreviewError('')
    setLivePreviewLoading(false)
    if (!opts?.keepPending) {
      setPendingVisibleEdits(null)
      lastAppliedVisibleEditsRef.current = null
      placementsSyncRef.current = null
      setVisibleEditorKey(k => k + 1)
    }
  }, [invalidatePreviewRequest, clearResultDisplay, clearLivePreviewDisplay])

  const handleBackToPlace = useCallback(() => {
    resetPreviewStage({ keepPending: true })
  }, [resetPreviewStage])

  const requestBackToPlace = useCallback(() => {
    if (hasVisibleMaskEditsPending()) {
      setMaskRetainReason('backToPlace')
      setMaskRetainDialogOpen(true)
      return
    }
    handleBackToPlace()
  }, [hasVisibleMaskEditsPending, handleBackToPlace])

  const closeMaskRetainDialog = useCallback(() => {
    setMaskRetainDialogOpen(false)
  }, [])

  const handleMaskRetainKeep = useCallback(async () => {
    await mergeUnsavedEditsIntoPending()
    setMaskRetainDialogOpen(false)
    if (maskRetainReason === 'backToPlace') {
      handleBackToPlace()
      return
    }
    if (maskRetainReason === 'paramChange') {
      const edits = pendingParamPreviewRef.current ?? pendingVisibleEditsRef.current
      pendingParamPreviewRef.current = undefined
      if (resultImg) clearResultDisplay()
      void fetchLivePreview(edits ?? null)
    }
  }, [mergeUnsavedEditsIntoPending, maskRetainReason, handleBackToPlace, resultImg, fetchLivePreview, clearResultDisplay])

  const handleMaskRetainDiscard = useCallback(() => {
    clearStoredVisibleMasks()
    setMaskRetainDialogOpen(false)
    if (maskRetainReason === 'backToPlace') {
      handleBackToPlace()
      return
    }
    if (maskRetainReason === 'paramChange') {
      pendingParamPreviewRef.current = undefined
      if (resultImg) clearResultDisplay()
      void fetchLivePreview(null)
    }
  }, [clearStoredVisibleMasks, maskRetainReason, handleBackToPlace, resultImg, fetchLivePreview, clearResultDisplay])

  // Resize the blur bar that is selected on the right canvas.
  const handleSelectedBlurResize = useCallback((w: number, h: number) => {
    setSelectedBlur({ w, h })
    visibleEditorRef.current?.resizeSelected(w, h)
  }, [])

  // Remember dashed-box placements as soon as they change, so clicking
  // 开始保护 (before any result exists) applies them in one shot — no need to
  // press 生成预览 first (optional).
  const handlePlacementsChange = useCallback((placements: VisibleAddPlacement[]) => {
    placementsSyncRef.current = placements
    setPendingVisibleEdits(prev => {
      const prevPlacements = prev?.placements ?? []
      if (
        prevPlacements.length === placements.length
        && prevPlacements.every((pp, i) =>
          pp.layer === placements[i].layer
          && pp.x === placements[i].x
          && pp.y === placements[i].y
          && pp.w === placements[i].w
          && pp.h === placements[i].h)
      ) {
        return prev
      }
      return {
        eraseMask: prev?.eraseMask ?? null,
        placements,
        blurMask: prev?.blurMask ?? null,
      }
    })
  }, [])

  // Auto-seed default dashed boxes the moment a box-flow layer is enabled, so
  // the user sees draggable placeholders on the right immediately — no need to
  // click 添加水印. 位移整词 → 3 boxes; 模糊条(整条横向) → N boxes by count.
  // Boxes become the single source of truth; the server skips that layer's
  // automatic render (see protect.py), so there is never a duplicate.
  const dispSeededRef = useRef(false)
  const blurSeededRef = useRef(false)
  const feSeededRef = useRef(false)
  const htSeededRef = useRef(false)
  const logoSeededRef = useRef(false)
  const lastLogoPosRef = useRef<LogoPosition>(logoPosition)
  const lastAsciiPosRef = useRef<LogoPosition>(asciiPosition)
  const prevHalftoneStyleRef = useRef<HalftoneStyle>(halftoneStyle)
  const embossSeededRef = useRef(false)
  const lastBlurCountRef = useRef(blurCount)
  const previewConfigRef = useRef({
    mode,
    creditMark,
    dispMode,
    dispDensity,
    dispFontRatio,
    dispShift,
    dispShadow,
    dispShadowStrength,
    dispText,
    feCopies,
    feShift,
    feOpacity,
    fePatchRatio,
    feText,
    embossPattern,
    embossStrength,
    embossText,
    embossTextDensity,
    blurSigma,
    blurY,
    blurText,
    halftoneStyle,
    halftoneSize,
    halftoneDensity,
    halftoneVisibility,
    halftoneSignature,
    halftoneSignatureSize,
    halftoneDotTexture,
    halftoneText,
    logoEnabled,
    logoFileKey: logoFile ? `${logoFile.name}:${logoFile.size}:${logoFile.lastModified}` : '',
    logoTint,
    logoPosition,
    logoOpacityPct,
    logoSizePct,
  })
  useEffect(() => {
    const dispOn = !isCredit && dispEnabled && Boolean(dispText.trim()) && dispMode === 'band'
    const blurOn = blurEnabled && blurRegionMode === 'bar'
    const feOn = feEnabled && Boolean(feText.trim())
    const htOn = halftonePlacementEnabled
    const embossOn = embossEnabled
    // One placement = one word. Seed a single centered box; the user adds more
    // by clicking if they want extras. 署名·快速 displacement is auto-placed.
    const makeDispBoxes = (): VisibleAddPlacement[] =>
      [{ layer: 'displacement', x: 0.5, y: 0.5 }]
    // One placement = one patch. Seed a single box; the user drags it onto the
    // face (or adds more by clicking). Avoid auto-spreading onto the face.
    const makeFeBoxes = (): VisibleAddPlacement[] =>
      [{ layer: 'face_emboss', x: 0.5, y: 0.5 }]
    const makeHalftoneBoxes = (): VisibleAddPlacement[] =>
      [{ layer: 'halftone_signature', ...asciiAnchorFromPosition(asciiPosition) }]
    const makeEmbossBoxes = (): VisibleAddPlacement[] =>
      [{ layer: 'emboss', x: 0.5, y: 0.5 }]
    const makeLogoBox = (): VisibleAddPlacement =>
      ({ layer: 'logo', ...logoAnchorFromPosition(logoPosition) })
    const makeBlurBoxes = (n: number): VisibleAddPlacement[] => {
      const count = Math.max(1, Math.min(5, Math.round(n)))
      const w = 0.6
      const h = 0.07
      return Array.from({ length: count }, (_, i) => {
        const cy = count === 1 ? 0.5 : (i + 1) / (count + 1)
        return {
          layer: 'blur_bar' as const,
          x: (1 - w) / 2,
          y: Math.max(0, Math.min(1 - h, cy - h / 2)),
          w,
          h,
        }
      })
    }
    // Read the current snapshot synchronously (functional setState updaters may
    // be deferred, so we must decide "changed" here, not inside the updater).
    const prev = pendingVisibleEditsRef.current
    let placements = prev?.placements ?? []
    let changed = false
    if (dispOn && !dispSeededRef.current) {
      placements = [...placements.filter(p => p.layer !== 'displacement'), ...makeDispBoxes()]
      changed = true
    } else if (!dispOn && (dispSeededRef.current || (isCredit && placements.some(p => p.layer === 'displacement')))) {
      placements = placements.filter(p => p.layer !== 'displacement')
      changed = true
    }
    if (blurOn && !blurSeededRef.current) {
      placements = [...placements.filter(p => p.layer !== 'blur_bar'), ...makeBlurBoxes(blurCount)]
      lastBlurCountRef.current = blurCount
      changed = true
    } else if (!blurOn && blurSeededRef.current) {
      placements = placements.filter(p => p.layer !== 'blur_bar')
      changed = true
    } else if (blurOn && blurSeededRef.current && lastBlurCountRef.current !== blurCount) {
      placements = [...placements.filter(p => p.layer !== 'blur_bar'), ...makeBlurBoxes(blurCount)]
      lastBlurCountRef.current = blurCount
      changed = true
    }
    if (feOn && !feSeededRef.current) {
      placements = [...placements.filter(p => p.layer !== 'face_emboss'), ...makeFeBoxes()]
      changed = true
    } else if (!feOn && feSeededRef.current) {
      placements = placements.filter(p => p.layer !== 'face_emboss')
      changed = true
    }
    if (htOn && !htSeededRef.current) {
      placements = [...placements.filter(p => p.layer !== 'halftone_signature'), ...makeHalftoneBoxes()]
      lastAsciiPosRef.current = asciiPosition
      changed = true
    } else if (!htOn && htSeededRef.current) {
      placements = placements.filter(p => p.layer !== 'halftone_signature')
      changed = true
    } else if (htOn && htSeededRef.current && lastAsciiPosRef.current !== asciiPosition) {
      placements = [...placements.filter(p => p.layer !== 'halftone_signature'), ...makeHalftoneBoxes()]
      lastAsciiPosRef.current = asciiPosition
      changed = true
    }
    if (embossOn && !embossSeededRef.current) {
      placements = [...placements.filter(p => p.layer !== 'emboss'), ...makeEmbossBoxes()]
      changed = true
    } else if (!embossOn && embossSeededRef.current) {
      placements = placements.filter(p => p.layer !== 'emboss')
      changed = true
    }
    if (logoOn && !logoSeededRef.current) {
      placements = [...placements.filter(p => p.layer !== 'logo'), makeLogoBox()]
      lastLogoPosRef.current = logoPosition
      changed = true
    } else if (!logoOn && logoSeededRef.current) {
      placements = placements.filter(p => p.layer !== 'logo')
      changed = true
    } else if (logoOn && logoSeededRef.current && lastLogoPosRef.current !== logoPosition) {
      placements = [...placements.filter(p => p.layer !== 'logo'), makeLogoBox()]
      lastLogoPosRef.current = logoPosition
      changed = true
    }
    dispSeededRef.current = dispOn
    blurSeededRef.current = blurOn
    feSeededRef.current = feOn
    htSeededRef.current = htOn
    embossSeededRef.current = embossOn
    logoSeededRef.current = logoOn
    if (!changed) return
    const nextEdits: PendingVisibleEdits = {
      eraseMask: prev?.eraseMask ?? null,
      placements,
      blurMask: prev?.blurMask ?? null,
    }
    setPendingVisibleEdits(nextEdits)
    lastAppliedVisibleEditsRef.current = nextEdits
    setPlacementSeedKey(k => k + 1)
    if (livePreviewImg || resultImg) {
      if (resultImg) clearResultDisplay()
      void fetchLivePreview(nextEdits)
    } else {
      resetPreviewStage({ keepPending: true })
    }
  }, [
    dispEnabled, dispText, dispMode, blurEnabled, blurRegionMode, blurCount,
    feEnabled, feText, halftonePlacementEnabled, asciiPosition, embossEnabled, logoOn, logoPosition,
    isCredit,
    resetPreviewStage, livePreviewImg, resultImg,
    fetchLivePreview, clearResultDisplay,
  ])

  useEffect(() => {
    if (prevHalftoneStyleRef.current === halftoneStyle) return
    prevHalftoneStyleRef.current = halftoneStyle
    clearLivePreviewDisplay()
    clearResultDisplay()
  }, [halftoneStyle, clearLivePreviewDisplay, clearResultDisplay])

  // Left-panel render tweaks refresh the live preview when a frame is already shown.
  useEffect(() => {
    if (!file || !preview) return
    const prev = previewConfigRef.current
    const next = {
      mode,
      creditMark,
      dispMode,
      dispDensity,
      dispFontRatio,
      dispShift,
      dispShadow,
      dispShadowStrength,
      dispText,
      feCopies,
      feShift,
      feOpacity,
      fePatchRatio,
      feText,
      embossPattern,
      embossStrength,
      embossText,
      embossTextDensity,
      blurSigma,
      blurY,
      blurText,
      halftoneStyle,
      halftoneSize,
      halftoneDensity,
      halftoneVisibility,
      halftoneSignature,
      halftoneSignatureSize,
      halftoneDotTexture,
      halftoneText,
      logoEnabled,
      logoFileKey: logoFile ? `${logoFile.name}:${logoFile.size}:${logoFile.lastModified}` : '',
      logoTint,
      logoPosition,
      logoOpacityPct,
      logoSizePct,
    }
    const renderChanged = (Object.keys(next) as (keyof typeof next)[]).some(k => prev[k] !== next[k])
    previewConfigRef.current = next
    if (!renderChanged || !(livePreviewImg || resultImg)) return

    const timer = window.setTimeout(() => {
      void (async () => {
        let editsForPreview = pendingVisibleEditsRef.current
        if (prev.dispMode !== dispMode) {
          const p = pendingVisibleEditsRef.current
          if (p) {
            const normalized = {
              eraseMask: p.eraseMask,
              placements: p.placements.filter(pl => pl.layer !== 'displacement'),
              blurMask: p.blurMask,
            }
            editsForPreview = (normalized.placements.length || normalized.eraseMask || normalized.blurMask)
              ? normalized
              : null
          } else {
            editsForPreview = null
          }
          lastAppliedVisibleEditsRef.current = editsForPreview
          setPendingVisibleEdits(editsForPreview)
          setPlacementSeedKey(k => k + 1)
        }
        const hadMaskEdits = Boolean(
          editsForPreview?.eraseMask
          || editsForPreview?.blurMask
          || visibleEditorRef.current?.hasUnsavedChanges(),
        )
        if (visibleEditorRef.current?.hasUnsavedChanges()) {
          await mergeUnsavedEditsIntoPending()
          editsForPreview = pendingVisibleEditsRef.current
        }
        if (hadMaskEdits) {
          pendingParamPreviewRef.current = editsForPreview
          setMaskRetainReason('paramChange')
          setMaskRetainDialogOpen(true)
          return
        }
        if (resultImg) clearResultDisplay()
        void fetchLivePreview(editsForPreview)
      })()
    }, 300)
    return () => window.clearTimeout(timer)
  }, [
    file, preview, mode, creditMark, dispEnabled, dispMode, dispDensity, dispFontRatio, dispShift, dispShadow, dispShadowStrength, dispText,
    feCopies, feShift, feOpacity, fePatchRatio, feText,
    embossPattern, embossStrength, embossText, embossTextDensity,
    blurSigma, blurY, blurText,
    halftoneStyle, halftoneSize, halftoneDensity, halftoneVisibility,
    halftoneSignature, halftoneSignatureSize, halftoneDotTexture, halftoneText,
    logoEnabled, logoFile, logoTint, logoPosition, logoOpacityPct, logoSizePct,
    livePreviewImg, resultImg, fetchLivePreview, mergeUnsavedEditsIntoPending,
    halftoneEnabled, clearResultDisplay,
  ])


  useEffect(() => () => {
    previewAbortRef.current?.abort()
    adoptObjectUrl(null, resultUrlRef)
    adoptObjectUrl(null, comparisonUrlRef)
    adoptObjectUrl(null, livePreviewUrlRef)
  }, [])

  // Two-phase UX: visible-layer placement keeps the clean frame until the user
  // clicks 生成预览. Clear stale rendered frames when preview is no longer needed.
  useEffect(() => {
    if (!file || !preview || resultImg || !needsLivePreview) {
      clearLivePreviewDisplay()
    }
  }, [file, preview, resultImg, needsLivePreview, clearLivePreviewDisplay])

  // Logo / 追踪巩固：无需框选时自动刷新可见层预览。位移整词等框选层仍等用户点「生成预览」。
  const logoAnchor = useMemo(
    () => resolveLogoAnchor(pendingVisibleEdits?.placements, logoOn),
    [pendingVisibleEdits, logoOn],
  )
  const editorStayInPlace = logoOn
    && !hasPendingBoxFlow
    && !(blurEnabled && blurRegionMode === 'brush')
  const showPlaceOnOriginal = hasPendingBoxFlow
    || (blurEnabled && blurRegionMode === 'brush')
  const autoFetchVisiblePreview = (hasTrackPreview || logoOn) && !hasPendingBoxFlow
  useEffect(() => {
    if (!file || !preview || resultImg || !autoFetchVisiblePreview) {
      if (!autoFetchVisiblePreview) setLivePreviewLoading(false)
      return
    }
    setLivePreviewLoading(true)
    setLivePreviewError('')
    const t = window.setTimeout(() => { void fetchLivePreview(null) }, 300)
    return () => window.clearTimeout(t)
  }, [
    autoFetchVisiblePreview, file, preview, resultImg, hasPendingBoxFlow, fetchLivePreview,
    trackEnabled, trackArtist, artist, dwtPayload, watermarkText, signatureText,
    halftoneEnabled, halftoneOn, halftoneStyle, halftoneText, halftoneSize, halftoneDensity,
    halftoneVisibility, halftoneSignature, halftoneSignatureSize, halftoneDotTexture,
    logoEnabled, logoFile, creditMark, logoPosition, logoSizePct,
    logoAnchor?.x, logoAnchor?.y,
  ])

  const downloadResult = useCallback(() => {
    if (!resultImg) return
    const baseName = file ? file.name.replace(/\.[^.]+$/, '') : 'protected'
    downloadProtectedImage(resultImg, baseName, outputFormat)
  }, [resultImg, file, outputFormat])

  const downloadHoloClip = useCallback(async () => {
    if (!resultImg || holoLoading) return
    setHoloLoading(true)
    setHoloError('')
    try {
      const upload = await resultImageToFile(resultImg)
      const fd = new FormData()
      fd.append('image', upload)
      const headers: HeadersInit = {}
      const token = getToken()
      if (token) headers.Authorization = `Bearer ${token}`
      const res = await fetch('/api/protect/holo-clip', { method: 'POST', body: fd, headers })
      const contentType = res.headers.get('content-type') || ''
      if (!res.ok) {
        if (contentType.includes('application/json')) {
          const data = await res.json() as { error_code?: string; error?: string }
          setHoloError(apiErr(data, t.errors.holoFailed) || t.errors.holoFailed)
        } else {
          setHoloError(t.errors.holoFailed)
        }
        return
      }
      const blob = await res.blob()
      const objectUrl = URL.createObjectURL(blob)
      const baseName = file ? file.name.replace(/\.[^.]+$/, '') : 'protected'
      downloadUrl(objectUrl, `${baseName}_holo.mp4`)
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1_000)
    } catch (e: unknown) {
      const isNetwork = e instanceof TypeError
        || (e instanceof Error && /failed to fetch|networkerror|load failed/i.test(e.message))
      setHoloError(isNetwork ? m.clientErrors.networkFailed : formatClientError(locale, e, t.errors.holoFailed))
    } finally {
      setHoloLoading(false)
    }
  }, [resultImg, holoLoading, file, apiErr, t.errors.holoFailed, m.clientErrors.networkFailed, locale])

  return (
    <div className="page-section">
      <div className="container">
        <div className="section-header" style={{ textAlign: 'center', marginBottom: 32 }}>
          <h1>{t.pageTitle}</h1>
          <p style={{ marginTop: 8 }}>{t.pageLead}</p>
        </div>

        <div className="jw-process-steps" aria-label={t.process.ariaLabel}>
          <div className="jw-process-step">
            <JingweiMiniIcon type="image" className="jw-process-icon" />
            <strong>{t.process.upload}</strong>
            <span>{t.process.uploadDesc}</span>
          </div>
          <div className="jw-process-step">
            <JingweiMiniIcon type="watermark" className="jw-process-icon" />
            <strong>{t.process.write}</strong>
            <span>{t.process.writeDesc}</span>
          </div>
          <div className="jw-process-step">
            <JingweiMiniIcon type="shield" className="jw-process-icon" />
            <strong>{t.process.download}</strong>
            <span>{t.process.downloadDesc}</span>
          </div>
        </div>

        <div className="two-col">
          {/* LEFT — Controls */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
            <div>
              <h3 style={{ marginBottom: 'var(--space-4)' }}>{t.sections.upload}</h3>
              <ImageUpload
                onFile={handleFile}
                preview={preview}
                onClear={clearFile}
                loading={processing}
              />
              <p className="form-hint" style={{ marginTop: 8 }}>
                {f.uploadLongEdgeHint}
              </p>
            </div>

            <div>
              <h3 style={{ marginBottom: 'var(--space-4)' }}>{t.sections.baseMode}</h3>
              <RadioPills options={modeOptions} value={mode} onChange={setMode} />
              <p className="form-hint" style={{ marginTop: 8 }}>
                {isCredit ? f.creditModeHint : f.stealthModeHint}
              </p>
            </div>

            {isCredit && (
              <div className="card" style={{ padding: 'var(--space-4)' }}>
                <div className="form-group">
                  <label className="form-label form-label-with-help">
                    {f.quickArtist}<span style={{ color: 'var(--color-danger)' }}>*</span>
                    <HelpTip text={f.artistNameHelp} />
                  </label>
                  <input
                    className={`form-input${isCredit && !artist.trim() ? ' input-error' : ''}`}
                    placeholder={f.artistPlaceholder}
                    value={artist}
                    onChange={e => setArtist(e.target.value)}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">{f.visibleMark}</label>
                  <RadioPills
                    options={creditMarkOptions}
                    value={creditMark}
                    onChange={v => setCreditMark(v as CreditVisibleMark)}
                  />
                  <span className="form-hint" style={{ display: 'block', marginTop: 6 }}>
                    {f.visibleMarkHint}
                  </span>
                </div>
                <div className="form-group">
                  <label className="form-label">{f.quickSignText}</label>
                  <input
                    className="form-input"
                    placeholder={f.dispTextPlaceholder}
                    value={dispText}
                    onChange={e => setDispText(e.target.value)}
                  />
                  <span className="form-hint" style={{ display: 'block', marginTop: 6 }}>
                    {creditUsesDisp ? f.creditDispLockedHint : f.quickSignPlaceHint}
                  </span>
                </div>
                {creditUsesAscii && (
                  <div className="form-group">
                    <label className="form-label">{f.logoPosition}</label>
                    <RadioPills
                      options={logoPositionOptions}
                      value={asciiPosition}
                      onChange={v => setAsciiPosition(v as LogoPosition)}
                    />
                    <span className="form-hint" style={{ display: 'block', marginTop: 6 }}>
                      {f.logoDragHint}
                    </span>
                  </div>
                )}
                <div className="form-group">
                  <label className="form-label">{f.quickLogo}</label>
                  <input
                    className="form-input"
                    type="file"
                    accept="image/png,image/jpeg,image/webp,.png,.jpg,.jpeg,.webp"
                    onChange={e => onLogoFileChange(e.target.files?.[0] ?? null)}
                  />
                  <span className="form-hint" style={{ display: 'block', marginTop: 6 }}>
                    {logoFile ? logoFile.name : f.quickLogoHint}
                  </span>
                </div>
                {logoFile && (
                  <>
                    <div className="form-group">
                      <label className="form-label">{f.logoPosition}</label>
                      <RadioPills options={logoPositionOptions} value={logoPosition} onChange={v => setLogoPosition(v as LogoPosition)} />
                      <span className="form-hint" style={{ display: 'block', marginTop: 6 }}>
                        {f.logoDragHint}
                      </span>
                    </div>
                    <Slider
                      label={f.logoSize}
                      min={6}
                      max={45}
                      step={1}
                      value={isCredit ? 8 : logoSizePct}
                      onChange={isCredit ? () => undefined : setLogoSizePct}
                      hint={f.logoSizeHint}
                    />
                    <span className="form-hint" style={{ display: 'block' }}>
                      {f.creditLogoFaintHint}
                    </span>
                  </>
                )}
              </div>
            )}

            {isCredit && creditUsesAscii && (
              <p className="form-hint" style={{ lineHeight: 1.6, color: 'var(--color-warning, #b26a00)' }}>
                {f.flatCreditHint}
              </p>
            )}

            {!isCredit && (
              <div>
                <h3 style={{ marginBottom: 'var(--space-4)' }}>{t.sections.visibleLayers}</h3>
              </div>
            )}

            <MaybeAccordion wrap={isCredit} title={t.accordions.moreOptions}>
            <Accordion title={t.accordions.displacement} defaultOpen={false}>
              <p className="form-hint" style={{ lineHeight: 1.6 }}>
                <strong>{f.dispPrincipleLead}</strong>{f.dispPrinciple}
              </p>
              <label className="form-checkbox">
                <input type="checkbox" checked={dispEnabled} onChange={e => setDispEnabled(e.target.checked)} />
                {f.enableDisp}
              </label>
              {dispEnabled && (
                <>
                  <label className="form-checkbox">
                    <input type="checkbox" checked={dispShadow} onChange={e => setDispShadow(e.target.checked)} />
                    {f.dispShadow}
                  </label>
                  {!isCredit && (
                  <div className="form-group">
                    <label className="form-label">
                      {f.dispText}<span style={{ color: 'var(--color-danger)' }}>*</span>
                    </label>
                    <input
                      className="form-input"
                      placeholder={f.dispTextPlaceholder}
                      value={dispText}
                      onChange={e => setDispText(e.target.value)}
                      required={dispEnabled}
                    />
                    {!dispText.trim() && (
                      <span className="form-hint" style={{ display: 'block', marginTop: 6, color: 'var(--color-danger)' }}>
                        {f.dispTextRequired}
                      </span>
                    )}
                  </div>
                  )}
                  <div className="form-group">
                    <label className="form-label">{f.dispMode}</label>
                    <RadioPills options={dispModeOptions} value={dispMode} onChange={setDispMode} />
                  </div>
                  <div
                    className="form-hint"
                    style={{
                      marginBottom: 12,
                      padding: '10px 12px',
                      lineHeight: 1.65,
                      borderRadius: 8,
                      borderLeft: '3px solid var(--color-accent, #3d6b9e)',
                      background: 'var(--color-surface-2, rgba(0,0,0,0.04)',
                    }}
                  >
                    <strong>{f.dispPlacementLead}</strong>{f.dispPlacementTip}
                    {dispMode === 'band' && f.dispBandExtra}
                  </div>
                  <Slider
                    label={f.dispFontSize}
                    min={0.07}
                    max={0.25}
                    step={0.01}
                    value={dispFontRatio}
                    onChange={setDispFontRatio}
                    hint={fmt(f.dispFontHint, { pct: (dispFontRatio * 100).toFixed(0) })}
                  />
                  <Slider label={f.dispShift} min={2} max={20} step={1} value={dispShift} onChange={setDispShift} unit="px"
                    hint={f.dispShiftHint} />
                  {dispMode !== 'band' ? (
                    <>
                      <div className="form-group">
                        <label className="form-label">{f.dispDensity}</label>
                        <RadioPills options={dispDensityOptions} value={dispDensity} onChange={setDispDensity} />
                      </div>
                      {file && Boolean(dispText.trim()) && (
                        <>
                          <button className="btn btn-secondary" onClick={bumpDispSeed} disabled={processing || livePreviewLoading}>
                            {t.actions.swapPattern}
                          </button>
                          <span className="form-hint" style={{ display: 'block', marginTop: 6, color: 'var(--color-text-tertiary)' }}>
                            {f.dispSwapHint}
                          </span>
                        </>
                      )}
                    </>
                  ) : (
                    <span className="form-hint" style={{ display: 'block', marginTop: 6 }}>
                      {f.dispBandModeHint}
                    </span>
                  )}
                </>
              )}
            </Accordion>

            {!isCredit && (
            <Accordion title={t.accordions.logoMark} defaultOpen={false}>
              <p className="form-hint" style={{ lineHeight: 1.6 }}>
                {f.logoHint}
              </p>
              <label className="form-checkbox">
                <input type="checkbox" checked={logoEnabled} onChange={e => setLogoEnabled(e.target.checked)} />
                {f.enableLogo}
              </label>
              {logoEnabled && (
                <>
                  <div className="form-group">
                    <label className="form-label">
                      {f.logoFile}<span style={{ color: 'var(--color-danger)' }}>*</span>
                    </label>
                    <input
                      className="form-input"
                      type="file"
                      accept="image/png,image/jpeg,image/webp,.png,.jpg,.jpeg,.webp"
                      onChange={e => onLogoFileChange(e.target.files?.[0] ?? null)}
                    />
                    <span className="form-hint" style={{ display: 'block', marginTop: 6 }}>
                      {logoFile ? logoFile.name : f.logoFileHint}
                    </span>
                  </div>
                  <div className="form-group">
                    <label className="form-label">{f.logoPosition}</label>
                    <RadioPills options={logoPositionOptions} value={logoPosition} onChange={v => setLogoPosition(v as LogoPosition)} />
                    <span className="form-hint" style={{ display: 'block', marginTop: 6 }}>
                      {f.logoDragHint}
                    </span>
                  </div>
                  <Slider
                    label={f.logoOpacity}
                    min={5}
                    max={90}
                    step={1}
                    value={logoOpacityPct}
                    onChange={setLogoOpacityPct}
                    hint={f.logoOpacityHint}
                  />
                  <Slider
                    label={f.logoSize}
                    min={6}
                    max={45}
                    step={1}
                    value={logoSizePct}
                    onChange={setLogoSizePct}
                    hint={f.logoSizeHint}
                  />
                </>
              )}
            </Accordion>
            )}

            <Accordion title={t.accordions.faceEmboss}>
              <label className="form-checkbox">
                <input type="checkbox" checked={feEnabled} onChange={e => setFeEnabled(e.target.checked)} />
                {f.enableFe}
              </label>
              {feEnabled && (
                <>
                  <div className="form-group">
                    <label className="form-label">{f.feText}</label>
                    <input className="form-input" placeholder={f.feTextPlaceholder}
                      value={feText} onChange={e => setFeText(e.target.value)} />
                  </div>
                  <Slider label={f.feCopies} min={1} max={10} step={1} value={feCopies} onChange={setFeCopies} />
                  <Slider label={f.feShift} min={5} max={40} step={1} value={feShift} onChange={setFeShift} unit="px" />
                  <Slider label={f.feOpacity} min={0.10} max={0.60} step={0.05} value={feOpacity} onChange={setFeOpacity} />
                  <Slider label={f.fePatchRatio} min={0.15} max={0.50} step={0.05} value={fePatchRatio} onChange={setFePatchRatio} />
                  <span className="form-hint" style={{ display: 'block', marginTop: 6 }}>
                    {f.fePlacementHint}
                  </span>
                </>
              )}
            </Accordion>

            <Accordion title={t.accordions.emboss}>
              <label className="form-checkbox">
                <input type="checkbox" checked={embossEnabled} onChange={e => setEmbossEnabled(e.target.checked)} />
                {f.enableEmboss}
              </label>
              {embossEnabled && (
                <>
                  <div className="form-group">
                    <label className="form-label">{f.embossPattern}</label>
                    <RadioPills options={embossPatternOptions} value={embossPattern} onChange={setEmbossPattern} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">{f.embossStrength}</label>
                    <RadioPills options={embossStrengthOptions} value={embossStrength} onChange={setEmbossStrength} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">{f.embossText}</label>
                    <input className="form-input" placeholder={f.embossTextPlaceholder}
                      value={embossText} onChange={e => setEmbossText(e.target.value)} />
                  </div>
                </>
              )}
            </Accordion>

            <Accordion title={t.accordions.blur}>
              <label className="form-checkbox">
                <input type="checkbox" checked={blurEnabled} onChange={e => setBlurEnabled(e.target.checked)} />
                {f.enableBlur}
              </label>
              {blurEnabled && (
                <>
                  <div className="form-group">
                    <label className="form-label">{f.blurRegion}</label>
                    <RadioPills
                      options={blurRegionOptions}
                      value={blurRegionMode}
                      onChange={v => setBlurRegionMode(v as 'bar' | 'brush')}
                    />
                  </div>
                  {blurRegionMode === 'bar' ? (
                    <>
                      <Slider label={f.blurCount} min={1} max={5} step={1} value={blurCount} onChange={setBlurCount} />
                      {selectedBlur ? (
                        <>
                          <Slider
                            label={f.blurSelectedW}
                            min={5} max={100} step={1}
                            value={Math.round(selectedBlur.w * 100)}
                            onChange={v => handleSelectedBlurResize(v / 100, selectedBlur.h)}
                            unit="%"
                          />
                          <Slider
                            label={f.blurSelectedH}
                            min={2} max={60} step={1}
                            value={Math.round(selectedBlur.h * 100)}
                            onChange={v => handleSelectedBlurResize(selectedBlur.w, v / 100)}
                            unit="%"
                          />
                          <span className="form-hint">{f.blurAdjusting}</span>
                        </>
                      ) : (
                        <span className="form-hint">
                          {f.blurBarHint}
                        </span>
                      )}
                    </>
                  ) : (
                    <span className="form-hint">{f.blurBrushHint}</span>
                  )}
                  <Slider label={f.blurSigma} min={3} max={40} step={1} value={blurSigma} onChange={setBlurSigma} unit=" sigma" />
                  <div className="form-group">
                    <label className="form-label">{f.blurText}</label>
                    <input className="form-input" placeholder={f.blurTextPlaceholder}
                      value={blurText} onChange={e => setBlurText(e.target.value)} />
                  </div>
                </>
              )}
            </Accordion>

            <Accordion title={t.accordions.asciiWatermark}>
              <label className="form-checkbox">
                <input type="checkbox" checked={halftoneEnabled} onChange={e => setHalftoneEnabled(e.target.checked)} />
                {f.enableHalftone}
              </label>
              {halftoneEnabled && (
                <>
                  <div className="form-group">
                    <label className="form-label">{f.halftoneStyle}</label>
                    <div className="halftone-style-grid" role="radiogroup" aria-label={f.halftoneStyle}>
                      {halftoneStyleOptions.map(opt => (
                        <button
                          key={opt.value}
                          type="button"
                          className={`halftone-style-card${halftoneStyle === opt.value ? ' is-selected' : ''}`}
                          onClick={() => setHalftoneStyle(opt.value)}
                          aria-pressed={halftoneStyle === opt.value}
                        >
                          <span className="halftone-style-card-title">{opt.title}</span>
                          <span className="halftone-style-card-desc">{opt.desc}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                  <div className="form-group">
                    <label className="form-label">
                      {f.halftoneText}<span style={{ color: 'var(--color-danger)' }}>*</span>
                    </label>
                    <input
                      className="form-input"
                      placeholder={f.halftoneTextPlaceholder}
                      value={halftoneText}
                      onChange={e => setHalftoneText(e.target.value)}
                      required={halftoneEnabled}
                    />
                    {!halftoneText.trim() && (
                      <span className="form-hint" style={{ display: 'block', marginTop: 6, color: 'var(--color-danger)' }}>
                        {f.halftoneTextRequired}
                      </span>
                    )}
                  </div>
                  {halftoneStyle === 'halftone_dots' && (
                    <Slider
                      label={f.halftoneDotTexture}
                      min={0}
                      max={100}
                      step={1}
                      value={halftoneDotTexture}
                      onChange={setHalftoneDotTexture}
                      hint={f.halftoneDotTextureHint}
                    />
                  )}
                  <Slider
                    label={halftoneSizeLabel}
                    min={0}
                    max={100}
                    step={1}
                    value={halftoneSize}
                    onChange={setHalftoneSize}
                    hint={halftoneSizeHint}
                  />
                  <Slider
                    label={halftoneDensityLabel}
                    min={0}
                    max={100}
                    step={1}
                    value={halftoneDensity}
                    onChange={setHalftoneDensity}
                    hint={halftoneDensityHint}
                  />
                  <Slider
                    label={f.halftoneVisibility}
                    min={0}
                    max={100}
                    step={1}
                    value={halftoneVisibility}
                    onChange={setHalftoneVisibility}
                    hint={f.halftoneVisibilityHint}
                  />
                  <Slider
                    label={f.halftoneSignatureSize}
                    min={0}
                    max={100}
                    step={1}
                    value={halftoneSignatureSize}
                    onChange={setHalftoneSignatureSize}
                    hint={f.halftoneSignatureSizeHint}
                  />
                  <Slider
                    label={f.halftoneSignatureVisibility}
                    min={0}
                    max={100}
                    step={1}
                    value={halftoneSignature}
                    onChange={setHalftoneSignature}
                    hint={halftoneSignatureHint}
                  />
                  {halftonePlacementEnabled && (
                    <span className="form-hint" style={{ display: 'block', marginTop: 6 }}>
                      {f.halftoneAnchorHint}
                    </span>
                  )}
                </>
              )}
            </Accordion>

            <div>
              {!isCredit && (
                <>
                  <h3 style={{ marginBottom: 'var(--space-4)' }}>{t.sections.track}</h3>
                  {trackArtist && !trackEnabled && (
                    <p style={{
                      marginBottom: 'var(--space-3)', lineHeight: 1.6,
                      color: 'var(--color-warning, #b26a00)',
                    }}>
                      {fmt(f.trackFilledNotEnabled, { value: trackArtist.value, source: trackArtist.source })}
                    </p>
                  )}
                </>
              )}
              {!jwEnabled && (
                <label className="form-checkbox" style={{ marginBottom: 'var(--space-4)' }}>
                  <input type="checkbox" checked={autoTimestamp} onChange={e => setAutoTimestamp(e.target.checked)} />
                  {f.autoTimestamp}
                </label>
              )}
              {jwEnabled && (
                <p className="form-hint" style={{ margin: 0, lineHeight: 1.6 }}>
                  {f.jwTimestampHint}
                </p>
              )}
            </div>

            <Accordion title={t.accordions.jwDeclaration} defaultOpen={!isCredit && jwEnabled}>
              <p className="form-hint" style={{ lineHeight: 1.6, marginBottom: 'var(--space-2)' }}>
                {JW_PROTECT_INTRO}
              </p>
              <div
                className="card"
                style={{
                  padding: 'var(--space-4)',
                  marginBottom: 'var(--space-4)',
                  background: 'var(--color-bg-secondary)',
                  border: '1px solid var(--color-border)',
                }}
              >
                <p className="text-sm" style={{ fontWeight: 600, marginBottom: 'var(--space-2)' }}>
                  {JW_PROTECT_PIXEL_REWARD.title}
                </p>
                <ul
                  className="text-sm text-secondary"
                  style={{ paddingLeft: 'var(--space-5)', lineHeight: 1.75, marginBottom: 'var(--space-2)' }}
                >
                  {JW_PROTECT_PIXEL_REWARD.bullets.map(line => (
                    <li key={line}>{line}</li>
                  ))}
                </ul>
                <p
                  className="text-xs text-secondary jw-quota-login-hint"
                  style={{ margin: 0, lineHeight: 1.6, opacity: 0.9 }}
                >
                  {JW_PROTECT_PIXEL_REWARD.loginHint}{' '}
                  <a href="https://jwprotect.com/community" className="jw-quota-login-link">
                    {t.links.goCommunity}
                  </a>
                </p>
              </div>
              {jwQuotaNotice && (
                <p className="text-sm" style={{ marginBottom: 'var(--space-3)', color: 'var(--color-accent)' }}>
                  {jwQuotaNotice}
                </p>
              )}
              <p style={{ marginBottom: 'var(--space-4)' }}>
                <Link to="/protocol" target="_blank" rel="noopener" className="text-sm" style={{ fontWeight: 500 }}>
                  {t.links.learnJw}
                </Link>
              </p>
              <label className="form-checkbox" style={{ marginBottom: 'var(--space-4)' }}>
                <input type="checkbox" checked={jwEnabled} onChange={e => setJwEnabled(e.target.checked)} />
                {f.enableJw}
              </label>
              {jwEnabled && (
                <>
                  <label className="form-checkbox" style={{ marginBottom: 'var(--space-2)' }}>
                    <input type="checkbox" checked={autoTimestamp} onChange={e => setAutoTimestamp(e.target.checked)} />
                    {f.attachTimestamp}
                  </label>
                  <p className="form-hint" style={{ marginTop: 0, marginBottom: 'var(--space-4)', lineHeight: 1.6 }}>
                    {f.timestampHint}
                  </p>
                </>
              )}
              {!jwEnabled && (
                <p className="form-hint" style={{ marginTop: -8, marginBottom: 'var(--space-4)' }}>
                  {f.metadataWithoutJw}
                </p>
              )}
              {jwEnabled && (
                <>
                  {outputFormat === 'jpg' && (
                    <div className="card notice-warning">
                      <p className="text-sm" style={{ margin: 0 }}><strong>{f.notice}</strong>{JW_PNG_HINT}</p>
                    </div>
                  )}
                  {!isCredit && (
                  <div className="form-group">
                    <label className="form-label form-label-with-help">
                      {f.artistNameRequired}<span style={{ color: 'var(--color-danger)' }}>*</span>
                      <HelpTip text={f.artistNameHelp} />
                    </label>
                    <input className={`form-input${jwEnabled && !artist.trim() ? ' input-error' : ''}`}
                      placeholder={f.artistPlaceholder}
                      value={artist} onChange={e => setArtist(e.target.value)} />
                    {jwEnabled && !artist.trim() && (
                      <span className="form-hint" style={{ color: 'var(--color-danger)' }}>
                        {f.artistRequiredHint}
                      </span>
                    )}
                    <span className="form-hint">
                      {f.artistMetaHint}
                    </span>
                  </div>
                  )}
                  <div className="form-group">
                    <label className="form-label">{f.creationType}</label>
                    <div className="jw-option-list">
                      {JW_CREATION_OPTIONS.map(opt => (
                        <label key={opt.id} className="form-checkbox jw-option-row jw-option-row--radio">
                          <input type="radio" name="jw_creation" value={opt.id}
                            checked={jwCreation === opt.id}
                            onChange={() => setJwCreation(opt.id)} />
                          <span className="jw-option-icon" aria-hidden="true">
                            <JwIcon type={opt.id as 'OC' | 'AI'} size={40} />
                          </span>
                          <span className="jw-option-body">
                            <strong>{opt.id}</strong> {localeUsesLatinJwFields(locale) ? opt.label : opt.labelZh}
                            <span className="text-sm text-secondary" style={{ display: 'block', marginTop: 2 }}>{localeUsesLatinJwFields(locale) ? opt.desc : opt.descZh}</span>
                          </span>
                        </label>
                      ))}
                    </div>
                  </div>
                  <div className="form-group">
                    <label className="form-label">{f.restrictions}</label>
                    <div className="jw-option-list">
                      {JW_RESTRICTION_FLAGS.map(flag => (
                        <label key={flag.id} className="form-checkbox jw-option-row">
                          <input type="checkbox"
                            checked={jwRestrictions.includes(flag.id)}
                            onChange={() => toggleJwRestriction(flag.id)} />
                          <span className="jw-option-icon" aria-hidden="true">
                            <JwIcon type={flag.id as 'NO-TR' | 'NO-ED'} size={40} />
                          </span>
                          <span className="jw-option-body">
                            <strong>{flag.abbrev}</strong> {localeUsesLatinJwFields(locale) ? flag.label : flag.labelZh}
                            <span className="text-sm text-secondary" style={{ display: 'block', marginTop: 2 }}>{localeUsesLatinJwFields(locale) ? flag.desc : flag.descZh}</span>
                          </span>
                        </label>
                      ))}
                    </div>
                  </div>
                  <div className="form-group">
                    <p className="form-hint" style={{ marginBottom: 'var(--space-3)', lineHeight: 1.65 }}>
                      {JW_INVISIBLE_INTRO}
                    </p>
                    {jwWriteHint && (
                      <div
                        className="card"
                        style={{
                          padding: 'var(--space-3) var(--space-4)',
                          marginBottom: 'var(--space-3)',
                          background: jwWriteHint.kind === 'flat'
                            ? 'var(--color-warning-bg, #fff8e6)'
                            : 'var(--color-bg-secondary)',
                          lineHeight: 1.65,
                        }}
                      >
                        <p className="text-sm" style={{ margin: 0 }}>{jwWriteHint.summary}</p>
                        <p className="text-sm text-secondary" style={{ margin: '6px 0 0' }}>{jwWriteHint.suggest}</p>
                      </div>
                    )}
                  </div>
                  <p className="form-hint" style={{ marginBottom: 'var(--space-4)', lineHeight: 1.6 }}>
                    {JW_DWT_RELATION.protectHint}
                  </p>
                  <div className="form-group">
                    <label className="form-label">{f.visibleMode}</label>
                    <div className="jw-visible-mode-options">
                      <label className="form-checkbox">
                        <input type="radio" name="jw_visible_mode" value="none"
                          checked={jwVisibleMode === 'none'}
                          onChange={() => setJwVisibleMode('none')} />
                        {f.visibleNone}
                      </label>
                      <label className="form-checkbox">
                        <input type="radio" name="jw_visible_mode" value="badge"
                          checked={jwVisibleMode === 'badge'}
                          onChange={() => setJwVisibleMode('badge')} />
                        {f.visibleBadge}
                      </label>
                      <label className="form-checkbox">
                        <input type="radio" name="jw_visible_mode" value="footer"
                          checked={jwVisibleMode === 'footer'}
                          onChange={() => setJwVisibleMode('footer')} />
                        {f.visibleFooter}
                      </label>
                    </div>
                  </div>
                  {jwVisibleMode === 'badge' && (
                    <div className="jw-badge-inline-preview" style={{ display: 'flex', flexDirection: 'column', gap: 8, alignItems: 'flex-start' }}>
                      <span className="text-sm text-secondary">{f.badgePreview}</span>
                      <div style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '6px 10px', background: '#fff', border: '1px solid var(--color-border-soft)', borderRadius: 8 }}>
                        <span className="jw-icon-row">
                          <JwIcon type="JW" size={28} />
                          <JwIcon type={jwCreation as 'OC' | 'AI'} size={28} />
                          {jwRestrictions.map(r => (
                            <JwIcon key={r} type={r as 'NO-TR' | 'NO-ED'} size={28} />
                          ))}
                        </span>
                      </div>
                      <code className="text-xs text-secondary">{formatBadgePreview(jwCreation, jwRestrictions)}</code>
                    </div>
                  )}
                  {jwVisibleMode === 'footer' && (
                    <div className="jw-badge-inline-preview" style={{ display: 'flex', flexDirection: 'column', gap: 8, alignItems: 'flex-start' }}>
                      <span className="text-sm text-secondary">{f.footerPreview}</span>
                      <div style={{
                        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                        width: '100%', padding: '8px 14px',
                        background: '#fff', border: '1px solid var(--color-border-soft)', borderRadius: 8,
                      }}>
                        <span className="jw-footer-brand">
                          <img src={jingweiBird} alt="" className="jw-bird-logo" style={{ height: 28 }} />
                          <span className="jw-footer-brand-text">
                            <strong>{f.footerBrand}</strong>
                            <span>Jingwei</span>
                          </span>
                        </span>
                        <span className="jw-icon-row">
                          <JwIcon type="JW" size={24} />
                          <JwIcon type={jwCreation as 'OC' | 'AI'} size={24} />
                          {jwRestrictions.map(r => (
                            <JwIcon key={r} type={r as 'NO-TR' | 'NO-ED'} size={24} />
                          ))}
                        </span>
                      </div>
                    </div>
                  )}
                </>
              )}
            </Accordion>

            {!jwEnabled && (
            <Accordion title={t.accordions.dwt}>
              <div className="form-group">
                <label className="form-label">{f.dwtLabel}</label>
                <input className="form-input" placeholder={f.dwtPlaceholder}
                  maxLength={24} value={dwtPayload} onChange={e => setDwtPayload(e.target.value)} />
                <span className="form-hint">
                  {`${JW_DWT_RELATION.verifyStandaloneDwtHint} ${f.dwtHintSuffix}`}
                </span>
              </div>
            </Accordion>
            )}

            <Accordion title={t.accordions.lsb}>
              <div className="form-group">
                <label className="form-label">{f.lsbLabel}</label>
                <input className="form-input" placeholder={f.lsbPlaceholder}
                  value={watermarkText} onChange={e => setWatermarkText(e.target.value)} />
                <span className="form-hint">{f.lsbHint}</span>
              </div>
              <div className="form-group">
                <label className="form-label">{f.signatureLabel}</label>
                <input className="form-input" placeholder={f.signaturePlaceholder}
                  value={signatureText} onChange={e => setSignatureText(e.target.value)} />
                <span className="form-hint">{f.signatureHint}</span>
              </div>
              <div className="form-group">
                <label className="form-label">{f.signaturePos}</label>
                <RadioPills options={sigPosOptions} value={signaturePos} onChange={setSignaturePos} />
              </div>
            </Accordion>

            <Accordion title={t.accordions.metadata}>
              <div className="form-group">
                <label className="form-label">{f.metadataArtist}</label>
                <input className="form-input" placeholder={f.artistPlaceholderOptional}
                  value={artist} onChange={e => setArtist(e.target.value)} />
                <span className="form-hint">
                  {f.metadataExifHint}
                  {jwEnabled ? f.metadataHintJw : f.metadataHintNoJw}
                </span>
              </div>
              <label className="form-checkbox">
                <input type="checkbox" checked={embedMeta} onChange={e => setEmbedMeta(e.target.checked)} />
                {f.embedMeta}
              </label>
            </Accordion>

            <Accordion title={t.accordions.track} defaultOpen={trackEnabled}>
              <p style={{ lineHeight: 1.6, color: 'var(--color-text)' }}>
                {f.trackIntro}
              </p>
              <label className="form-checkbox">
                <input type="checkbox" checked={trackEnabled} onChange={e => setTrackEnabled(e.target.checked)} />
                {f.enableTrack}
              </label>
              {trackEnabled && !trackArtist && (
                <p style={{ color: 'var(--color-danger)', lineHeight: 1.6 }}>
                  {f.trackNoArtist}
                </p>
              )}
              {trackEnabled && trackArtist && (
                <div style={{
                  border: '1px solid var(--color-warning, #b26a00)', borderRadius: 8,
                  padding: 'var(--space-3)', color: 'var(--color-warning, #b26a00)', lineHeight: 1.6,
                }}>
                  <strong>{f.trackRememberPrefix}{trackArtist.value}{f.trackRememberSuffix}{trackArtist.source}{f.trackRememberEnd}</strong>
                </div>
              )}
              {trackEnabled && uploadTooSmallForAnchor && uploadDims && (
                <p style={{
                  lineHeight: 1.6, color: 'var(--color-danger, #c0392b)',
                  padding: 'var(--space-3)', borderRadius: 8,
                  background: 'var(--color-danger-bg, #fdecea)',
                }}>
                  {fmt(f.trackTooSmall, {
                    w: uploadDims.w,
                    h: uploadDims.h,
                    shortEdge: Math.min(uploadDims.w, uploadDims.h),
                    minEdge: anchorMinEdge,
                  })}
                </p>
              )}
              {trackEnabled && (
                <p style={{ lineHeight: 1.6, color: 'var(--color-text)' }}>
                  {f.trackConfirm}
                </p>
              )}
            </Accordion>
            </MaybeAccordion>

            <button
              className="btn btn-primary btn-lg"
              style={{ width: '100%', marginTop: 'var(--space-4)' }}
              onClick={() => handleStartProtectClick()}
              disabled={!file || processing || !accepted || (jwEnabled && !artist.trim()) || (dispEnabled && !(isCredit ? creditStampText : dispText.trim())) || (halftoneEnabled && !(isCredit ? creditStampText : halftoneText.trim())) || (logoEnabled && !logoFile)}
            >
              {processing
                ? <><span className="spinner" /> {t.actions.processing}</>
                : !accepted
                  ? t.actions.agreeTerms
                  : (dispEnabled && !(isCredit ? creditStampText : dispText.trim()))
                    ? t.actions.fillDispText
                    : (halftoneEnabled && !halftoneText.trim())
                      ? t.actions.fillHalftoneText
                    : (logoEnabled && !logoFile)
                      ? t.actions.fillLogoFile
                    : (jwEnabled && !artist.trim())
                      ? t.actions.fillArtist
                      : t.actions.startProtect}
            </button>
          </div>

          {/* RIGHT — Preview / Results (sticky while scrolling left controls) */}
          <div className="protect-results-sticky">
            <div>
              <h3 style={{ marginBottom: 'var(--space-4)' }}>
                {resultImg ? t.sections.result : needsLivePreview && file ? t.sections.preview : t.sections.result}
              </h3>
              {resultImg ? (
                <div className="card visible-layer-editor-card">
                  <VisibleLayerEditor
                    key={visibleEditorKey}
                    ref={visibleEditorRef}
                    imageSrc={resultImg}
                    originalSrc={preview ?? undefined}
                    processing={processing}
                    availableLayers={visibleLayers}
                    allowBlurBrush={blurEnabled && blurRegionMode === 'brush'}
                    onApply={handleVisibleEditApply}
                    onClear={handleVisibleEditClear}
                    onPlacementsChange={handlePlacementsChange}
                    onBackToPlace={requestBackToPlace}
                    onSelectedChange={setSelectedBlur}
                    seed={{ key: placementSeedKey, placements: pendingVisibleEdits?.placements ?? [] }}
                    applyLabel={t.actions.saveEdits}
                    hideTitle
                    hasPreview
                    displacementText={dispText}
                    displacementFontRatio={dispFontRatio}
                    halftoneText={halftoneText}
                    halftoneSignatureSize={halftoneSignatureSize}
                    logoScale={creditLogoScale}
                  />
                </div>
              ) : file && preview && (hasVisibleLayers || logoOn) ? (
                <div className="card visible-layer-editor-card">
                  <div className="protect-preview-panel-header" style={{ marginBottom: 8 }}>
                    <span className="text-sm" style={{ color: 'var(--color-text)' }}>
                      {hasTrackPreview
                        ? t.preview.visibleAndTrack
                        : t.preview.visibleOnly}
                    </span>
                  </div>
                  {livePreviewError && (
                    <p className="form-hint" style={{ color: 'var(--color-danger, #c0392b)' }}>
                      {livePreviewError}
                    </p>
                  )}
                  <div style={{ position: 'relative' }}>
                    <VisibleLayerEditor
                      key={`preview-${visibleEditorKey}`}
                      ref={visibleEditorRef}
                      imageSrc={livePreviewImg || preview}
                      originalSrc={preview ?? undefined}
                      processing={processing || livePreviewLoading}
                      availableLayers={visibleLayers}
                      allowBlurBrush={blurEnabled && blurRegionMode === 'brush'}
                      onApply={handleVisibleEditApply}
                      onClear={handleVisibleEditClear}
                      onPlacementsChange={handlePlacementsChange}
                      onBackToPlace={requestBackToPlace}
                      onSelectedChange={setSelectedBlur}
                      seed={{ key: placementSeedKey, placements: pendingVisibleEdits?.placements ?? [] }}
                      applyLabel={t.actions.saveEdits}
                      updatePreviewLabel={t.actions.updatePreview}
                      onUpdatePreview={handleVisibleEditUpdatePreview}
                      previewMode
                      hasPreview={Boolean(livePreviewImg) && !editorStayInPlace}
                      hideTitle
                      displacementText={dispText}
                      displacementFontRatio={dispFontRatio}
                      halftoneText={halftoneText}
                      halftoneSignatureSize={halftoneSignatureSize}
                      logoScale={creditLogoScale}
                    />
                    {livePreviewLoading && (
                      <p className="form-hint" style={{ marginTop: 8 }}>
                        {t.preview.generating}
                      </p>
                    )}
                    {!livePreviewImg && !livePreviewLoading && showPlaceOnOriginal && (
                      <p style={{ marginTop: 8, color: 'var(--color-text)' }}>
                        {t.preview.placeOnOriginal}
                      </p>
                    )}
                    {logoOn && livePreviewImg && !livePreviewLoading && (
                      <p style={{ marginTop: 8, color: 'var(--color-success, #1f7a4d)' }}>
                        {t.preview.logoDone}
                      </p>
                    )}
                    {hasTrackPreview && livePreviewImg && !livePreviewLoading && (
                      <p style={{ marginTop: 8, lineHeight: 1.6, color: 'var(--color-text)' }}>
                        {t.preview.trackConfirm}
                      </p>
                    )}
                  </div>
                </div>
              ) : file && preview && hasTrackPreview ? (
                <div className="image-preview protect-result-preview">
                  {livePreviewError && (
                    <p style={{ color: 'var(--color-danger, #c0392b)', marginBottom: 8 }}>
                      {livePreviewError}
                    </p>
                  )}
                  <img
                    src={livePreviewImg || preview}
                    alt={hasTrackPreview ? t.preview.trackAlt : t.preview.logoAlt}
                    className="protect-preview-img"
                  />
                  {livePreviewLoading && (
                    <p style={{ marginTop: 8, color: 'var(--color-text)' }}>
                      {hasTrackPreview ? t.preview.trackGenerating : t.preview.logoGenerating}
                    </p>
                  )}
                  {!livePreviewLoading && livePreviewImg && (
                    <>
                      <p style={{ marginTop: 8, color: 'var(--color-success, #1f7a4d)' }}>
                        {hasTrackPreview ? t.preview.trackDone : t.preview.logoDone}
                      </p>
                      {hasTrackPreview && (
                        <p style={{ marginTop: 4, lineHeight: 1.6, color: 'var(--color-text)' }}>
                          {t.preview.trackConfirm}
                        </p>
                      )}
                    </>
                  )}
                  {!livePreviewLoading && !livePreviewImg && (
                    <p style={{ marginTop: 8, color: 'var(--color-text)' }}>
                      {t.preview.trackFailed}
                    </p>
                  )}
                </div>
              ) : file && preview ? (
                <div className="image-preview protect-result-preview">
                  <img src={preview} alt={t.preview.uploadAlt} className="protect-preview-img" />
                  {!isCredit && trackArtist && !trackEnabled ? (
                    <p style={{ marginTop: 8, lineHeight: 1.6, color: 'var(--color-warning, #b26a00)' }}>
                      {fmt(f.trackFilledEnable, { value: trackArtist.value })}
                    </p>
                  ) : !isCredit ? (
                    <p style={{ marginTop: 8, color: 'var(--color-text)' }}>
                      {t.preview.enableHint}
                    </p>
                  ) : null}
                </div>
              ) : (
                <div className="image-preview preview-with-overlay protect-result-preview">
                  <div className="result-placeholder">
                    {t.preview.placeholder}
                  </div>
                  {processing && (
                    <div className="preview-loading-overlay">
                      <span className="spinner" />
                      <span>{t.actions.processing}</span>
                    </div>
                  )}
                </div>
              )}
              {resultImg && (
                <div style={{ marginTop: 8, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => openLightbox(resultImg, t.preview.protectedAlt)}
                  >
                    {t.actions.zoomPreview}
                  </button>
                </div>
              )}
              {resultImg && (
                <div className="protect-holo-block">
                  <h3 style={{ marginBottom: 8 }}>{t.sections.holoPreview}</h3>
                  <p className="form-hint" style={{ lineHeight: 1.6 }}>{t.preview.holoHint}</p>
                  <div className="protect-holo-stage">
                    <HoloCard className="holo-card-hero protect-holo-card">
                      <img src={resultImg} alt={t.preview.holoAlt} loading="lazy" decoding="async" />
                    </HoloCard>
                  </div>
                </div>
              )}
              {resultImg && processing && (
                <p className="form-hint" style={{ marginTop: 8 }}>{t.preview.applyingEdits}</p>
              )}
            </div>

            {resultImg && (
              <div style={{ marginBottom: 'var(--space-4)' }}>
                <h3 style={{ marginBottom: 'var(--space-4)' }}>{t.sections.output}</h3>
                <div className="form-group" style={{ marginBottom: 'var(--space-4)' }}>
                  <label className="form-label">{t.labels.outputFormat}</label>
                  <RadioPills options={formatOptions} value={outputFormat} onChange={setOutputFormat} />
                  {hasAlpha && outputFormat !== 'png' && (
                    <p className="text-sm notice-warning" style={{ marginTop: 'var(--space-2)', padding: '6px 10px', borderRadius: 6 }}>
                      {t.result.alphaWarning}
                    </p>
                  )}
                </div>
                <button className="btn btn-primary btn-lg" style={{ width: '100%' }} onClick={downloadResult}>
                  {t.labels.downloadProtected}
                </button>
                <button
                  className="btn btn-secondary btn-lg"
                  style={{ width: '100%', marginTop: 10 }}
                  onClick={() => { void downloadHoloClip() }}
                  disabled={holoLoading}
                >
                  {holoLoading ? t.preview.holoRecording : t.labels.downloadHolo}
                </button>
                {holoError && (
                  <p className="form-hint" style={{ color: 'var(--color-danger, #c0392b)', marginTop: 8 }}>
                    {holoError}
                  </p>
                )}
              </div>
            )}

            {comparison && (
              <div>
                <h3 style={{ marginBottom: 'var(--space-3)' }}>{t.preview.comparisonTitle}</h3>
                <p className="text-xs text-secondary" style={{ marginBottom: 'var(--space-3)' }}>
                  {t.preview.comparisonCaption}
                </p>
                <div className="zoomable-wrap">
                  <img
                    src={comparison}
                    alt="comparison"
                    className="zoomable-image protect-comparison-img"
                    onClick={() => openLightbox(comparison, t.preview.comparisonAlt)}
                  />
                  <span className="zoom-hint">{t.labels.clickToZoom}</span>
                </div>
              </div>
            )}

            {metrics && (
              <div className="card fade-in">
                <div className="metrics-row">
                  <div className="metric-item">
                    <span className="label">{t.labels.quality}</span>
                    <span className={`badge badge-${qualityLabel === 'success' ? 'success' : qualityLabel === 'warning' ? 'warning' : 'danger'}`}>
                      {qualityText}
                    </span>
                  </div>
                  <div className="metric-item">
                    <span className="label">PSNR</span>
                    <span className="value">{metrics.psnr == null || metrics.psnr === Infinity ? '∞' : metrics.psnr.toFixed(2)} dB</span>
                  </div>
                  <div className="metric-item">
                    <span className="label">SSIM</span>
                    <span className="value">{metrics.ssim.toFixed(4)}</span>
                  </div>
                  <div className="metric-item">
                    <span className="label">Max Diff</span>
                    <span className="value">{metrics.max_diff}</span>
                  </div>
                </div>
                <p className="text-xs text-secondary" style={{ marginTop: 'var(--space-3)', lineHeight: 1.6 }}>
                  {t.metrics.qualityHint}
                </p>
              </div>
            )}

            {error && (
              <div className="card fade-in" style={{ borderColor: 'var(--color-danger)', background: 'var(--color-danger-bg)' }}>
                <strong>{t.result.failed}</strong>
                <p>{error}</p>
              </div>
            )}

            {resizeNotice && (
              <div className="card fade-in" style={{ background: 'var(--color-bg-secondary)' }}>
                <p className="text-sm">{resizeNotice}</p>
              </div>
            )}

            {layersApplied && resultImg && (
              <div className="card fade-in" style={{ background: 'var(--color-bg-secondary)', marginBottom: 'var(--space-4)' }}>
                <strong style={{ display: 'block', marginBottom: 8 }}>{t.result.layersTitle}</strong>
                <ul className="text-sm" style={{ margin: 0, paddingLeft: 'var(--space-5)', lineHeight: 1.75 }}>
                  <li>
                    {t.result.layerJw}{layersApplied.jw
                      ? (() => {
                          const method = layersApplied.jwEmbedMethod
                            ? JW_EMBED_METHOD_LABEL[layersApplied.jwEmbedMethod] ?? layersApplied.jwEmbedMethod
                            : t.result.jwInvisible
                          const tier = layersApplied.jwEmbedTier && layersApplied.jwEmbedTier !== 'lsb'
                            ? ` · ${layersApplied.jwEmbedTier}`
                            : ''
                          return fmt(t.result.jwWritten, { method, tier })
                        })()
                      : (jwEnabled
                        ? t.result.jwEnabledFailed
                        : t.result.jwNotEnabled)}
                  </li>
                  {!jwEnabled && (
                    <li>
                      {t.result.layerDwt}{layersApplied.dwt
                        ? t.result.dwtWritten
                        : (dwtPayload.trim() ? t.result.dwtFailed : t.result.dwtEmpty)}
                    </li>
                  )}
                  <li>
                    {t.result.layerLsb}{layersApplied.lsb ? t.result.lsbWritten : (watermarkText.trim() ? t.result.lsbFailed : t.result.lsbEmpty)}
                  </li>
                  <li>
                    {t.result.layerTrack}{layersApplied.track
                      ? t.result.trackWritten
                      : (trackEnabled
                        ? t.result.trackFailed
                        : t.result.trackNotEnabled)}
                  </li>
                </ul>
                <p className="form-hint" style={{ marginTop: 8, marginBottom: 0 }}>
                  {t.result.verifyHint}
                </p>
              </div>
            )}

            {status && (
              <div className="card fade-in" style={{ background: 'var(--color-success-bg)' }}>
                <strong>{t.result.done}</strong>
                <p className="text-sm">{status}</p>
              </div>
            )}


          </div>
        </div>

        {/* 保护限度说明 — 诚实告知能做什么、不能做什么 */}
        <section className="jw-limits-card" style={{ marginTop: 'var(--space-12)', marginBottom: 'var(--space-8)' }}>
          <h3>{JW_PROTECT_LIMITS.title}</h3>
          {JW_PROTECT_LIMITS.paragraphs.map((p, i) => (
            <p key={i}>{p}</p>
          ))}
          <ul>
            {JW_PROTECT_LIMITS.bullets.map((b, i) => (
              <li key={i}>
                <strong>{b.strong}</strong>
                {b.body}
              </li>
            ))}
          </ul>
          <p className="text-sm text-secondary" style={{ marginTop: 'var(--space-4)', marginBottom: 0 }}>
            {t.links.faqMore} <Link to="/faq">{t.links.faq}</Link>
          </p>
        </section>

        {/* 核心信念 — 为什么仍然值得做这件事 */}
        <section className="card jw-belief-card" style={{ padding: 'var(--space-8)', marginTop: 'var(--space-12)' }}>
          <h2 style={{ marginBottom: 'var(--space-4)' }}>{JW_CORE_BELIEF_SUMMARY.title}</h2>
          {JW_CORE_BELIEF_SUMMARY.paragraphs.map((para, i) => (
            <p key={i} className="text-secondary" style={{ marginTop: i === 0 ? 0 : 'var(--space-3)', lineHeight: 1.8 }}>
              {para}
            </p>
          ))}
          <p style={{ marginTop: 'var(--space-5)', textAlign: 'center' }}>
            <Link to={JW_CORE_BELIEF_SUMMARY.linkTo} className="btn btn-secondary btn-sm">
              {JW_CORE_BELIEF_SUMMARY.linkLabel}
            </Link>
          </p>
        </section>
        <FeedbackHelpLink from="protect" />
      </div>
      <ProtectMaskRetainDialog
        open={maskRetainDialogOpen}
        reason={maskRetainReason}
        onKeep={() => { void handleMaskRetainKeep() }}
        onDiscard={() => { void handleMaskRetainDiscard() }}
        onCancel={maskRetainReason === 'backToPlace' ? closeMaskRetainDialog : undefined}
        busy={processing}
      />
      <ProtectUnsavedDialog
        open={unsavedProtectDialogOpen}
        onSaveAndProtect={() => { void handleUnsavedSaveAndProtect() }}
        onDiscardAndProtect={handleUnsavedDiscardAndProtect}
        onCancel={handleUnsavedProtectCancel}
        busy={processing}
      />
      <ImageLightbox src={lightboxSrc} alt={lightboxAlt} onClose={() => setLightboxSrc(null)} />
    </div>
  )
}
