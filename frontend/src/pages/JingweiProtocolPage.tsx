import { useEffect } from 'react'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { usePageMeta } from '../hooks/usePageMeta'
import { SITE_NAME, SITE_URL } from '../lib/site'
import { localeUsesLatinJwFields, localeSchemaLanguage } from '../i18n/types'
import { useLocale } from '../i18n/LocaleContext'
import jingweiBird from '../assets/jingwei-bird.png'
import { JwIcon, JwBadgeRow, type JwIconType } from '../components/jw/JwIcon'
const COMBO_TYPES = [
  ['JW', 'OC', 'NO-TR', 'NO-ED'],
  ['JW', 'AI', 'NO-TR'],
  ['JW', 'OC'],
  ['JW', 'AI'],
] as const

function SectionHead({
  kicker,
  title,
  lead,
  as = 'h2',
}: {
  kicker: string
  title: string
  lead?: string
  as?: 'h1' | 'h2'
}) {
  const TitleTag = as
  return (
    <header className="jp-section-head">
      <p className="jp-kicker">{kicker}</p>
      <TitleTag className={as === 'h1' ? 'jp-page-title' : 'jp-section-title'}>{title}</TitleTag>
      {lead ? <p className="jp-section-lead">{lead}</p> : null}
    </header>
  )
}

function SubsectionHead({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="jp-subsection-head">
      <h3 className="jp-subsection-title">{title}</h3>
      {hint ? <p className="jp-subsection-hint">{hint}</p> : null}
    </div>
  )
}

function FlagRow({
  icon,
  meta,
  title,
  desc,
}: {
  icon: JwIconType
  meta: string
  title: string
  desc: string
}) {
  return (
    <div className="jw-flag-item">
      <JwIcon type={icon} size={64} />
      <div className="jw-flag-copy">
        <p className="jp-card-meta">{meta}</p>
        <h4 className="jp-card-title">{title}</h4>
        <p className="jp-card-desc">{desc}</p>
      </div>
    </div>
  )
}

function SplitSection({
  kicker,
  title,
  lead,
  children,
}: {
  kicker: string
  title: string
  lead?: string
  children: ReactNode
}) {
  return (
    <section className="jp-section jp-split-section">
      <SectionHead kicker={kicker} title={title} lead={lead} />
      <div className="jp-split-body">{children}</div>
    </section>
  )
}

