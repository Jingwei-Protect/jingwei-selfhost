import { useState } from 'react'

interface Option {
  label: string
  value: string
  /** Shown in the full-width panel under the row when the “?” is open. */
  hint?: string
}

interface Props {
  options: Option[]
  value: string
  onChange: (v: string) => void
}

export function HelpTip({ text }: { text: string }) {
  const [open, setOpen] = useState(false)
  return (
    <span className="field-help">
      <button
        type="button"
        className="mode-help-q"
        aria-label={text}
        aria-expanded={open}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onClick={e => {
          e.preventDefault()
          setOpen(v => !v)
        }}
      >
        ?
      </button>
      {open ? (
        <span className="mode-help-panel" role="tooltip">
          {text}
        </span>
      ) : null}
    </span>
  )
}

export default function RadioPills({ options, value, onChange }: Props) {
  const [openHint, setOpenHint] = useState<string | null>(null)
  const hasHints = options.some(o => Boolean(o.hint))

  return (
    <div
      className={hasHints ? 'form-radio-group-block' : undefined}
      onMouseLeave={hasHints ? () => setOpenHint(null) : undefined}
    >
      <div className="form-radio-group">
        {options.map(o => (
          <span key={o.value} className="radio-pill-wrap">
            <button
              type="button"
              className={`radio-pill${value === o.value ? ' active' : ''}`}
              onClick={() => onChange(o.value)}
            >
              {o.label}
            </button>
            {o.hint ? (
              <button
                type="button"
                className="mode-help-q"
                aria-label={o.hint}
                aria-expanded={openHint === o.value}
                onMouseEnter={() => setOpenHint(o.value)}
                onFocus={() => setOpenHint(o.value)}
                onClick={e => {
                  e.preventDefault()
                  setOpenHint(prev => (prev === o.value ? null : o.value))
                }}
              >
                ?
              </button>
            ) : null}
          </span>
        ))}
      </div>
      {hasHints && openHint ? (
        <div className="mode-help-panel" role="tooltip">
          {options.find(o => o.value === openHint)?.hint}
        </div>
      ) : null}
    </div>
  )
}
