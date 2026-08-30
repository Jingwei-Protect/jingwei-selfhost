import type { TextEffect, FrameStyle } from './types'
import { useLocale } from '../../i18n/LocaleContext'

export function NameplateCard({
  order,
  username,
  imageData,
  textEffect = 'rainbow',
  frameStyle = 'default',
  placeholder = false,
}: {
  order: number
  username: string
  imageData?: string | null
  textEffect?: TextEffect
  frameStyle?: FrameStyle
  placeholder?: boolean
}) {
  const { messages: m } = useLocale()
  const t = m.components.nameplate
  const frameClass = frameStyle && frameStyle !== 'default' ? ` np-frame-${frameStyle}` : ''

  return (
    <div className="np-card">
      <div className={`np-card-frame${frameClass}`}>
        {imageData ? (
          <img src={imageData} alt={`${username} ${t.save}`} className="np-card-img" />
        ) : (
          <div className="np-card-placeholder">
            {placeholder ? '✨' : '—'}
          </div>
        )}
      </div>
      <div className="np-card-meta">
        <span className="np-card-badge">#{String(order).padStart(3, '0')}</span>
        <span className={`np-card-name np-effect-${textEffect}`}>{username}</span>
      </div>
    </div>
  )
}
