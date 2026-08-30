import { useState, useCallback, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import ImageUpload from '../components/ImageUpload'
import {
} from '../content/jingweiProtocol'
import { JwIcon, type JwIconType } from '../components/jw/JwIcon'
import JingweiMiniIcon from '../components/JingweiMiniIcon'
import LegalConsentGate, { useLegalAccepted } from '../components/LegalConsentGate'
import FeedbackHelpLink from '../components/FeedbackHelpLink'
import { usePageSeo } from '../hooks/usePageSeo'
import { jwRestrictionLabel } from '../i18n/contentBridge'
import { useLocale } from '../i18n/LocaleContext'
import { localeListSeparator } from '../i18n/types'
import { SITE_NAME, VERIFY_PAGE_CANONICAL } from '../lib/site'

const JW_ICON_TYPES = new Set<string>(['JW', 'OC', 'AI', 'NO-TR', 'NO-ED'])

interface RecoveryMeta {
  scale: number
  offset?: [number, number] | null
  attempts_used?: number
}

interface DwtResult {
  found: boolean
  payload?: string
  timestamp?: string
  confidence?: number
  error?: string
  recovered?: boolean
  recovery?: RecoveryMeta | null
}

interface LsbResult {
  found: boolean
  text?: string
  error?: string
}

interface MetaResult {
  found: boolean
  exif?: Record<string, string>
  iptc?: Record<string, string>
  error?: string
}

interface C2paResult {
  found: boolean
  available?: boolean
  claim_generator?: string
  software_agent?: string
  digital_source_type?: string
  title?: string
  author?: string
  actions?: string[]
  training_policy?: string
  signature_valid?: boolean
  validation_status?: unknown
  hint?: string
  error?: string
}

interface JwResult {
  found: boolean
  confidence?: number
  creation?: string
  creation_label?: string
  restrictions?: string[]
  artist?: string
  artist_hash?: string
  badge_text?: string
  protected_at?: string | null
  hint?: string
  error?: string
  recovered?: boolean
  recovery?: RecoveryMeta | null
}

interface AnchorResult {
  found: boolean
  artist_code?: string
  artist_name?: string | null
  year?: number
  month?: number
  year_month?: string
  signed_date?: string
  confidence?: number
  artist_matches?: boolean | null
  claim_checked?: boolean
  claim_code?: string | null
  error?: string
}

type ClaimVerdict = 'idle' | 'match' | 'mismatch'

/** Parse signatures like ``jw260606`` → tag + YYMMDD (screenshot-friendly convention). */
function parseSignatureDateSuffix(raw: string): { tag: string; year: number; month: number; day: number } | null {
  const m = raw.trim().match(/^(.+?)(\d{6})$/)
  if (!m) return null
  const yy = parseInt(m[2].slice(0, 2), 10)
  const mm = parseInt(m[2].slice(2, 4), 10)
  const dd = parseInt(m[2].slice(4, 6), 10)
  if (!Number.isFinite(yy) || mm < 1 || mm > 12 || dd < 1 || dd > 31) return null
  return { tag: m[1], year: 2000 + yy, month: mm, day: dd }
}

function formatAnchorUnlockLabel(anchor: AnchorResult): string {
  const raw = (anchor.artist_name || '').trim()
  if (!raw) return ''
  // Prefer exact embed date (with day), recovered from JW / metadata / DWT / LSB.
  // The user signs normally — no manual date in the handle — yet the result reads 年月日.
  if (anchor.signed_date) {
    const [y, m, d] = anchor.signed_date.split('-').map((n) => parseInt(n, 10))
    if (Number.isFinite(y) && Number.isFinite(m) && Number.isFinite(d)) {
      return `${raw}  ${y}  ${m}  ${d}`
    }
  }
  // Back-compat: a signature that itself encodes tag+YYMMDD (e.g. ``jw260606``).
  const parsed = parseSignatureDateSuffix(raw)
  if (parsed) {
    return `${parsed.tag}  ${parsed.year}  ${parsed.month}  ${parsed.day}`
  }
  // Screenshot fallback: the anchor alone only preserves year-month.
  const y = anchor.year ?? 0
  const m = anchor.month ?? 0
  return `${raw}  ${y}  ${m}`
}

export default function VerifyPage() {
  return (
    <LegalConsentGate>
      <VerifyPageInner />
    </LegalConsentGate>
  )
}

function VerifyPageInner() {
  const { locale, messages: m, jw: jwBundle } = useLocale()
  const t = m.verify
  const { JW_VERIFY_LIMITS, JW_CORE_BELIEF_SUMMARY, JW_DWT_RELATION } = jwBundle
  usePageSeo({
    title: `${t.pageTitle} · ${SITE_NAME}`,
    description: t.metaDescription,
    canonical: VERIFY_PAGE_CANONICAL,
  })
  const accepted = useLegalAccepted()
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [dwt, setDwt] = useState<DwtResult | null>(null)
  const [lsb, setLsb] = useState<LsbResult | null>(null)
  const [meta, setMeta] = useState<MetaResult | null>(null)
  const [jw, setJw] = useState<JwResult | null>(null)
  const [c2pa, setC2pa] = useState<C2paResult | null>(null)
  const [anchor, setAnchor] = useState<AnchorResult | null>(null)
  const [claimName, setClaimName] = useState('')
  const [claimVerdict, setClaimVerdict] = useState<ClaimVerdict>('idle')
  const abortRef = useRef<AbortController | null>(null)

  const handleFile = useCallback((f: File) => {
    if (!accepted) return
    setFile(f)
    setPreview(URL.createObjectURL(f))
    setDwt(null)
    setLsb(null)
    setMeta(null)
    setJw(null)
    setC2pa(null)
    setAnchor(null)
    setClaimName('')
    setClaimVerdict('idle')
  }, [accepted])

  const clearFile = useCallback(() => {
    setFile(null)
    setPreview(null)
    setDwt(null)
    setLsb(null)
    setMeta(null)
    setJw(null)
    setC2pa(null)
    setAnchor(null)
    setClaimName('')
    setClaimVerdict('idle')
  }, [])

  const runVerify = useCallback(async (target: File, extraName?: string) => {
    abortRef.current?.abort()
    const ctrl = new AbortController()
    abortRef.current = ctrl

    setLoading(true)
    try {
      const fd = new FormData()
      fd.append('image', target)
      // The author types their own name to translate a screenshot's artist code
      // back to a readable name. Sent transiently for matching only — never
      // stored anywhere (not in the browser, not on the server).
      if (extraName && extraName.trim()) fd.append('claim_artists', extraName.trim())
      const res = await fetch('/api/verify', { method: 'POST', body: fd, signal: ctrl.signal })
      const data = await res.json()
      setDwt(data.dwt)
      setLsb(data.lsb)
      setMeta(data.metadata)
      setJw(data.jw)
      setC2pa(data.c2pa)
      setAnchor(data.anchor)
      if (extraName?.trim()) {
        const a = data.anchor
        if (a?.artist_name || a?.artist_matches === true) setClaimVerdict('match')
        else setClaimVerdict('mismatch')
      }
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === 'AbortError') return
      setDwt({ found: false, error: t.errors.network })
    } finally {
      setLoading(false)
    }
  }, [t.errors.network])

  useEffect(() => {
    if (file && accepted) runVerify(file)
    return () => abortRef.current?.abort()
  }, [file, accepted, runVerify])

  const hasResults = dwt || lsb || meta || jw || c2pa || anchor

  const p = t.panels
  const foundLayers: string[] = []
  if (c2pa?.found) foundLayers.push(p.c2pa)
  if (jw?.found) foundLayers.push(t.layers.jwShort)
  if (anchor?.found) foundLayers.push(p.anchor)
  if (dwt?.found) foundLayers.push(p.dwt)
  if (lsb?.found) foundLayers.push(t.layers.lsbShort)
  if (meta?.found) foundLayers.push(p.metadata)

  const notFoundItems: string[] = []
  if (c2pa && !c2pa.found && c2pa.available !== false) notFoundItems.push(p.c2pa)
  if (jw && !jw.found) notFoundItems.push(t.layers.jwShort)
  if (dwt && !dwt.found && !jw?.found) notFoundItems.push(p.dwt)
  if (lsb && !lsb.found) notFoundItems.push(t.layers.lsbShort)
  if (meta && !meta.found) notFoundItems.push(p.metadata)

  return (
    <div className="page-section">
      <div className="container">
        <div className="section-header" style={{ textAlign: 'center', marginBottom: 32 }}>
          <h1>{t.pageTitle}</h1>
          <p style={{ marginTop: 8 }}>{t.pageLead}</p>
        </div>

        <div className="jw-process-steps" aria-label={t.processAriaLabel}>
          <div className="jw-process-step">
            <JingweiMiniIcon type="image" className="jw-process-icon" />
            <strong>{t.processSteps.upload}</strong>
            <span>{t.processSteps.uploadDesc}</span>
          </div>
          <div className="jw-process-step">
            <JingweiMiniIcon type="search" className="jw-process-icon" />
            <strong>{t.processSteps.read}</strong>
            <span>{t.processSteps.readDesc}</span>
          </div>
          <div className="jw-process-step">
            <JingweiMiniIcon type="pebble" className="jw-process-icon" />
            <strong>{t.processSteps.evidence}</strong>
            <span>{t.processSteps.evidenceDesc}</span>
          </div>
        </div>

        <div className="two-col">
          {/* LEFT */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
            <div>
              <h3 style={{ marginBottom: 'var(--space-4)' }}>{t.uploadLabel}</h3>
              <ImageUpload onFile={handleFile} preview={preview} onClear={clearFile} height={320} />
            </div>

            {file && (
              <button
                className="btn btn-secondary"
                style={{ width: '100%' }}
                onClick={() => { setClaimVerdict('idle'); setClaimName(''); runVerify(file) }}
                disabled={loading}
              >
                {loading ? <><span className="spinner" /> {t.checking}</> : t.recheck}
              </button>
            )}

            <div className="card" style={{ background: 'var(--color-bg-secondary)', border: 'none' }}>
              <p className="text-sm text-secondary" style={{ lineHeight: 1.7 }}>
                <strong>{t.hints.supportTypesTitle}：</strong><br />
                · {t.typesCard.c2pa}<br />
                · {t.typesCard.jw}<br />
                · {t.typesCard.anchor}<br />
                · {t.typesCard.dwtPrefix}{JW_DWT_RELATION.verifyStandaloneDwtHint}<br />
                · {t.typesCard.lsb}<br />
                · {t.typesCard.metadata}
              </p>
            </div>
          </div>

          {/* RIGHT */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
            <h3>{t.verifyResults}</h3>

            {loading && (
              <div className="card" style={{ textAlign: 'center', padding: 'var(--space-8)', color: 'var(--color-text-secondary)' }}>
                <span className="spinner" style={{ marginRight: 8 }} />
                {t.checkingAll}
              </div>
            )}

            {!hasResults && !loading && (
              <div className="card" style={{ textAlign: 'center', color: 'var(--color-text-tertiary)', padding: 'var(--space-16)' }}>
                {t.waitingUpload}
              </div>
            )}

            {hasResults && !loading && (
              <div className={`result-card fade-in ${foundLayers.length > 0 ? 'found' : 'not-found'}`}>
                {foundLayers.length > 0 ? (
                  <>
                    <h4 style={{ marginBottom: 8 }}>{t.found}</h4>
                    <p>{t.labels.layersPrefix}{foundLayers.join(localeListSeparator(locale))}</p>
                    {jw?.found && jw.artist && <p>{t.labels.creator}<code>{jw.artist}</code></p>}
                    {jw?.found && jw.creation_label && <p>{t.labels.creationType}<code>{jw.creation_label}</code></p>}
                    {jw?.found && jw.protected_at && <p>{t.labels.protectedAt}<code>{jw.protected_at}</code></p>}
                  </>
                ) : (
                  <>
                    <h4 style={{ marginBottom: 8 }}>{t.notFound}</h4>
                    <p className="text-sm text-secondary">{t.hints.notFoundHint}</p>
                  </>
                )}
              </div>
            )}

            {/* Found layers — details */}
            {/* C2PA — higher trust when present */}
            {c2pa?.found && (
              <details className="result-details fade-in" open>
                <summary className="result-details-summary found">{p.c2pa}</summary>
                <div className="result-details-body">
                  {c2pa.claim_generator && <p>{t.c2pa.claimGenerator}<code>{c2pa.claim_generator}</code></p>}
                  {c2pa.author && <p>{t.c2pa.author}<code>{c2pa.author}</code></p>}
                  {c2pa.digital_source_type && (
                    <p>{t.c2pa.digitalSource}<code>{c2pa.digital_source_type}</code></p>
                  )}
                  {c2pa.actions && c2pa.actions.length > 0 && (
                    <p>{t.c2pa.actions}<code>{c2pa.actions.join(', ')}</code></p>
                  )}
                  {c2pa.training_policy && (
                    <p>{t.c2pa.trainingPolicy}<code>{c2pa.training_policy}</code></p>
                  )}
                  {c2pa.signature_valid != null && (
                    <p>{t.c2pa.signatureValid}<code>{c2pa.signature_valid ? t.labels.yes : t.labels.no}</code></p>
                  )}
                  <p className="text-sm text-secondary">{t.c2pa.hint}</p>
                </div>
              </details>
            )}

            {c2pa && !c2pa.found && c2pa.available === false && (
              <p className="text-sm text-secondary">{c2pa.hint}</p>
            )}

            {jw?.found && (
              <details className="result-details fade-in" open>
                <summary className="result-details-summary found">{p.jw}</summary>
                <div className="result-details-body">
                  <p style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                    <span>{t.labels.creationType}</span>
                    {jw.creation && JW_ICON_TYPES.has(jw.creation) && (
                      <JwIcon type={jw.creation as JwIconType} size={28} />
                    )}
                    <code>{jw.creation_label}</code>
                  </p>
                  {jw.artist && <p>{t.labels.creator}<code>{jw.artist}</code></p>}
                  {jw.protected_at && <p>{t.labels.protectedAt}<code>{jw.protected_at}</code></p>}
                  {jw.restrictions && jw.restrictions.length > 0 && (
                    <div style={{ marginTop: 4 }}>
                      <span>{t.labels.restrictions}</span>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 6 }}>
                        {jw.restrictions.map(r => (
                          <span
                            key={r}
                            title={jwRestrictionLabel(locale, r)}
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: 6,
                              padding: '4px 8px',
                              background: 'var(--color-bg-secondary)',
                              borderRadius: 6,
                              fontFamily: 'var(--font-mono, monospace)',
                              fontSize: 12,
                            }}
                          >
                            {JW_ICON_TYPES.has(r) && (
                              <JwIcon type={r as JwIconType} size={22} />
                            )}
                            <strong>{r}</strong>
                            <span style={{ opacity: 0.7, fontWeight: 400 }}>· {jwRestrictionLabel(locale, r)}</span>
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  <p>{t.labels.badgeText}<code>{jw.badge_text}</code></p>
                  <p>{t.labels.confidence}<code>{((jw.confidence || 0) * 100).toFixed(1)}%</code></p>
                  {jw.recovered && jw.recovery && (
                    <p className="text-sm recovery-hint">
                      {t.anchor.recoveryPrefix} {(jw.recovery.scale * 100).toFixed(0)}%
                      {jw.recovery.offset ? `${t.anchor.recoveryOffset} (${jw.recovery.offset[0]}, ${jw.recovery.offset[1]})` : ''}
                    </p>
                  )}
                  {!dwt?.found && (
                    <p className="text-sm text-secondary">{JW_DWT_RELATION.verifyJwNote}</p>
                  )}
                </div>
              </details>
            )}

            {anchor?.found && (
              <details className="result-details fade-in" open>
                <summary className="result-details-summary found">{p.anchor}</summary>
                <div className="result-details-body">
                  {claimVerdict === 'match' && anchor.artist_name ? (
                    <>
                      <div style={{
                        padding: 'var(--space-5) var(--space-4)',
                        borderRadius: 10,
                        background: 'var(--color-success-bg, #e8f5e9)',
                        border: '2px solid var(--color-success, #2e7d32)',
                        textAlign: 'center',
                        lineHeight: 1.5,
                      }}>
                        <div className="text-sm" style={{ color: 'var(--color-success, #1f7a4d)', marginBottom: 8 }}>
                          {t.anchor.resultTitle}
                        </div>
                        <div style={{
                          fontSize: '1.35rem',
                          fontWeight: 700,
                          letterSpacing: '0.04em',
                          fontFamily: 'var(--font-mono, monospace)',
                          color: 'var(--color-text)',
                        }}>
                          {formatAnchorUnlockLabel(anchor)}
                        </div>
                        <p className="text-sm text-secondary" style={{ margin: '10px 0 0' }}>
                          {t.anchor.formatHint}
                        </p>
                      </div>
                      {(jw?.protected_at || lsb?.text) && (
                        <div style={{ marginTop: 'var(--space-3)', lineHeight: 1.75 }}>
                          {jw?.protected_at && <p>{t.anchor.jwExactTime}<code>{jw.protected_at}</code></p>}
                          {lsb?.found && lsb.text && <p>{t.anchor.lsbOriginal}<code>{lsb.text}</code></p>}
                        </div>
                      )}
                      <button type="button" className="btn btn-secondary btn-sm" style={{ marginTop: 'var(--space-3)' }}
                        onClick={() => { setClaimVerdict('idle'); setClaimName('') }}>
                        {t.claim.retry}
                      </button>
                    </>
                  ) : (
                    <>
                      <p>{t.labels.authorCode}<code>{anchor.artist_code}</code></p>
                      {anchor.year_month && <p>{t.labels.yearMonth}<code>{anchor.year_month}</code></p>}
                      <p>{t.labels.confidence}<code>{((anchor.confidence || 0) * 100).toFixed(1)}%</code></p>
                      <div className="form-group" style={{ marginTop: 'var(--space-3)' }}>
                        <label className="form-label">{t.claim.inputLabel}</label>
                        <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
                          <input className="form-input" placeholder={t.claim.inputPlaceholder} value={claimName}
                            onChange={e => { setClaimName(e.target.value); setClaimVerdict('idle') }}
                            onKeyDown={e => { if (e.key === 'Enter' && file && claimName.trim()) runVerify(file, claimName) }} />
                          <button type="button" className="btn btn-secondary"
                            disabled={!file || !claimName.trim() || loading}
                            onClick={() => { if (file) runVerify(file, claimName) }}>
                            {loading ? t.claim.checking : t.claim.check}
                          </button>
                        </div>
                        {claimVerdict === 'mismatch' && (
                          <div style={{
                            marginTop: 10, padding: 'var(--space-3)', borderRadius: 8,
                            background: 'var(--color-danger-bg, #fdecea)',
                            border: '1px solid var(--color-danger, #c0392b)',
                            lineHeight: 1.7, color: 'var(--color-danger, #c0392b)',
                          }}>
                            <strong>{t.claim.mismatchTitle}</strong>
                            <p style={{ margin: '6px 0 0' }}>
                              {t.anchor.mismatchBody.replace('{name}', claimName.trim()).replace('{code}', anchor.artist_code ?? '')}
                              {anchor.claim_code ? (
                                <> {t.anchor.mismatchCode.replace('{code}', anchor.claim_code)}</>
                              ) : null}。
                            </p>
                            <p style={{ margin: '6px 0 0' }}>
                              {t.anchor.mismatchHint.replace('{pct}', ((anchor.confidence || 0) * 100).toFixed(1))}
                            </p>
                          </div>
                        )}
                        <span className="form-hint">
                          {t.anchor.claimHint}
                        </span>
                      </div>
                    </>
                  )}
                  <p className="text-sm text-secondary" style={{ marginTop: 'var(--space-3)' }}>
                    {t.anchor.verifyHint}
                  </p>
                </div>
              </details>
            )}

            {anchor && !anchor.found && (
              <details className="result-details fade-in" open>
                <summary className="result-details-summary">{t.anchor.notDetectedTitle}</summary>
                <div className="result-details-body">
                  <p className="text-sm text-secondary" style={{ lineHeight: 1.75 }}>
                    {t.anchor.notDetectedIntro}
                  </p>
                  <ul className="text-sm text-secondary" style={{ lineHeight: 1.8, margin: '8px 0 0', paddingLeft: '1.2em' }}>
                    {t.anchor.notDetectedBullets.map(line => (
                      <li key={line}>{line}</li>
                    ))}
                  </ul>
                </div>
              </details>
            )}

            {dwt?.found && (
              <details className="result-details fade-in" open>
                <summary className="result-details-summary found">{JW_DWT_RELATION.verifyStandaloneDwtTitle}</summary>
                <div className="result-details-body">
                  <p>{t.labels.payload}<code>{dwt.payload}</code></p>
                  {dwt.timestamp && <p>{t.labels.embeddedAt}<code>{dwt.timestamp}</code></p>}
                  <p>{t.labels.confidence}<code>{((dwt.confidence || 0) * 100).toFixed(1)}%</code></p>
                  {dwt.recovered && dwt.recovery && (
                    <p className="text-sm recovery-hint">
                      {t.anchor.recoveryPrefix} {(dwt.recovery.scale * 100).toFixed(0)}%
                    </p>
                  )}
                </div>
              </details>
            )}

            {lsb?.found && (
              <details className="result-details fade-in" open>
                <summary className="result-details-summary found">{p.lsb}</summary>
                <div className="result-details-body">
                  <p>{t.labels.lsbDetected}<code>{lsb.text}</code></p>
                  <p className="text-sm text-secondary">{t.lsb.hint}</p>
                </div>
              </details>
            )}

            {meta?.found && (
              <details className="result-details fade-in" open>
                <summary className="result-details-summary found">{p.metadata}</summary>
                <div className="result-details-body">
                  {meta.exif && Object.entries(meta.exif).map(([k, v]) => (
                    v ? <p key={k}>EXIF {k}：<code>{v}</code></p> : null
                  ))}
                  {meta.iptc && Object.entries(meta.iptc).map(([k, v]) => (
                    v ? <p key={k}>IPTC {k}：<code>{v}</code></p> : null
                  ))}
                </div>
              </details>
            )}

            {notFoundItems.length > 0 && !loading && (
              <div className="text-sm text-secondary" style={{ padding: 'var(--space-2) 0', lineHeight: 1.8 }}>
                {notFoundItems.map(item => (
                  <div key={item}>· {item}{t.hints.notDetectedSuffix}</div>
                ))}
                {jw && !jw.found && (
                  <p className="text-xs text-secondary" style={{ marginTop: 8, lineHeight: 1.6 }}>
                    {t.hints.uploadProtectedPng}
                  </p>
                )}
              </div>
            )}
          </div>
        </div>

        {/* 验证限度说明 — 诚实告知能验证什么、不能验证什么 */}
        <section className="jw-limits-card" style={{ marginTop: 'var(--space-12)', marginBottom: 'var(--space-8)' }}>
          <h3>{JW_VERIFY_LIMITS.title}</h3>
          {JW_VERIFY_LIMITS.paragraphs.map((p, i) => (
            <p key={i}>{p}</p>
          ))}
          <ul>
            {JW_VERIFY_LIMITS.bullets.map((b, i) => (
              <li key={i}>
                <strong>{b.strong}</strong>
                {b.body}
              </li>
            ))}
          </ul>
          <p className="text-sm text-secondary" style={{ marginTop: 'var(--space-4)', marginBottom: 0 }}>
            {t.links.faqMore} <Link to="/faq">{t.links.faq}</Link>
          </p>
        </section>

        {/* 核心信念 — 为什么仍然值得做这件事 */}
        <section className="card jw-belief-card" style={{ padding: 'var(--space-8)', marginTop: 'var(--space-12)' }}>
          <h2 style={{ marginBottom: 'var(--space-4)' }}>{JW_CORE_BELIEF_SUMMARY.title}</h2>
          {JW_CORE_BELIEF_SUMMARY.paragraphs.map((para, i) => (
            <p key={i} className="text-secondary" style={{ marginTop: i === 0 ? 0 : 'var(--space-3)', lineHeight: 1.8 }}>
              {para}
            </p>
          ))}
          <p style={{ marginTop: 'var(--space-5)', textAlign: 'center' }}>
            <Link to={JW_CORE_BELIEF_SUMMARY.linkTo} className="btn btn-secondary btn-sm">
              {JW_CORE_BELIEF_SUMMARY.linkLabel}
            </Link>
          </p>
        </section>
        <FeedbackHelpLink from="verify" />
      </div>
    </div>
  )
}
