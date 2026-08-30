import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import ImageCompareSlider from '../components/ImageCompareSlider'
import { useLocale } from '../i18n/LocaleContext'
import { usePageMeta } from '../hooks/usePageMeta'
import '../styles/showcase-compare.css'

export default function GuideMatrixPage() {
  const { matrix, messages: m } = useLocale()
  const g = m.guidePage
  const comparisons = matrix.getMatrixComparisons()
  usePageMeta(matrix.MATRIX_META_TITLE, matrix.MATRIX_META_DESCRIPTION)

  useEffect(() => {
    let canonical = document.querySelector<HTMLLinkElement>('link[rel="canonical"]')
    const prevCanonical = canonical?.href ?? ''
    if (!canonical) {
      canonical = document.createElement('link')
      canonical.rel = 'canonical'
      document.head.appendChild(canonical)
    }
    canonical.href = matrix.MATRIX_CANONICAL

    const scriptId = 'matrix-json-ld'
    let script = document.getElementById(scriptId) as HTMLScriptElement | null
    if (!script) {
      script = document.createElement('script')
      script.id = scriptId
      script.type = 'application/ld+json'
      document.head.appendChild(script)
    }
    script.textContent = JSON.stringify(matrix.buildMatrixJsonLd())

    return () => {
      if (canonical) canonical.href = prevCanonical || 'https://jwprotect.com/'
      script?.remove()
    }
  }, [matrix])

  return (
    <div className="page-guide-matrix">
      <div className="am-container">
        <header className="guide-matrix-hero jp-hero">
          <p className="jp-kicker">{g.matrixKicker}</p>
          <h1 className="jp-page-title">{matrix.MATRIX_INTRO.title}</h1>
          <p className="jp-section-lead">{matrix.MATRIX_INTRO.lead}</p>
          <p className="text-secondary text-sm">
            <time dateTime={matrix.MATRIX_DATE_MODIFIED}>{matrix.MATRIX_INTRO.updated}</time>
          </p>
        </header>

        <section aria-labelledby="matrix-invisible-title">
          <h2 id="matrix-invisible-title" className="am-section-title">
            {matrix.MATRIX_INTRO.tableCaption}
          </h2>
          <div className="guide-matrix-table-wrap">
            <table className="guide-matrix-table">
              <thead>
                <tr>
                  <th scope="col">{g.tableLayer}</th>
                  <th scope="col">{g.tableNormal}</th>
                  <th scope="col">{g.tableAfterAi}</th>
                  <th scope="col">{g.tableVerify}</th>
                </tr>
              </thead>
              <tbody>
                {matrix.MATRIX_TABLE.map(row => (
                  <tr key={row.id}>
                    <th scope="row">{row.layer}</th>
                    <td>{row.normalView}</td>
                    <td>{row.afterAiWash}</td>
                    <td>
                      <span className={`guide-matrix-status guide-matrix-status--${row.verify}`}>
                        {matrix.MATRIX_STATUS_LABELS[row.verify]}
                      </span>
                      <span className="text-sm" style={{ display: 'block', marginTop: 4, opacity: 0.75 }}>
                        {row.verifyLabel}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section aria-labelledby="matrix-compare-title" style={{ marginTop: '2.5rem' }}>
          <h2 id="matrix-compare-title" className="am-section-title">
            {matrix.MATRIX_INTRO.compareCaption}
          </h2>
          <p className="am-section-lead" style={{ marginBottom: '1.5rem' }}>
            {matrix.MATRIX_INTRO.colProtected} · {matrix.MATRIX_INTRO.colAiRestored}
          </p>

          {comparisons.map(pair => (
            <article key={pair.id} className="guide-matrix-row-block">
              <h3 className="am-showcase-item-title">{pair.layerName}</h3>
              {pair.note ? <p className="am-showcase-item-desc">{pair.note}</p> : null}
              <ImageCompareSlider
                beforeSrc={pair.protectedSrc}
                afterSrc={pair.aiRestoredSrc}
                beforeAlt={pair.protectedAlt}
                afterAlt={pair.aiRestoredAlt}
                beforeLabel={matrix.MATRIX_INTRO.colProtected}
                afterLabel={matrix.MATRIX_INTRO.colAiRestored}
                hint={g.compareHint}
              />
            </article>
          ))}
        </section>

        <p className="guide-disclaimer">{matrix.MATRIX_DISCLAIMER}</p>

        <section className="guide-matrix-row-block" aria-labelledby="matrix-faq-title">
          <h2 id="matrix-faq-title" className="am-section-title">
            {g.faqTitle}
          </h2>
          {matrix.MATRIX_FAQ.map(item => (
            <article key={item.q} className="faq-entry">
              <h3 className="faq-question">{item.q}</h3>
              <p className="faq-answer-p">{item.a}</p>
            </article>
          ))}
        </section>

        <footer className="jp-section about-cta">
          <p className="about-cta-title">{matrix.MATRIX_CTA.title}</p>
          <p className="jp-body-text">{matrix.MATRIX_CTA.body}</p>
          <p style={{ marginTop: '1rem' }}>
            {matrix.MATRIX_CTA.links.map((link, idx) => (
              <span key={link.to}>
                {idx > 0 && <span className="faq-related-sep"> · </span>}
                <Link to={link.to}>{link.label}</Link>
              </span>
            ))}
          </p>
        </footer>
      </div>
    </div>
  )
}
