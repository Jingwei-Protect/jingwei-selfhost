import { useCallback, useRef, useState, type KeyboardEvent, type PointerEvent } from 'react'

export interface ImageCompareSliderProps {
  beforeSrc: string
  afterSrc: string
  beforeAlt: string
  afterAlt: string
  beforeLabel: string
  afterLabel: string
  hint?: string
}

/**
 * 竖线分割对比：左为加水印后，右为 AI 试图还原后。
 * 滑竿从左向右拖，右侧露出越多 AI 修复图。
 */
export default function ImageCompareSlider({
  beforeSrc,
  afterSrc,
  beforeAlt,
  afterAlt,
  beforeLabel,
  afterLabel,
  hint,
}: ImageCompareSliderProps) {
  const [split, setSplit] = useState(50)
  const boxRef = useRef<HTMLDivElement>(null)
  const dragging = useRef(false)

  const updateSplit = useCallback((clientX: number) => {
    const box = boxRef.current
    if (!box) return
    const rect = box.getBoundingClientRect()
    const pct = ((clientX - rect.left) / rect.width) * 100
    setSplit(Math.max(0, Math.min(100, pct)))
  }, [])

  const onPointerDown = (e: PointerEvent<HTMLDivElement>) => {
    dragging.current = true
    e.currentTarget.setPointerCapture(e.pointerId)
    updateSplit(e.clientX)
  }

  const onPointerMove = (e: PointerEvent<HTMLDivElement>) => {
    if (!dragging.current) return
    updateSplit(e.clientX)
  }

  const onPointerUp = (e: PointerEvent<HTMLDivElement>) => {
    dragging.current = false
    e.currentTarget.releasePointerCapture(e.pointerId)
  }

  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'ArrowLeft') {
      e.preventDefault()
      setSplit(v => Math.max(0, v - 2))
    } else if (e.key === 'ArrowRight') {
      e.preventDefault()
      setSplit(v => Math.min(100, v + 2))
    }
  }

  /** 竖线位置 = 分界：左侧 protected，右侧 AI（overlay 从 split% 起显示） */
  const afterClip = `inset(0 0 0 ${split}%)`

  return (
    <div className="img-compare">
      <div
        ref={boxRef}
        className="img-compare-viewport img-compare-viewport--vertical jw-sample-mark"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
        onKeyDown={onKeyDown}
        tabIndex={0}
        role="slider"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(split)}
        aria-label={hint ?? beforeLabel}
      >
        <img className="img-compare-img img-compare-base" src={beforeSrc} alt={beforeAlt} draggable={false} />
        <div className="img-compare-after-wrap" style={{ clipPath: afterClip, WebkitClipPath: afterClip }}>
          <img className="img-compare-img img-compare-overlay" src={afterSrc} alt={afterAlt} draggable={false} />
        </div>
        <div className="img-compare-handle img-compare-handle--vertical" style={{ left: `${split}%` }} aria-hidden>
          <span className="img-compare-handle-line" />
          <span className="img-compare-handle-grip" aria-hidden>◀ ▶</span>
        </div>
      </div>
      <div className="img-compare-labels">
        <span>{beforeLabel}</span>
        <span>{afterLabel}</span>
      </div>
      {hint ? <p className="img-compare-hint text-secondary">{hint}</p> : null}
    </div>
  )
}
