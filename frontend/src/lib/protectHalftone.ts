import type { VisibleAddPlacement } from '../components/VisibleLayerEditor'

export type HalftoneStyle = 'ascii_chars' | 'halftone_dots'

export const DEFAULT_HALFTONE_ANCHOR = { x: 0.5, y: 0.54 }

export function halftoneAnchorFromPlacements(
  placements: VisibleAddPlacement[] | undefined,
): { x: number; y: number } | null {
  const p = placements?.find(item => item.layer === 'halftone_signature')
  return p ? { x: p.x, y: p.y } : null
}

export function resolveHalftoneAnchor(
  placements: VisibleAddPlacement[] | undefined,
  halftoneOn: boolean,
  placementEnabled: boolean,
): { x: number; y: number } | null {
  if (!halftoneOn || !placementEnabled) return null
  return halftoneAnchorFromPlacements(placements) ?? DEFAULT_HALFTONE_ANCHOR
}

/** Anchor travels via halftone_anchor_x/y — omit from visible_add_points JSON. */
export function placementsForVisibleEditApi(
  placements: VisibleAddPlacement[] | undefined | null,
): VisibleAddPlacement[] {
  return (placements ?? []).filter(p => p.layer !== 'halftone_signature')
}

export function appendHalftoneFields(
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
    backgroundChain: number
    contourWarp: number
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
  fd.append('halftone_background_chain', String(opts.backgroundChain))
  fd.append('halftone_contour_warp', String(opts.contourWarp))
}
