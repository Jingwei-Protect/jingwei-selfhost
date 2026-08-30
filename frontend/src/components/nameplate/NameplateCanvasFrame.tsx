import type { RefObject } from 'react'
import { CANVAS_W, CANVAS_H } from './constants'
import type { FrameStyle } from './types'

interface Props {
  frameStyle?: FrameStyle
  canvasRef: RefObject<HTMLCanvasElement | null>
  cursor: string
  onPointerDown: (e: React.PointerEvent) => void
  onPointerMove: (e: React.PointerEvent) => void
  onPointerUp: () => void
}

export default function NameplateCanvasFrame({
  frameStyle = 'default',
  canvasRef,
  cursor,
  onPointerDown,
  onPointerMove,
  onPointerUp,
}: Props) {
  return (
    <div className="np-canvas-wrap">
      <div className={`np-canvas-frame np-frame-${frameStyle}`}>
        <div className="np-canvas-frame-inner">
          <span className="np-canvas-frame-wavy" aria-hidden="true" />
          <canvas
            ref={canvasRef}
            width={CANVAS_W}
            height={CANVAS_H}
            className="np-canvas"
            style={{ cursor }}
            onPointerDown={onPointerDown}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerUp}
            onPointerLeave={onPointerUp}
          />
        </div>
      </div>
    </div>
  )
}
