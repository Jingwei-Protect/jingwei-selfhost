import { useLocale } from '../i18n/LocaleContext'

export type MaskRetainReason = 'backToPlace' | 'paramChange'

interface Props {
  open: boolean
  reason: MaskRetainReason
  onKeep: () => void
  onDiscard: () => void
  onCancel?: () => void
  busy?: boolean
}

/** Ask whether to keep erase/blur masks when leaving refine or after render params change. */
export default function ProtectMaskRetainDialog({
  open,
  reason,
  onKeep,
  onDiscard,
  onCancel,
  busy = false,
}: Props) {
  const { messages: m } = useLocale()
  const d = m.protect.maskRetainDialog
  const copy = reason === 'backToPlace' ? d.backToPlace : d.paramChange

  if (!open) return null

  const showCancel = reason === 'backToPlace' && onCancel

  return (
    <div
      className="auth-modal-backdrop"
      onClick={busy || !showCancel ? undefined : onCancel}
      role="presentation"
    >
      <div
        className="auth-modal card protect-unsaved-dialog"
        onClick={e => e.stopPropagation()}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="protect-mask-retain-title"
        aria-describedby="protect-mask-retain-body"
      >
        {showCancel && (
          <button
            type="button"
            className="auth-modal-close"
            onClick={onCancel}
            disabled={busy}
            aria-label={d.cancel}
          >
            ×
          </button>
        )}
        <h2 id="protect-mask-retain-title" style={{ marginBottom: 'var(--space-2)' }}>{copy.title}</h2>
        <p
          id="protect-mask-retain-body"
          className="text-sm text-secondary"
          style={{ lineHeight: 1.7, marginBottom: 'var(--space-5)' }}
        >
          {copy.body}
        </p>
        <div className="protect-unsaved-dialog-actions">
          <button type="button" className="btn btn-primary" onClick={onKeep} disabled={busy}>
            {copy.keep}
          </button>
          <button type="button" className="btn btn-secondary" onClick={onDiscard} disabled={busy}>
            {copy.discard}
          </button>
          {showCancel && (
            <button type="button" className="btn btn-secondary" onClick={onCancel} disabled={busy}>
              {d.cancel}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
