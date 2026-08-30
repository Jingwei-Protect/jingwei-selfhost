import type { SponsorTier } from './types'

export type FrameStyle = 'default' | 'sustained' | 'deep' | 'patron'

export const TIER_ORDER: Record<SponsorTier, number> = {
  none: 0,
  supporter: 1,
  sustained: 2,
  deep: 3,
  patron: 4,
}

export const FRAME_STYLE_OPTIONS: {
  id: FrameStyle
  label: string
  minTier: SponsorTier
}[] = [
  { id: 'default', label: '标准', minTier: 'supporter' },
  { id: 'sustained', label: '淡蓝', minTier: 'sustained' },
  { id: 'deep', label: '金边', minTier: 'deep' },
  { id: 'patron', label: '彩虹', minTier: 'patron' },
]

export function meetsTier(user: SponsorTier, required: SponsorTier): boolean {
  return TIER_ORDER[user] >= TIER_ORDER[required]
}

export function frameStylesForTier(tier: SponsorTier): FrameStyle[] {
  return FRAME_STYLE_OPTIONS
    .filter(opt => meetsTier(tier, opt.minTier))
    .map(opt => opt.id)
}

export function isFrameStyleUnlocked(tier: SponsorTier, style: FrameStyle): boolean {
  const opt = FRAME_STYLE_OPTIONS.find(o => o.id === style)
  return !!opt && meetsTier(tier, opt.minTier)
}

export function frameStyleLabel(style: FrameStyle): string {
  return FRAME_STYLE_OPTIONS.find(o => o.id === style)?.label ?? style
}

/** Locked feature hint — no specific amounts. */
export const TIER_LOCKED_HINT = '更高支持档位解锁'
