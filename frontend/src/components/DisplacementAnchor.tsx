import { useRef, useCallback } from 'react'

interface Props {
  anchor: { x: number; y: number } | null
  onChange: (anchor: { x: number; y: number }) => void
  onDragEnd?: (anchor: { x: number; y: number }) => void
  maxHeight?: number
  /** 仅拖动图钉本身，不占用整图点击区域（用于保护后结果图） */
  pinOnly?: boolean
}

/** Draggable pin on image preview — sets normalized anchor (0–1). */
export default function DisplacementAnchor({
  anchor,
  onChange,
  onDragEnd,
  maxHeight = 280,
  pinOnly = false,
}: Props) {
  const wrapRef = useRef<HTMLDivElement>(null)
  const dragging = useRef(false)

  const updateFromEvent = useCallback((clientX: number, clientY: number) => {
    const wrap = wrapRef.current
    if (!wrap) return
    const rect = wrap.getBoundingClientRect()
    const x = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width))
    const y = Math.max(0, Math.min(1, (clientY - rect.top) / rect.height))
    onChange({ x, y })
  }, [onChange])

  const onWrapPointerDown = (e: React.PointerEvent) => {
    if (pinOnly) return
    dragging.current = true
    ;(e.target as HTMLElement).setPointerCapture(e.pointerId)
    updateFromEvent(e.clientX, e.clientY)
  }

  const onPinPointerDown = (e: React.PointerEvent) => {
    e.stopPropagation()
    dragging.current = true
    ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
    updateFromEvent(e.clientX, e.clientY)
  }

  const onPointerMove = (e: React.PointerEvent) => {
    if (!dragging.current) return
    updateFromEvent(e.clientX, e.clientY)
  }

  const finishDrag = (e: React.PointerEvent) => {
    if (!dragging.current) return
    dragging.current = false
    const wrap = wrapRef.current
    if (!wrap) return
    const rect = wrap.getBoundingClientRect()
    const x = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width))
    const y = Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height))
    onChange({ x, y })
    onDragEnd?.({ x, y })
  }

  const pinX = anchor ? `${anchor.x * 100}%` : '50%'
  const pinY = anchor ? `${anchor.y * 100}%` : '50%'

  return (
    <div
      ref={wrapRef}
      className={`disp-anchor-wrap${pinOnly ? ' disp-anchor-wrap--pin-only' : ''}`}
      style={{ maxHeight, cursor: pinOnly ? 'default' : 'crosshair', touchAction: 'none' }}
      onPointerDown={onWrapPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={finishDrag}
      onPointerLeave={finishDrag}
    >
      <div
        className="disp-anchor-pin"
        style={{ left: pinX, top: pinY }}
        title="拖动指定水印放置区域"
        onPointerDown={onPinPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={finishDrag}
      />
      {!anchor && !pinOnly && (
        <div className="disp-anchor-hint">点击或拖动图钉，指定水印主要放置位置</div>
      )}
      {!anchor && pinOnly && (
        <div className="disp-anchor-hint">拖动图钉，调整位移水印位置</div>
      )}
    </div>
  )
}
