import { useLocale } from '../i18n/LocaleContext'

interface Props {
  open: boolean
  onSaveAndProtect: () => void
  onDiscardAndProtect: () => void
  onCancel: () => void
  busy?: boolean
}

/** Three-way choice when preview-layer edits were not saved before protect. */
export default function ProtectUnsavedDialog({
  open,
  onSaveAndProtect,
  onDiscardAndProtect,
  onCancel,
  busy = false,
}: Props) {
  const { messages: m } = useLocale()
  const d = m.protect.unsavedPreviewDialog

  if (!open) return null

  return (
    <div className="auth-modal-backdrop" onClick={busy ? undefined : onCancel} role="presentation">
      <div
        className="auth-modal card protect-unsaved-dialog"
        onClick={e => e.stopPropagation()}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="protect-unsaved-title"
        aria-describedby="protect-unsaved-body"
      >
        <button
          type="button"
          className="auth-modal-close"
          onClick={onCancel}
          disabled={busy}
          aria-label={d.cancel}
        >
          ×
        </button>
        <h2 id="protect-unsaved-title" style={{ marginBottom: 'var(--space-2)' }}>{d.title}</h2>
        <p id="protect-unsaved-body" className="text-sm text-secondary" style={{ lineHeight: 1.7, marginBottom: 'var(--space-5)' }}>
          {d.body}
        </p>
        <div className="protect-unsaved-dialog-actions">
          <button type="button" className="btn btn-primary" onClick={onSaveAndProtect} disabled={busy}>
            {busy ? d.saving : d.saveAndProtect}
          </button>
          <button type="button" className="btn btn-secondary" onClick={onDiscardAndProtect} disabled={busy}>
            {d.discardAndProtect}
          </button>
          <button type="button" className="btn btn-secondary" onClick={onCancel} disabled={busy}>
            {d.cancel}
          </button>
        </div>
      </div>
    </div>
  )
}
