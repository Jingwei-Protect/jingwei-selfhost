/** 与 ``core/ascii_watermark._author_mask_font_size`` 对齐的预览字号。 */

export const HALFTONE_REF_LONG_SIDE = 1280

export function lerpUi(value: number, lo: number, hi: number): number {
  const t = Math.max(0, Math.min(100, value)) / 100
  return lo + t * (hi - lo)
}

export function halftoneAuthorMaskScale(signatureSize: number): number {
  return lerpUi(signatureSize, 0.55, 1.35)
}

export function halftoneAuthorMaskFontRatio(maskScale: number): number {
  const scale = Math.max(0.4, Math.min(2.5, maskScale))
  const t = (scale - 0.55) / (1.35 - 0.55)
  return 0.050 + Math.max(0, Math.min(1, t)) * (0.120 - 0.050)
}

/** 图像像素坐标下的署名字号（未乘 CSS 显示缩放）。 */
export function halftoneAuthorFontPxNatural(
  imgNatural: { w: number; h: number },
  signatureSize: number,
): number {
  const shortSide = Math.max(12, Math.min(imgNatural.w, imgNatural.h))
  const ratio = halftoneAuthorMaskFontRatio(halftoneAuthorMaskScale(signatureSize))
  let fontPx = Math.max(12, Math.floor(shortSide * ratio))
  fontPx = Math.min(fontPx, Math.max(12, Math.floor(shortSide * 0.42)))
  return fontPx
}

/** 摆放虚线框内文字字号（屏幕像素）。 */
export function halftoneAuthorFontPxDisplay(
  imgNatural: { w: number; h: number },
  renderSize: { w: number; h: number },
  signatureSize: number,
): number {
  if (imgNatural.w <= 0 || imgNatural.h <= 0 || renderSize.w <= 0) return 11
  const natural = halftoneAuthorFontPxNatural(imgNatural, signatureSize)
  const scale = renderSize.w / imgNatural.w
  return Math.max(11, natural * scale)
}
