import WigglyButton from './WigglyButton'
import {
  FRAME_STYLE_OPTIONS,
  TIER_LOCKED_HINT,
  isFrameStyleUnlocked,
  type FrameStyle,
} from './frameStyles'
import type { SponsorTier } from './types'
import { useLocale } from '../../i18n/LocaleContext'

interface Props {
  value: FrameStyle
  onChange: (style: FrameStyle) => void
  userTier?: SponsorTier
}

export default function NameplateFramePicker({ value, onChange, userTier = 'supporter' }: Props) {
  const { messages: m } = useLocale()
  const t = m.components.nameplate
  return (
    <div className="np-frame-picker">
      <span className="np-frame-picker-label">{t.frameStyle}</span>
      <div className="np-frame-picker-options">
        {FRAME_STYLE_OPTIONS.map(opt => {
          const unlocked = isFrameStyleUnlocked(userTier, opt.id)
          return (
            <WigglyButton
              key={opt.id}
              active={value === opt.id}
              disabled={!unlocked}
              className={`np-frame-chip${!unlocked ? ' np-frame-chip-locked' : ''}`}
              title={unlocked ? opt.label : `${opt.label}（${TIER_LOCKED_HINT}）`}
              onClick={() => unlocked && onChange(opt.id)}
            >
              <span className={`np-frame-chip-preview np-frame-${opt.id}`} aria-hidden="true" />
              <span className="np-frame-chip-text">{opt.label}</span>
            </WigglyButton>
          )
        })}
      </div>
    </div>
  )
}
