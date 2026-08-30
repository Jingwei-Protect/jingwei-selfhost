import { useEffect, useId, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { LOCALES, LOCALE_LABELS, type Locale } from './types'
import { useLocale } from './LocaleContext'

export default function LanguageSwitcher() {
  const { locale, setLocale, messages } = useLocale()
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)
  const location = useLocation()
  const listId = useId()

  useEffect(() => {
    setOpen(false)
  }, [location.pathname])

  useEffect(() => {
    if (!open) return
    const onPointerDown = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false)
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('mousedown', onPointerDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [open])

  const pick = (code: Locale) => {
    setLocale(code)
    setOpen(false)
  }

  return (
    <div
      ref={rootRef}
      className={`lang-switcher${open ? ' is-open' : ''}`}
    >
      <button
        type="button"
        className="lang-switcher-trigger"
        aria-expanded={open}
        aria-haspopup="listbox"
        aria-controls={listId}
        onClick={() => setOpen(v => !v)}
      >
        <span className="lang-switcher-trigger-label">{LOCALE_LABELS[locale]}</span>
        <span className="lang-switcher-chevron" aria-hidden="true" />
      </button>
      {open && (
        <ul
          id={listId}
          className="lang-switcher-menu"
          role="listbox"
          aria-label={messages.common.lang.label}
        >
          {LOCALES.map(code => (
            <li key={code} role="presentation">
              <button
                type="button"
                role="option"
                aria-selected={locale === code}
                className={`lang-switcher-option${locale === code ? ' is-active' : ''}`}
                onClick={() => pick(code)}
              >
                {LOCALE_LABELS[code]}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
