import { useState, useRef, useCallback, useEffect } from 'react'
import { CANVAS_W, CANVAS_H, BG_COLOR, MAX_HISTORY, UPLOAD_IMAGE_MAX_BYTES } from './constants'
import type { Tool } from './constants'

function sprayAt(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  color: string,
  size: number,
  opacity = 1,
) {
  const density = Math.max(8, size * 4)
  ctx.fillStyle = color
  const r = size * 2
  const baseAlpha = Math.max(0.05, opacity)
  for (let i = 0; i < density; i++) {
    const angle = Math.random() * Math.PI * 2
    const dist = Math.random() * r
    ctx.globalAlpha = baseAlpha * (0.35 + Math.random() * 0.65)
    ctx.beginPath()
    ctx.arc(x + Math.cos(angle) * dist, y + Math.sin(angle) * dist, 0.6 + Math.random(), 0, Math.PI * 2)
    ctx.fill()
  }
  ctx.globalAlpha = 1
}

function drawSticker(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  type: 'star' | 'heart' | 'sparkle',
  color: string,
  size: number,
) {
  ctx.fillStyle = color
  ctx.font = `${size * 3}px serif`
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  const ch = type === 'star' ? '⭐' : type === 'heart' ? '❤️' : '✨'
  ctx.fillText(ch, x, y)
}

/** Tiny brush stamps for star / heart trail (vector drawn, color-controllable). */
function drawStarStamp(ctx: CanvasRenderingContext2D, cx: number, cy: number, r: number, color: string) {
  const spikes = 5
  const outer = r
  const inner = r * 0.45
  ctx.beginPath()
  for (let i = 0; i < spikes * 2; i++) {
    const radius = i % 2 === 0 ? outer : inner
    const angle = (Math.PI / spikes) * i - Math.PI / 2
    const x = cx + Math.cos(angle) * radius
    const y = cy + Math.sin(angle) * radius
    if (i === 0) ctx.moveTo(x, y)
    else ctx.lineTo(x, y)
  }
  ctx.closePath()
  ctx.fillStyle = color
  ctx.fill()
}

function drawHeartStamp(ctx: CanvasRenderingContext2D, cx: number, cy: number, r: number, color: string) {
  const s = r * 0.85
  ctx.beginPath()
  ctx.moveTo(cx, cy + s * 0.7)
  ctx.bezierCurveTo(cx + s * 1.4, cy - s * 0.2, cx + s * 0.6, cy - s * 1.0, cx, cy - s * 0.3)
  ctx.bezierCurveTo(cx - s * 0.6, cy - s * 1.0, cx - s * 1.4, cy - s * 0.2, cx, cy + s * 0.7)
  ctx.closePath()
  ctx.fillStyle = color
  ctx.fill()
}

function parseHexColor(hex: string): [number, number, number] {
  const h = hex.replace('#', '')
  return [
    parseInt(h.slice(0, 2), 16),
    parseInt(h.slice(2, 4), 16),
    parseInt(h.slice(4, 6), 16),
  ]
}

function withAlpha(hex: string, alpha: number): string {
  const [r, g, b] = parseHexColor(hex)
  return `rgba(${r},${g},${b},${Math.max(0, Math.min(1, alpha))})`
}

function initCanvas(ctx: CanvasRenderingContext2D) {
  ctx.fillStyle = BG_COLOR
  ctx.fillRect(0, 0, CANVAS_W, CANVAS_H)
}

function floodFill(ctx: CanvasRenderingContext2D, startX: number, startY: number, fillHex: string) {
  const w = CANVAS_W
  const h = CANVAS_H
  const img = ctx.getImageData(0, 0, w, h)
  const data = img.data
  const px = Math.max(0, Math.min(w - 1, Math.round(startX)))
  const py = Math.max(0, Math.min(h - 1, Math.round(startY)))
  const startIdx = (py * w + px) * 4
  const target = [data[startIdx], data[startIdx + 1], data[startIdx + 2], data[startIdx + 3]]
  const [fr, fg, fb] = parseHexColor(fillHex)

  if (
    target[0] === fr &&
    target[1] === fg &&
    target[2] === fb &&
    target[3] === 255
  ) {
    return
  }

  const matches = (idx: number) =>
    data[idx] === target[0] &&
    data[idx + 1] === target[1] &&
    data[idx + 2] === target[2] &&
    data[idx + 3] === target[3]

  const stack: [number, number][] = [[px, py]]
  const visited = new Uint8Array(w * h)

  while (stack.length > 0) {
    const [x, y] = stack.pop()!
    const vi = y * w + x
    if (x < 0 || y < 0 || x >= w || y >= h || visited[vi]) continue
    const idx = vi * 4
    if (!matches(idx)) continue
    visited[vi] = 1
    data[idx] = fr
    data[idx + 1] = fg
    data[idx + 2] = fb
    data[idx + 3] = 255
    stack.push([x + 1, y], [x - 1, y], [x, y + 1], [x, y - 1])
  }

  ctx.putImageData(img, 0, 0)
}

