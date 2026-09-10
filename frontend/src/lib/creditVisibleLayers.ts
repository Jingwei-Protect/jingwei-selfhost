/** 署名·快速 visible-layer switch — shared by ProtectPage and tests. */

export type CreditVisibleMark = 'auto' | 'ascii' | 'displacement'

export type CreditHintKind = 'flat' | 'mixed' | 'rich'

/** Dog c024 rung locked into 署名·快速 displacement. */
export const CREDIT_DISP_FONT_RATIO = 0.07
export const CREDIT_DISP_SHIFT = 3
export const CREDIT_DISP_SHADOW_STRENGTH = 0.1518

export type CreditVisibleLayers = {
  asciiEnabled: boolean
  dispEnabled: boolean
  dispFontRatio: number
  dispShift: number
  dispShadow: boolean
  dispShadowStrength: number
}

export function creditUsesAscii(
  mark: CreditVisibleMark,
  hintKind: CreditHintKind | null | undefined,
): boolean {
  return mark === 'ascii' || (mark === 'auto' && hintKind === 'flat')
}

/**
 * Next visible-layer flags for 署名·快速.
 *
 * Texture / forced displacement never leaves ASCII on (a leftover 更多选项
 * checkbox must not paint a letter grid on the puppy). Displacement strength
 * is always c024, including before the flat/texture hint arrives.
 */
export function nextCreditVisibleLayers(
  mark: CreditVisibleMark,
  hintKind: CreditHintKind | null | undefined,
): CreditVisibleLayers {
  if (creditUsesAscii(mark, hintKind)) {
    return {
      asciiEnabled: true,
      dispEnabled: false,
      dispFontRatio: CREDIT_DISP_FONT_RATIO,
      dispShift: CREDIT_DISP_SHIFT,
      dispShadow: true,
      dispShadowStrength: CREDIT_DISP_SHADOW_STRENGTH,
    }
  }
  return {
    asciiEnabled: false,
    dispEnabled: true,
    dispFontRatio: CREDIT_DISP_FONT_RATIO,
    dispShift: CREDIT_DISP_SHIFT,
    dispShadow: true,
    dispShadowStrength: CREDIT_DISP_SHADOW_STRENGTH,
  }
}

/** On-image credit text. Empty 画面署名 falls back to 创作者姓名 at send time. */
export function creditVisibleName(sign: string, author: string): string {
  const trimmedSign = sign.trim()
  if (trimmedSign) return trimmedSign
  return author.trim()
}

/** 署名·快速 displacement is auto-placed; leftover dashed boxes must not drag it. */
export function stripCreditDispPlacements<T extends { layer: string }>(
  isCredit: boolean,
  placements: T[],
): T[] {
  if (!isCredit) return placements
  return placements.filter(p => p.layer !== 'displacement')
}

export type CreditDispPin = {
  x: number
  y: number
  w?: number
  h?: number
}

/** Default dashed-box pin from the server hint (best-host). Fallback: canvas centre. */
export function creditDispPinFromHint(hint: {
  credit_disp_x?: number
  credit_disp_y?: number
  credit_disp_w?: number
  credit_disp_h?: number
} | null | undefined): CreditDispPin {
  const x = hint?.credit_disp_x
  const y = hint?.credit_disp_y
  if (typeof x === 'number' && typeof y === 'number') {
    return {
      x,
      y,
      w: hint?.credit_disp_w,
      h: hint?.credit_disp_h,
    }
  }
  return { x: 0.5, y: 0.5 }
}
