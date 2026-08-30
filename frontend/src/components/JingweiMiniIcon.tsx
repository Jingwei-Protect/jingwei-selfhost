import type { CSSProperties } from 'react'

export type JingweiMiniIconType =
  | 'bird'
  | 'pebble'
  | 'wave'
  | 'shield'
  | 'search'
  | 'watermark'
  | 'nameplate'
  | 'spark'
  | 'lock'
  | 'image'

interface Props {
  type: JingweiMiniIconType
  size?: number
  className?: string
  style?: CSSProperties
  title?: string
}

const TITLES: Record<JingweiMiniIconType, string> = {
  bird: '精卫鸟',
  pebble: '石子',
  wave: '海浪',
  shield: '保护',
  search: '验证',
  watermark: '水印',
  nameplate: '铭牌',
  spark: '发光',
  lock: '锁定',
  image: '图片',
}

/** Small hand-drawn SVG icons for Jingwei UI. No emoji, no external asset dependency. */
export default function JingweiMiniIcon({
  type,
  size = 28,
  className,
  style,
  title,
}: Props) {
  const label = title ?? TITLES[type]
  return (
    <svg
      viewBox="0 0 64 64"
      width={size}
      height={size}
      className={className}
      style={{ display: 'inline-block', flexShrink: 0, ...style }}
      role="img"
      aria-label={label}
    >
      <title>{label}</title>
      {renderIcon(type)}
    </svg>
  )
}

function renderIcon(type: JingweiMiniIconType) {
  const ink = '#1a1a1a'
  const blue = '#94b6df'
  const softBlue = '#d3e1f3'
  const gold = '#ffd966'
  const coral = '#ffb6a3'
  const green = '#cce8b5'

  switch (type) {
    case 'bird':
      return (
        <>
          <path d="M13 37c8-14 22-20 36-10-8 1-13 5-17 11-5 7-14 8-19-1Z" fill={softBlue} stroke={ink} strokeWidth="3" strokeLinejoin="round" />
          <path d="M33 24c2-6 7-9 14-9-2 5-5 9-10 12" fill={blue} stroke={ink} strokeWidth="3" strokeLinejoin="round" />
          <circle cx="25" cy="31" r="2.5" fill={ink} />
          <path d="M14 36 6 33l8-4" fill={gold} stroke={ink} strokeWidth="3" strokeLinejoin="round" />
          <path d="M32 39c2 5 7 7 13 6-3-4-6-7-10-9" fill="#fff" stroke={ink} strokeWidth="3" strokeLinejoin="round" />
        </>
      )
    case 'pebble':
      return (
        <>
          <path d="M17 37c-3-10 5-20 18-22 12-2 20 8 17 20-3 11-15 17-25 14-5-1-8-6-10-12Z" fill="#f4e7c3" stroke={ink} strokeWidth="3" strokeLinejoin="round" />
          <path d="M25 27c4-4 12-6 18-3" fill="none" stroke="#d2b06b" strokeWidth="3" strokeLinecap="round" />
        </>
      )
    case 'wave':
      return (
        <>
          <path d="M8 40c7-9 14-9 21 0s14 9 27 0" fill="none" stroke={ink} strokeWidth="3" strokeLinecap="round" />
          <path d="M8 29c6-7 12-7 18 0s12 7 23 0" fill="none" stroke={blue} strokeWidth="4" strokeLinecap="round" />
        </>
      )
    case 'shield':
      return (
        <>
          <path d="M32 8 51 16v14c0 13-8 22-19 26-11-4-19-13-19-26V16Z" fill={green} stroke={ink} strokeWidth="3" strokeLinejoin="round" />
          <path d="m23 32 6 6 13-15" fill="none" stroke={ink} strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
        </>
      )
    case 'search':
      return (
        <>
          <circle cx="27" cy="27" r="15" fill="#fff" stroke={ink} strokeWidth="3" />
          <path d="m38 38 14 14" stroke={ink} strokeWidth="4" strokeLinecap="round" />
          <path d="M20 27c4-5 9-7 16-4" fill="none" stroke={blue} strokeWidth="3" strokeLinecap="round" />
        </>
      )
    case 'watermark':
      return (
        <>
          <rect x="12" y="14" width="40" height="36" rx="5" fill="#fff" stroke={ink} strokeWidth="3" />
          <path d="M18 40c7-7 12-7 18 0s11 7 20 0" fill="none" stroke={blue} strokeWidth="3" strokeLinecap="round" />
          <circle cx="24" cy="25" r="4" fill={gold} stroke={ink} strokeWidth="2" />
        </>
      )
    case 'nameplate':
      return (
        <>
          <rect x="9" y="18" width="46" height="28" rx="6" fill={softBlue} stroke={ink} strokeWidth="3" />
          <path d="M16 31h22M16 38h14" stroke={ink} strokeWidth="3" strokeLinecap="round" />
          <path d="M44 27c2-4 6-4 8 0-1 4-4 6-8 8-4-2-7-4-8-8 2-4 6-4 8 0Z" fill={coral} stroke={ink} strokeWidth="2" />
        </>
      )
    case 'spark':
      return (
        <>
          <path d="M32 8 38 26 56 32 38 38 32 56 26 38 8 32 26 26Z" fill={gold} stroke={ink} strokeWidth="3" strokeLinejoin="round" />
          <path d="M48 10v9M43 15h10" stroke={ink} strokeWidth="3" strokeLinecap="round" />
        </>
      )
    case 'lock':
      return (
        <>
          <rect x="14" y="28" width="36" height="24" rx="5" fill={softBlue} stroke={ink} strokeWidth="3" />
          <path d="M22 28v-7c0-7 4-12 10-12s10 5 10 12v7" fill="none" stroke={ink} strokeWidth="3" strokeLinecap="round" />
          <circle cx="32" cy="40" r="3" fill={ink} />
        </>
      )
    case 'image':
      return (
        <>
          <rect x="10" y="13" width="44" height="38" rx="5" fill="#fff" stroke={ink} strokeWidth="3" />
          <circle cx="24" cy="26" r="5" fill={gold} stroke={ink} strokeWidth="2" />
          <path d="M15 45 27 34l8 7 6-5 8 9" fill={softBlue} stroke={ink} strokeWidth="3" strokeLinejoin="round" />
        </>
      )
  }
}