function VisualGuideSection() {
  const { messages: m, jw, locale } = useLocale()
  const v = m.protocol.visualGuide
  const useLatinJw = localeUsesLatinJwFields(locale)
  return (
    <section className="jp-section jp-split-section jp-visual-guide">
      <SectionHead
        kicker={v.kicker}
        title={m.protocol.sectionTitles.symbolSystem}
        lead={v.lead}
      />
      <div className="jp-visual-guide-body">
        <div className="jp-visual-block">
          <SubsectionHead title={v.symbolSystem} hint={v.symbolHint} />
          <div className="jw-flag-grid">
            <FlagRow
              icon="JW"
              meta={v.jwMeta}
              title={v.jwTitle}
              desc={v.jwDesc}
            />
          </div>

          <SubsectionHead title={v.creationType} hint={v.creationHint} />
          <div className="jw-flag-grid">
            {jw.JW_CREATION_OPTIONS.map(opt => (
              <FlagRow
                key={opt.id}
                icon={opt.id as 'OC' | 'AI'}
                meta={opt.label}
                title={useLatinJw ? opt.label : opt.labelZh}
                desc={useLatinJw ? opt.desc : opt.descZh}
              />
            ))}
          </div>

          <SubsectionHead title={v.restrictions} hint={v.restrictionsHint} />
          <div className="jw-flag-grid">
            {jw.JW_RESTRICTION_FLAGS.map(flag => (
              <FlagRow
                key={flag.id}
                icon={flag.id as 'NO-TR' | 'NO-ED'}
                meta={flag.label}
                title={useLatinJw ? flag.label : flag.labelZh}
                desc={useLatinJw ? flag.desc : flag.descZh}
              />
            ))}
          </div>
        </div>

        <div className="jp-visual-block">
          <SubsectionHead title={v.comboTitle} hint={v.flexibleCombo} />
          <p className="jp-visual-block-lead">
            {v.comboLead}
          </p>
          <div className="jp-combo-list">
            {COMBO_TYPES.map((types, i) => (
              <div key={v.comboExamples[i]} className="jw-combo-row">
                <span className="jw-icon-row">
                  <JwBadgeRow types={[...types]} size={28} gap={4} />
                </span>
                <span className="jp-combo-label">{v.comboExamples[i]}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="jp-visual-block">
          <SubsectionHead title={v.badgeTitle} hint={v.badgeHint} />
          <p className="jp-visual-block-lead">
            {v.badgeLead}
          </p>
          <div className="jp-badge-preview">
            <div className="jw-badge-mock">
              <div className="jw-badge-mock-image" aria-hidden="true" />
              <div className="jw-badge-mock-sticker">
                <img src={jingweiBird} alt="" className="jw-badge-mock-logo" aria-hidden="true" />
                <span className="jw-icon-row">
                  <JwBadgeRow types={['JW', 'OC', 'NO-TR', 'NO-ED']} size={24} gap={3} />
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

export default function JingweiProtocolPage() {
  const { messages: m, jw, locale } = useLocale()
  const useLatinJw = localeUsesLatinJwFields(locale)
  usePageMeta(`${m.protocol.pageTitle} · ${SITE_NAME}`, jw.JW_PROTOCOL_META_DESCRIPTION)

  useEffect(() => {
    let canonical = document.querySelector<HTMLLinkElement>('link[rel="canonical"]')
    const prevCanonical = canonical?.href ?? ''
    if (!canonical) {
      canonical = document.createElement('link')
      canonical.rel = 'canonical'
      document.head.appendChild(canonical)
    }
    canonical.href = jw.JW_PROTOCOL_CANONICAL

    const scriptId = 'protocol-json-ld'
    let script = document.getElementById(scriptId) as HTMLScriptElement | null
    if (!script) {
      script = document.createElement('script')
      script.id = scriptId
      script.type = 'application/ld+json'
      document.head.appendChild(script)
    }
    script.textContent = JSON.stringify({
      '@context': 'https://schema.org',
      '@type': 'WebPage',
      name: m.protocol.pageTitle,
      description: jw.JW_PROTOCOL_META_DESCRIPTION,
      url: jw.JW_PROTOCOL_CANONICAL,
      inLanguage: localeSchemaLanguage(locale),
      dateModified: jw.JW_PROTOCOL_DATE_MODIFIED,
      isPartOf: { '@type': 'WebSite', name: SITE_NAME, url: SITE_URL },
    })

    return () => {
      if (canonical) canonical.href = prevCanonical || 'https://jwprotect.com/'
      script?.remove()
    }
  }, [jw, m.protocol.pageTitle, locale])

  return (
    <div className="page-protocol">
      <article className="jp-doc">
        <header className="jp-section jp-hero">
          <SectionHead
            as="h1"
            kicker="Jingwei Declaration"
            title={m.protocol.pageTitle}
            lead={m.protocol.heroLead}
          />
        </header>

        <SplitSection
          kicker={jw.JW_CC_SYMBOL_HISTORY.kicker}
          title={jw.JW_CC_SYMBOL_HISTORY.title}
          lead={jw.JW_CC_SYMBOL_HISTORY.lead}
        >
          {jw.JW_CC_SYMBOL_HISTORY.paragraphs.map((para, i) => (
            <p key={i} className="jp-body-text">{para}</p>
          ))}
        </SplitSection>

        <SplitSection kicker="The Story" title={m.protocol.sectionTitles.story}>
          {useLatinJw
            ? jw.JW_STORY.map((text, i) => (
              <p key={i} className={i === 0 ? 'jp-body-lead' : 'jp-body-text'}>{text}</p>
            ))
            : jw.JW_STORY_ZH.map((para, i) => (
              <p key={i} className={para.lead ? 'jp-body-lead' : 'jp-body-text'}>{para.text}</p>
            ))}
        </SplitSection>

        <SplitSection kicker="Why It Matters" title={jw.JW_CORE_BELIEF.title}>
          {jw.JW_CORE_BELIEF.paragraphs.map((para, i) => (
            <p key={i} className="jp-body-text">{para}</p>
          ))}
        </SplitSection>

        <SplitSection
          kicker={m.protocol.whatJwDoes.kicker}
          title={m.protocol.sectionTitles.whatJwDoes}
          lead={m.protocol.whatJwDoes.lead}
        >
          {m.protocol.whatJwDoes.paragraphs.map((para, i) => (
            <p key={i} className="jp-body-text">{para}</p>
          ))}
          <p className="jp-body-note">
            {m.protocol.whatJwDoes.note}
          </p>
        </SplitSection>

        <VisualGuideSection />

        <SplitSection kicker={m.protocol.c2paSection.kicker} title={m.protocol.sectionTitles.c2pa}>
          {m.protocol.c2paSection.paragraphs.map((para, i) => (
            <p key={i} className="jp-body-text">{para}</p>
          ))}
          <ul className="jp-bullet-list">
            {m.protocol.c2paSection.bullets.map(line => (
              <li key={line}>{line}</li>
            ))}
          </ul>
          <p className="jp-body-note">
            {m.protocol.c2paSection.note}
          </p>
        </SplitSection>

        <SplitSection kicker="Our Promise" title={jw.JW_TOOL_PROMISE.title}>
          {jw.JW_TOOL_PROMISE.paragraphs.map((para, i) => (
            <p key={i} className="jp-body-text">{para}</p>
          ))}
        </SplitSection>

        <footer className="jp-section jp-actions">
          <Link to="/protect" className="btn btn-primary">{m.protocol.actions.protectNow}</Link>
          <Link to="/verify" className="btn btn-secondary">{m.protocol.actions.verifyNow}</Link>
          <p className="jp-body-note" style={{ marginTop: 'var(--space-5)', marginBottom: 0, width: '100%' }}>
            {m.protocol.actions.faqLead} <Link to="/faq">{m.common.faqLink}</Link>
            {' · '}
            <Link to="/about">{m.common.footer.about}</Link>
          </p>
        </footer>
      </article>
    </div>
  )
}