export function useNameplateCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const historyRef = useRef<ImageData[]>([])
  const redoRef = useRef<ImageData[]>([])
  const snapshotRef = useRef<ImageData | null>(null)
  const startPos = useRef<{ x: number; y: number } | null>(null)
  const lastPos = useRef<{ x: number; y: number } | null>(null)
  const drawingRef = useRef(false)

  const [color, setColor] = useState('#1d1d1f')
  const [brushSize, setBrushSize] = useState(4)
  const [brushOpacity, setBrushOpacity] = useState(100)
  const [tool, setTool] = useState<Tool>('pencil')
  const [canUndo, setCanUndo] = useState(false)
  const [canRedo, setCanRedo] = useState(false)

  const pushHistory = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')!
    const snap = ctx.getImageData(0, 0, CANVAS_W, CANVAS_H)
    historyRef.current.push(snap)
    if (historyRef.current.length > MAX_HISTORY) historyRef.current.shift()
    redoRef.current = []
    setCanUndo(true)
    setCanRedo(false)
  }, [])

  const restore = useCallback((snap: ImageData) => {
    canvasRef.current?.getContext('2d')!.putImageData(snap, 0, 0)
  }, [])

  const undo = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas || historyRef.current.length === 0) return
    const ctx = canvas.getContext('2d')!
    redoRef.current.push(ctx.getImageData(0, 0, CANVAS_W, CANVAS_H))
    restore(historyRef.current.pop()!)
    setCanUndo(historyRef.current.length > 0)
    setCanRedo(true)
  }, [restore])

  const redo = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas || redoRef.current.length === 0) return
    const ctx = canvas.getContext('2d')!
    historyRef.current.push(ctx.getImageData(0, 0, CANVAS_W, CANVAS_H))
    restore(redoRef.current.pop()!)
    setCanUndo(true)
    setCanRedo(redoRef.current.length > 0)
  }, [restore])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    initCanvas(canvas.getContext('2d')!)
  }, [])

  const getPos = (e: React.PointerEvent) => {
    const canvas = canvasRef.current!
    const rect = canvas.getBoundingClientRect()
    return {
      x: (e.clientX - rect.left) * (CANVAS_W / rect.width),
      y: (e.clientY - rect.top) * (CANVAS_H / rect.height),
    }
  }

  const strokeLine = useCallback((
    from: { x: number; y: number },
    to: { x: number; y: number },
    t: Tool,
    c: string,
    size: number,
    opacity: number,
  ) => {
    const ctx = canvasRef.current?.getContext('2d')
    if (!ctx) return
    const alpha = Math.max(0, Math.min(1, opacity))

    if (t === 'eraser') {
      ctx.globalCompositeOperation = 'destination-out'
      ctx.strokeStyle = 'rgba(0,0,0,1)'
    } else {
      ctx.globalCompositeOperation = 'source-over'
      ctx.strokeStyle = withAlpha(c, alpha)
    }

    ctx.lineWidth = t === 'pencil' ? Math.max(1, size * 0.6) : size
    ctx.lineCap = 'round'
    ctx.lineJoin = 'round'
    ctx.globalAlpha = t === 'eraser' ? 1 : alpha

    // 发光画笔：先描宽柔光层，再描芯
    if (t === 'glow') {
      ctx.save()
      ctx.shadowColor = withAlpha(c, alpha)
      ctx.shadowBlur = size * 2.4
      ctx.lineWidth = size * 1.6
      ctx.beginPath()
      if (from.x === to.x && from.y === to.y) {
        ctx.arc(from.x, from.y, ctx.lineWidth / 2, 0, Math.PI * 2)
        ctx.fillStyle = withAlpha(c, alpha)
        ctx.fill()
      } else {
        ctx.moveTo(from.x, from.y)
        ctx.lineTo(to.x, to.y)
        ctx.stroke()
      }
      ctx.restore()
      // 中心高亮
      ctx.lineWidth = Math.max(1, size * 0.55)
      ctx.strokeStyle = withAlpha('#ffffff', alpha * 0.9)
      ctx.globalAlpha = alpha * 0.9
    }

    ctx.beginPath()
    if (from.x === to.x && from.y === to.y) {
      ctx.arc(from.x, from.y, ctx.lineWidth / 2, 0, Math.PI * 2)
      ctx.fillStyle = t === 'eraser'
        ? 'rgba(0,0,0,1)'
        : t === 'glow'
          ? withAlpha('#ffffff', alpha * 0.9)
          : withAlpha(c, alpha)
      ctx.fill()
    } else {
      ctx.moveTo(from.x, from.y)
      ctx.lineTo(to.x, to.y)
      ctx.stroke()
    }

    ctx.globalAlpha = 1
    ctx.globalCompositeOperation = 'source-over'
  }, [])

  /** Read pixel color under (x, y) and return as '#rrggbb'. */
  const pickColor = useCallback((x: number, y: number): string | null => {
    const canvas = canvasRef.current
    if (!canvas) return null
    const ctx = canvas.getContext('2d')!
    const px = Math.max(0, Math.min(CANVAS_W - 1, Math.round(x)))
    const py = Math.max(0, Math.min(CANVAS_H - 1, Math.round(y)))
    const data = ctx.getImageData(px, py, 1, 1).data
    const [r, g, b, a] = data
    if (a === 0) return null  // transparent pixel — keep current color
    const hex = (n: number) => n.toString(16).padStart(2, '0')
    return `#${hex(r)}${hex(g)}${hex(b)}`
  }, [])

  const onPointerDown = (e: React.PointerEvent) => {
    const pos = getPos(e)
    const canvas = canvasRef.current!
    const ctx = canvas.getContext('2d')!

    if (tool === 'eyedropper') {
      const picked = pickColor(pos.x, pos.y)
      if (picked) setColor(picked)
      return
    }

    if (tool === 'fill') {
      pushHistory()
      ctx.globalAlpha = brushOpacity / 100
      floodFill(ctx, pos.x, pos.y, color)
      ctx.globalAlpha = 1
      return
    }

    const paintAlpha = brushOpacity / 100

    // sparkle 保持「单击盖章」语义；star / heart 升级为画笔（按住拖动留下轨迹）
    if (tool === 'sparkle') {
      pushHistory()
      ctx.globalAlpha = paintAlpha
      drawSticker(ctx, pos.x, pos.y, 'sparkle', color, brushSize)
      ctx.globalAlpha = 1
      return
    }

    drawingRef.current = true
    startPos.current = pos
    lastPos.current = pos
    ;(e.target as HTMLElement).setPointerCapture(e.pointerId)

    if (tool === 'star' || tool === 'heart') {
      pushHistory()
      const stampFn = tool === 'star' ? drawStarStamp : drawHeartStamp
      ctx.globalAlpha = paintAlpha
      stampFn(ctx, pos.x, pos.y, brushSize * 1.5, withAlpha(color, paintAlpha))
      ctx.globalAlpha = 1
      return
    }

    if (['line', 'rect', 'ellipse'].includes(tool)) {
      snapshotRef.current = ctx.getImageData(0, 0, CANVAS_W, CANVAS_H)
      pushHistory()
    } else if (tool === 'spray') {
      pushHistory()
      sprayAt(ctx, pos.x, pos.y, color, brushSize, paintAlpha)
    } else {
      pushHistory()
      strokeLine(pos, pos, tool, color, brushSize, paintAlpha)
    }
  }

  const onPointerMove = (e: React.PointerEvent) => {
    if (!drawingRef.current || !startPos.current) return
    const pos = getPos(e)
    const canvas = canvasRef.current!
    const ctx = canvas.getContext('2d')!

    const paintAlpha = brushOpacity / 100

    if (['line', 'rect', 'ellipse'].includes(tool)) {
      if (snapshotRef.current) ctx.putImageData(snapshotRef.current, 0, 0)
      ctx.strokeStyle = withAlpha(color, paintAlpha)
      ctx.lineWidth = brushSize
      ctx.lineCap = 'round'
      ctx.globalAlpha = paintAlpha
      const x0 = startPos.current.x, y0 = startPos.current.y
      if (tool === 'line') {
        ctx.beginPath()
        ctx.moveTo(x0, y0)
        ctx.lineTo(pos.x, pos.y)
        ctx.stroke()
      } else if (tool === 'rect') {
        ctx.strokeRect(Math.min(x0, pos.x), Math.min(y0, pos.y), Math.abs(pos.x - x0), Math.abs(pos.y - y0))
      } else {
        const cx = (x0 + pos.x) / 2, cy = (y0 + pos.y) / 2
        ctx.beginPath()
        ctx.ellipse(cx, cy, Math.abs(pos.x - x0) / 2 || 0.5, Math.abs(pos.y - y0) / 2 || 0.5, 0, 0, Math.PI * 2)
        ctx.stroke()
      }
      ctx.globalAlpha = 1
      return
    }

    if (tool === 'spray') {
      sprayAt(ctx, pos.x, pos.y, color, brushSize, paintAlpha)
    } else if (tool === 'star' || tool === 'heart') {
      // 间距控制：避免过密；2 倍 brushSize 间距
      if (lastPos.current) {
        const dx = pos.x - lastPos.current.x
        const dy = pos.y - lastPos.current.y
        const dist = Math.hypot(dx, dy)
        const spacing = Math.max(4, brushSize * 1.6)
        if (dist >= spacing) {
          const stampFn = tool === 'star' ? drawStarStamp : drawHeartStamp
          ctx.globalAlpha = paintAlpha
          stampFn(ctx, pos.x, pos.y, brushSize * 1.5, withAlpha(color, paintAlpha))
          ctx.globalAlpha = 1
          lastPos.current = pos
        }
        return  // 不更新 lastPos 在距离不够时，让下一次有累积
      }
    } else if (['pencil', 'marker', 'eraser', 'glow'].includes(tool) && lastPos.current) {
      strokeLine(lastPos.current, pos, tool, color, brushSize, paintAlpha)
    }
    lastPos.current = pos
  }

  const onPointerUp = () => {
    drawingRef.current = false
    startPos.current = null
    lastPos.current = null
    snapshotRef.current = null
  }

  const clearCanvas = () => {
    pushHistory()
    initCanvas(canvasRef.current!.getContext('2d')!)
  }

  const exportImage = () => canvasRef.current?.toDataURL('image/png') ?? ''

  const importImageFromFile = useCallback(async (file: File) => {
    if (!file.type.startsWith('image/')) {
      throw new Error('unsupported')
    }
    if (file.size > UPLOAD_IMAGE_MAX_BYTES) {
      throw new Error('too_large')
    }
    const canvas = canvasRef.current
    if (!canvas) throw new Error('no_canvas')
    const dataUrl = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = () => resolve(String(reader.result))
      reader.onerror = () => reject(new Error('read_failed'))
      reader.readAsDataURL(file)
    })
    await new Promise<void>((resolve, reject) => {
      const img = new Image()
      img.onload = () => {
        const ctx = canvas.getContext('2d')
        if (!ctx) {
          reject(new Error('no_ctx'))
          return
        }
        pushHistory()
        initCanvas(ctx)
        // cover：铺满 5:2 画布，居中裁剪，不留白边
        const scale = Math.max(CANVAS_W / img.width, CANVAS_H / img.height)
        const dw = img.width * scale
        const dh = img.height * scale
        const dx = (CANVAS_W - dw) / 2
        const dy = (CANVAS_H - dh) / 2
        ctx.drawImage(img, dx, dy, dw, dh)
        resolve()
      }
      img.onerror = () => reject(new Error('decode_failed'))
      img.src = dataUrl
    })
  }, [pushHistory])

  const cursorForTool = tool === 'eyedropper' || tool === 'fill'
    ? 'cell'
    : tool === 'sparkle'
      ? 'copy'
      : 'crosshair'

  return {
    canvasRef,
    color,
    setColor,
    brushSize,
    setBrushSize,
    brushOpacity,
    setBrushOpacity,
    tool,
    setTool,
    canUndo,
    canRedo,
    undo,
    redo,
    clearCanvas,
    exportImage,
    importImageFromFile,
    onPointerDown,
    onPointerMove,
    onPointerUp,
    cursorForTool,
  }
}
