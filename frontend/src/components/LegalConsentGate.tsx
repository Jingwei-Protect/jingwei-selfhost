import { createContext, useContext, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useLegalConsent } from '../hooks/useLegalConsent'
import { useLocale } from '../i18n/LocaleContext'

const LegalAcceptedContext = createContext(false)

export function useLegalAccepted(): boolean {
  return useContext(LegalAcceptedContext)
}

interface Props {
  children: ReactNode
}

/** 上传类工具共用：未同意前弹窗拦截 + 同会话内只确认一次 */
export default function LegalConsentGate({ children }: Props) {
  const { messages: m, legal } = useLocale()
  const t = m.components.legalConsentGate
  const { accepted, checked, setChecked, accept } = useLegalConsent()

  return (
    <>
      {!accepted && (
        <div
          className="pixel-sea-welcome pixel-sea-welcome--blocking protect-terms-overlay"
          role="dialog"
          aria-modal="true"
          aria-labelledby="legal-consent-title"
        >
          <div className="pixel-sea-welcome-card card">
            <h2 id="legal-consent-title" style={{ marginBottom: 'var(--space-3)' }}>
              {t.title}
            </h2>
            <p className="text-secondary text-sm" style={{ marginBottom: 'var(--space-4)', lineHeight: 1.75 }}>
              {t.summaryLead}
              {' '}<Link to="/terms" target="_blank" rel="noopener noreferrer">{legal.LEGAL_TERMS_LINK_LABEL}</Link>。
            </p>
            <ul
              className="text-sm"
              style={{
                paddingLeft: 0,
                listStyle: 'none',
                marginBottom: 'var(--space-4)',
                lineHeight: 1.75,
              }}
            >
              {legal.LEGAL_CONSENT_SUMMARY.map(item => (
                <li key={item.title} style={{ marginBottom: 'var(--space-3)' }}>
                  <strong>{item.title}:</strong>
                  <span className="text-secondary">
                    {item.body}
                    {(item.title === '隐私' || item.title === 'Privacy') && (
                      <>
                        {' '}
                        <Link to="/privacy" target="_blank" rel="noopener noreferrer">{legal.LEGAL_PRIVACY_LINK_LABEL}</Link>
                      </>
                    )}
                  </span>
                </li>
              ))}
            </ul>
            <label
              className="form-checkbox"
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: 'var(--space-2)',
                marginBottom: 'var(--space-4)',
                textAlign: 'left',
                lineHeight: 1.65,
                fontSize: 'var(--text-sm)',
              }}
            >
              <input
                type="checkbox"
                checked={checked}
                onChange={e => setChecked(e.target.checked)}
                style={{ marginTop: 3 }}
              />
              <span>
                {t.readAndAgree}
              </span>
            </label>
            <div
              style={{
                display: 'flex',
                gap: 'var(--space-3)',
                justifyContent: 'center',
                flexWrap: 'wrap',
                marginBottom: 'var(--space-3)',
              }}
            >
              <Link to="/terms" target="_blank" rel="noopener noreferrer" className="btn btn-secondary">
                {t.readFull}
              </Link>
              <button
                type="button"
                className="btn btn-primary btn-lg"
                disabled={!checked}
                onClick={accept}
              >
                {t.accept}
              </button>
            </div>
          </div>
        </div>
      )}

      <LegalAcceptedContext.Provider value={accepted}>
        <div className={accepted ? undefined : 'protect-page-tool--locked'}>
          {children}
        </div>
      </LegalAcceptedContext.Provider>
    </>
  )
}
