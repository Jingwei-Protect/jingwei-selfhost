import { Link } from 'react-router-dom'
import { useLocale } from '../i18n/LocaleContext'

function renderBody(body: unknown) {
  if (!body || typeof body !== 'object') return null
  const value = body as Record<string, string>
  if (value.type === 'termsLink') {
    return (
      <p className="text-secondary">
        {value.before}{' '}
        <Link to={value.linkTo}>{value.linkLabel}</Link>
        {value.after}
      </p>
    )
  }
  if (value.type === 'contact') {
    return (
      <p className="text-secondary">
        {value.before}{' '}
        <a href={`mailto:${value.email}`}><code>{value.email}</code></a>
      </p>
    )
  }
  return null
}

export default function PrivacyPage() {
  const { privacy } = useLocale()
  return (
    <div className="page-section">
      <div className="container" style={{ maxWidth: 760 }}>
        <div className="section-header" style={{ marginBottom: 32 }}>
          <h1>{privacy.PRIVACY_TITLE}</h1>
          <p className="text-secondary" style={{ marginTop: 8 }}>
            <time dateTime={privacy.PRIVACY_DATE_MODIFIED}>{privacy.PRIVACY_UPDATED}</time>
          </p>
        </div>

        <section style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)', lineHeight: 1.8 }}>
          {privacy.PRIVACY_SECTIONS.map(section => (
            <div key={section.id} className={section.id === 'relation' || section.id === 'summary' ? 'card' : undefined}>
              <h3>{section.title}</h3>
              {renderBody(section.body)}
              {section.paragraphs?.map(p => (
                <p key={p} className="text-secondary">{p}</p>
              ))}
              {section.bullets && (
                <ul className="text-secondary" style={{ paddingLeft: 24, marginTop: 8 }}>
                  {section.bullets.map(b => (<li key={b}>{b}</li>))}
                </ul>
              )}
            </div>
          ))}
        </section>
      </div>
    </div>
  )
}
