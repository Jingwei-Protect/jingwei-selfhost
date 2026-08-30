import iconSave from '../../assets/paint-icons/save.png'
import iconEye from '../../assets/paint-icons/eye.png'
import iconTrash from '../../assets/paint-icons/trash.png'
import WigglyButton from './WigglyButton'
import { TIER_LOCKED_HINT, TIER_ORDER, meetsTier } from './frameStyles'
import { UPLOAD_IMAGE_ACCEPT, UPLOAD_IMAGE_MIN_TIER, UPLOAD_IMAGE_MIN_YUAN } from './constants'
import type { TextEffect, SponsorTier } from './types'
import { useLocale } from '../../i18n/LocaleContext'
import { useRef } from 'react'

const EFFECT_REQUIRED_TIER: Record<TextEffect, SponsorTier> = {
  normal: 'none',
  gold: 'deep',
  rainbow: 'deep',
}

interface Props {
  username: string
  onUsernameChange: (v: string) => void
  textEffect: TextEffect
  onTextEffectChange: (v: TextEffect) => void
  showEffectPreview: boolean
  onToggleEffectPreview: () => void
  onSave: () => void
  onClear: () => void
  onUploadImage?: (file: File) => void
  userTier?: SponsorTier
}

export default function NameplateTopBar({
  username,
  onUsernameChange,
  textEffect,
  onTextEffectChange,
  showEffectPreview,
  onToggleEffectPreview,
  onSave,
  onClear,
  onUploadImage,
  userTier = 'supporter',
}: Props) {
  const { messages: m } = useLocale()
  const t = m.components.nameplate
  const fileInputRef = useRef<HTMLInputElement>(null)
  const uploadDevBypass = import.meta.env.DEV
    && typeof localStorage !== 'undefined'
    && localStorage.getItem('jw-np-upload-dev') === '1'
  const uploadUnlocked = meetsTier(userTier, UPLOAD_IMAGE_MIN_TIER) || uploadDevBypass
  const uploadTitle = uploadUnlocked
    ? t.uploadImage
    : t.uploadImageLocked.replace('{yuan}', String(UPLOAD_IMAGE_MIN_YUAN))
  const EFFECT_LABELS: Record<TextEffect, string> = {
    normal: t.effects.normal,
    gold: t.effects.gold,
    rainbow: t.effects.rainbow,
  }
  return (
    <header className="np-top-bar">
      <input
        className="np-username-input"
        value={username}
        onChange={e => onUsernameChange(e.target.value.slice(0, 16))}
        placeholder={t.usernamePlaceholder}
        maxLength={16}
      />

      {showEffectPreview && (
        <div className="np-effect-picker">
          {(['normal', 'gold', 'rainbow'] as TextEffect[]).map(eff => {
            const req = EFFECT_REQUIRED_TIER[eff]
            const locked = TIER_ORDER[userTier] < TIER_ORDER[req]
            const title = locked
              ? `文字特效：${EFFECT_LABELS[eff]}（${TIER_LOCKED_HINT}）`
              : `文字特效：${EFFECT_LABELS[eff]}`
            return (
              <WigglyButton
                key={eff}
                active={textEffect === eff}
                className={`np-effect-chip${locked ? ' np-effect-chip-locked' : ''}`}
                disabled={locked}
                onClick={() => !locked && onTextEffectChange(eff)}
                title={title}
              >
                <span className={`np-effect-preview np-effect-${eff}`}>
                  {username.trim() || t.effectPreview}
                </span>
                {locked && <span className="np-effect-lock" aria-hidden="true">🔒</span>}
              </WigglyButton>
            )
          })}
        </div>
      )}

      <div className="np-top-actions">
        <input
          ref={fileInputRef}
          type="file"
          accept={UPLOAD_IMAGE_ACCEPT}
          hidden
          onChange={e => {
            const file = e.target.files?.[0]
            e.target.value = ''
            if (file && uploadUnlocked) onUploadImage?.(file)
          }}
        />
        <WigglyButton
          className={`np-upload-btn${uploadUnlocked ? '' : ' np-upload-btn-locked'}`}
          disabled={!uploadUnlocked || !onUploadImage}
          onClick={() => uploadUnlocked && fileInputRef.current?.click()}
          title={uploadTitle}
        >
          {uploadUnlocked ? t.uploadImage : `🔒 ${t.uploadImage}`}
        </WigglyButton>
        <WigglyButton icon className="np-top-icon-btn" onClick={onSave} title={t.save}>
          <img src={iconSave} alt="" className="np-tool-img" />
        </WigglyButton>
        <WigglyButton
          icon
          active={showEffectPreview}
          className="np-top-icon-btn"
          onClick={onToggleEffectPreview}
          title={t.effectPreview}
        >
          <img src={iconEye} alt="" className="np-tool-img" />
        </WigglyButton>
        <WigglyButton icon className="np-top-icon-btn" onClick={onClear} title={m.components.visibleLayerEditor.clear}>
          <img src={iconTrash} alt="" className="np-tool-img" />
        </WigglyButton>
      </div>
    </header>
  )
}
