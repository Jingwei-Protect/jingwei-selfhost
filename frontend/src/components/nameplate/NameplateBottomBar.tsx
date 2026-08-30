import WigglyButton from './WigglyButton'
import { useLocale } from '../../i18n/LocaleContext'

interface Props {
  brushSize: number
  toolLabel: string
  onCancel?: () => void
  onSave: () => void
}

export default function NameplateBottomBar({ brushSize, toolLabel, onCancel, onSave }: Props) {
  const { messages: m } = useLocale()
  const t = m.components.nameplate
  return (
    <footer className="np-bottom-bar">
      <div className="np-bottom-status">
        <span>{toolLabel}</span>
        <span className="np-bottom-dot">·</span>
        <span>{brushSize}px</span>
      </div>
      <div className="np-bottom-actions">
        {onCancel && (
          <WigglyButton className="np-bottom-btn" onClick={onCancel}>
            {t.cancel}
          </WigglyButton>
        )}
        <WigglyButton className="np-bottom-btn np-bottom-btn-primary" onClick={onSave}>
          {t.save}
        </WigglyButton>
      </div>
      <div className="np-resize-handle" aria-hidden="true" />
    </footer>
  )
}
