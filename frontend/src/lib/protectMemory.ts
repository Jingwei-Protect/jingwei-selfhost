/** Protect-page memory budget helpers.

The visible-layer editor used to snapshot three full-resolution RGBA
buffers on every placement drag. These helpers keep placement history
tiny and cap mask/work surfaces so the tab does not grow with image area.
*/

export const EDITOR_MASK_MAX_EDGE = 1024
export const EDITOR_HISTORY_MAX = 20
export const COMPARISON_MAX_EDGE = 960

export type EditorHistoryOp =
  | 'add'
  | 'delete'
  | 'move'
  | 'resize'
  | 'erase'
  | 'blur'
  | 'clear'

export type EditorHistoryEntry<T, M = null> = {
  placements: T
  mask: M
  blur: M
  eraseExport: M
}

/** Placement / resize / delete must not copy mask pixels. */
export function shouldSnapshotMasks(op: string): boolean {
  return op === 'erase' || op === 'blur'
}

/** Working canvas size for erase/blur — never larger than ``maxEdge``. */
export function workingCanvasSize(
  naturalW: number,
  naturalH: number,
  maxEdge: number = EDITOR_MASK_MAX_EDGE,
): { w: number; h: number } {
  const width = Math.max(0, Math.round(naturalW))
  const height = Math.max(0, Math.round(naturalH))
  const longEdge = Math.max(width, height)
  if (width <= 0 || height <= 0) return { w: 0, h: 0 }
  if (longEdge <= maxEdge) return { w: width, h: height }
  const scale = maxEdge / longEdge
  return {
    w: Math.max(1, Math.round(width * scale)),
    h: Math.max(1, Math.round(height * scale)),
  }
}

export function placementOnlySnapshot<T>(placements: T): EditorHistoryEntry<T, null> {
  return {
    placements,
    mask: null,
    blur: null,
    eraseExport: null,
  }
}

/** Append a history entry, drop redo tail, and cap length from the front. */
export function pushCappedHistory<T, M>(
  history: EditorHistoryEntry<T, M>[],
  currentIndex: number,
  next: EditorHistoryEntry<T, M>,
  maxLen: number = EDITOR_HISTORY_MAX,
): { history: EditorHistoryEntry<T, M>[]; index: number } {
  const cap = Math.max(1, maxLen)
  let nextHistory = history.slice(0, Math.max(0, currentIndex + 1))
  nextHistory = [...nextHistory, next]
  if (nextHistory.length > cap) {
    nextHistory = nextHistory.slice(nextHistory.length - cap)
  }
  return { history: nextHistory, index: nextHistory.length - 1 }
}

export function isRevocableObjectUrl(url: string | null | undefined): url is string {
  return Boolean(url && url.startsWith('blob:'))
}
