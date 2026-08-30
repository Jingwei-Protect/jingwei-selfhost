import { Link } from 'react-router-dom'
import { CONTACT_EMAIL } from '../lib/site'
import { useLocale } from '../i18n/LocaleContext'

export default function TermsPage() {
  const { legal } = useLocale()
  return (
    <div className="page-section">
      <div className="container" style={{ maxWidth: 760 }}>
        <div className="section-header" style={{ marginBottom: 32 }}>
          <h1 style={{ fontSize: 'var(--text-2xl)', lineHeight: 1.35 }}>{legal.LEGAL_TERMS_TITLE}</h1>
          <p className="text-secondary" style={{ marginTop: 8 }}>
            <time dateTime={legal.LEGAL_TERMS_DATE_MODIFIED}>{legal.LEGAL_TERMS_UPDATED}</time>
          </p>
          <p className="text-secondary" style={{ marginTop: 8 }}>
            <Link to="/privacy">{legal.LEGAL_TERMS_PRIVACY_LINK_LABEL}</Link>
            {' · '}
            <Link to="/protocol">{legal.LEGAL_TERMS_PROTOCOL_LINK_LABEL}</Link>
          </p>
        </div>

        <section style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)', lineHeight: 1.85 }}>
          {legal.LEGAL_TERMS_INTRO.map(p => (
            <p key={p} className="text-secondary">{p}</p>
          ))}

          {legal.LEGAL_TERMS_SECTIONS.map(section => (
            <div key={section.title} className="card" style={{ padding: 'var(--space-6)' }}>
              <h2 style={{ fontSize: 'var(--text-lg)', marginBottom: 'var(--space-3)' }}>{section.title}</h2>
              {section.intro && (
                <p className="text-secondary" style={{ marginBottom: 'var(--space-3)' }}>{section.intro}</p>
              )}
              {section.bullets && (
                <ul className="text-secondary" style={{ paddingLeft: 'var(--space-5)' }}>
                  {section.bullets.map(b => (
                    <li key={b} style={{ marginBottom: 'var(--space-2)' }}>{b}</li>
                  ))}
                </ul>
              )}
            </div>
          ))}

          <div className="card" style={{ padding: 'var(--space-6)', background: 'var(--color-bg-secondary)' }}>
            <h2 style={{ fontSize: 'var(--text-lg)', marginBottom: 'var(--space-3)' }}>{legal.LEGAL_TERMS_FINAL_CONFIRMATION_TITLE}</h2>
            <p className="text-secondary">{legal.LEGAL_TERMS_CONFIRMATION}</p>
          </div>

          <p className="text-secondary text-sm">
            {legal.LEGAL_TERMS_CONTACT_PREFIX}
            <a href={`mailto:${CONTACT_EMAIL}`}><code>{CONTACT_EMAIL}</code></a>
          </p>
        </section>
      </div>
    </div>
  )
}
