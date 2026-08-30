import { useCallback, useRef } from 'react'
import { useLocale } from '../i18n/LocaleContext'
import RegionPainter, { type RegionPaintMode } from './RegionPainter'

interface Props {
  /** Upload preview (fallback while loading). */
  uploadPreview: string
  /** Server-rendered visible-layer preview. */
  previewImg: string | null
  loading: boolean
  error?: string
  /** Displacement anchor (normalized 0–1). */
  dispEnabled: boolean
  dispText: string
  dispMode: string
  dispAnchor: { x: number; y: number } | null
  onDispAnchor: (p: { x: number; y: number }) => void
  /** Blur region painting. */
  blurEnabled: boolean
  blurRegionMode: 'bar' | 'brush' | 'rect'
  blurRegionExportRef: React.MutableRefObject<(() => Promise<Blob | null>) | null>
  onBlurRegionChange?: (hasStroke: boolean) => void
  blurRegionHasPaint: boolean
  onRefresh?: () => void
}

export default function ProtectPreviewPanel({
  uploadPreview,
  previewImg,
  loading,
  error,
  dispEnabled,
  dispText,
  dispMode,
  dispAnchor,
  onDispAnchor,
  blurEnabled,
  blurRegionMode,
  blurRegionExportRef,
  onBlurRegionChange,
  blurRegionHasPaint,
  onRefresh,
}: Props) {
  const { messages: m } = useLocale()
  const p = m.components.protectPreviewPanel
  const stageRef = useRef<HTMLDivElement>(null)

  const canPickAnchor = dispEnabled && Boolean(dispText.trim()) && dispMode === 'band'
  const showBlurPaint = blurEnabled && blurRegionMode !== 'bar'
  const displaySrc = previewImg || uploadPreview

  const onStageClick = useCallback(
    (e: React.MouseEvent) => {
      if (!canPickAnchor || loading) return
      const el = stageRef.current
      if (!el) return
      const rect = el.getBoundingClientRect()
      const x = (e.clientX - rect.left) / rect.width
      const y = (e.clientY - rect.top) / rect.height
      if (x >= 0 && x <= 1 && y >= 0 && y <= 1) {
        onDispAnchor({ x, y })
      }
    },
    [canPickAnchor, loading, onDispAnchor],
  )

  return (
    <div className="protect-preview-panel">
      <div className="protect-preview-panel-header">
        <span className="text-sm text-secondary">{p.title}</span>
        {onRefresh && (
          <button type="button" className="btn btn-secondary btn-sm" onClick={onRefresh} disabled={loading}>
            {loading ? p.updating : p.refresh}
          </button>
        )}
      </div>

      {showBlurPaint ? (
        <RegionPainter
          imageSrc={uploadPreview}
          mode={blurRegionMode as RegionPaintMode}
          exportRef={blurRegionExportRef}
          onMaskChange={onBlurRegionChange}
        />
      ) : (
        <div
          ref={stageRef}
          className={`protect-preview-stage${canPickAnchor ? ' is-pick-anchor' : ''}`}
          onClick={onStageClick}
        >
          <img src={displaySrc} alt={p.alt} className="protect-preview-img" draggable={false} />
          {dispAnchor && (
            <span
              className="visible-layer-editor-marker visible-layer-editor-marker--displacement"
              style={{ left: `${dispAnchor.x * 100}%`, top: `${dispAnchor.y * 100}%` }}
            />
          )}
          {loading && (
            <div className="preview-loading-overlay">
              <span className="spinner" />
              <span>{p.generating}</span>
            </div>
          )}
        </div>
      )}

      {error && <p className="form-hint" style={{ color: 'var(--color-danger, #c0392b)' }}>{error}</p>}

      <p className="form-hint" style={{ marginTop: 8 }}>
        {showBlurPaint && (
          blurRegionMode === 'brush' ? p.blurBrushHint : p.blurRectHint
        )}
        {!showBlurPaint && canPickAnchor && p.anchorHint}
        {!showBlurPaint && dispEnabled && dispMode !== 'band' && p.seedHint}
        {blurEnabled && blurRegionMode === 'bar' && p.barHint}
        {!blurRegionHasPaint && blurEnabled && blurRegionMode !== 'bar' && p.paintRequired}
      </p>
      {showBlurPaint && previewImg && (
        <div className="protect-preview-thumb-wrap">
          <p className="form-label" style={{ marginBottom: 6 }}>{p.effectPreview}</p>
          <img src={previewImg} alt="" className="protect-preview-thumb" draggable={false} />
        </div>
      )}
    </div>
  )
}
