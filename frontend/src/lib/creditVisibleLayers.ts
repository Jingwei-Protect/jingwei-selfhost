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
