import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import Accordion from '../components/Accordion'
import ImageUpload from '../components/ImageUpload'
import LegalConsentGate from '../components/LegalConsentGate'
import { usePageSeo } from '../hooks/usePageSeo'
import { useLocale } from '../i18n/LocaleContext'
import { SITE_URL } from '../lib/site'
import { downloadProtectedImage } from '../utils/downloadDataUrl'

type StatusPayload = {
  ok?: boolean
  enabled?: boolean
  torch_installed?: boolean
  device_hint?: string
  model_id?: string
}

type Metrics = {
  psnr?: number
  elapsed_sec?: number
  device?: string
}

type Strength = 'light' | 'standard' | 'strong'

const STRENGTH_PRESETS: Record<Strength, { steps: number; eps: number }> = {
  light: { steps: 30, eps: 0.04 },
  standard: { steps: 50, eps: 0.06 },
  strong: { steps: 80, eps: 0.08 },
}

export default function AdvProtectPage() {
  return (
    <LegalConsentGate>
      <AdvProtectPageInner />
    </LegalConsentGate>
  )
}

function AdvProtectPageInner() {
  const { messages: m } = useLocale()
  const t = m.advProtect

  usePageSeo({
    title: `${t.pageTitle} · 精卫 Jingwei`,
    description: t.pageLead,
    canonical: `${SITE_URL}/adv-protect`,
    robots: 'noindex, follow',
  })

  const [status, setStatus] = useState<StatusPayload | null>(null)
  const [statusError, setStatusError] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [uploadPreview, setUploadPreview] = useState<string | null>(null)
  const [strength, setStrength] = useState<Strength>('standard')
  const [steps, setSteps] = useState(STRENGTH_PRESETS.standard.steps)
  const [eps, setEps] = useState(STRENGTH_PRESETS.standard.eps)
  const [customAdvanced, setCustomAdvanced] = useState(false)
  const [busy, setBusy] = useState<'idle' | 'preview' | 'run'>('idle')
  const [resultUrl, setResultUrl] = useState<string | null>(null)
  const [resultKind, setResultKind] = useState<'preview' | 'final' | null>(null)
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const res = await fetch('/api/adv-protect/status')
        const data = (await res.json()) as StatusPayload
        if (!cancelled) {
          setStatus(data)
          setStatusError('')
        }
      } catch {
        if (!cancelled) {
          setStatusError(t.errors.network)
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [t.errors.network])

  const handleFile = useCallback((f: File) => {
    setFile(f)
    setUploadPreview(URL.createObjectURL(f))
    setResultUrl(null)
    setResultKind(null)
    setMetrics(null)
    setError('')
  }, [])

  const clearFile = useCallback(() => {
    setFile(null)
    setUploadPreview(null)
    setResultUrl(null)
    setResultKind(null)
    setMetrics(null)
    setError('')
  }, [])

  const applyStrength = useCallback((next: Strength) => {
    setStrength(next)
    setCustomAdvanced(false)
    setSteps(STRENGTH_PRESETS[next].steps)
    setEps(STRENGTH_PRESETS[next].eps)
    setResultUrl(null)
    setResultKind(null)
    setMetrics(null)
  }, [])

  const canRun = Boolean(status?.enabled && status?.torch_installed)
  const processing = busy !== 'idle'

  const activeParams = useMemo(() => {
    if (customAdvanced) return { steps, eps }
    return STRENGTH_PRESETS[strength]
  }, [customAdvanced, steps, eps, strength])

  const runProtect = useCallback(
    async (kind: 'preview' | 'final') => {
      if (!file) {
        setError(t.errors.noFile)
        return
      }
      if (!canRun) return
      setBusy(kind === 'preview' ? 'preview' : 'run')
      setError('')
      setResultUrl(null)
      setResultKind(null)
      setMetrics(null)

      const fd = new FormData()
      fd.append('image', file)
      fd.append('steps', String(activeParams.steps))
      fd.append('eps', String(activeParams.eps))

      try {
        const res = await fetch('/api/adv-protect', { method: 'POST', body: fd })
        const data = await res.json()
        if (data.ok && data.image) {
          setResultUrl(data.image as string)
          setResultKind(kind)
          setMetrics((data.metrics as Metrics) || null)
        } else {
          setError((data.error as string) || t.errors.failed)
        }
      } catch {
        setError(t.errors.network)
      } finally {
        setBusy('idle')
      }
    },
    [file, canRun, activeParams, t.errors.noFile, t.errors.failed, t.errors.network],
  )

  const downloadResult = useCallback(() => {
    if (!resultUrl) return
    downloadProtectedImage(resultUrl, 'jingwei-adv', 'png')
  }, [resultUrl])

  return (
    <div className="page-section">
      <div className="container" style={{ maxWidth: 720 }}>
        <div className="section-header" style={{ textAlign: 'center', marginBottom: 32 }}>
          <h1>{t.pageTitle}</h1>
          <p style={{ marginTop: 8 }}>{t.pageLead}</p>
        </div>

        <div
          className="card"
          style={{
            padding: 'var(--space-5)',
            marginBottom: 'var(--space-6)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-md)',
            background: 'var(--color-surface-muted, rgba(0,0,0,0.03))',
          }}
        >
          <strong style={{ display: 'block', marginBottom: 8 }}>{t.disclosureTitle}</strong>
          <p style={{ margin: 0, lineHeight: 1.65, fontSize: '0.95rem' }}>{t.disclosure}</p>
        </div>

        <div style={{ marginBottom: 'var(--space-6)', lineHeight: 1.65 }}>
          {statusError ? (
            <p style={{ color: 'var(--color-danger, #b00020)' }}>{statusError}</p>
          ) : !status ? (
            <p>{t.statusLoading}</p>
          ) : !status.enabled ? (
            <>
              <p>
                <strong>{t.statusDisabledTitle}</strong>
              </p>
              <p style={{ marginTop: 8 }}>{t.statusDisabledBody}</p>
            </>
          ) : !status.torch_installed ? (
            <p>{t.statusDepsMissing}</p>
          ) : (
            <>
              <p>
                <strong>{t.statusReady}</strong>
              </p>
              <p style={{ marginTop: 4, fontSize: '0.9rem', opacity: 0.85 }}>
                {t.statusDevice.replace('{device}', status.device_hint || '—')}
              </p>
              <p style={{ marginTop: 2, fontSize: '0.9rem', opacity: 0.85 }}>
                {t.statusModel.replace('{model}', status.model_id || '—')}
              </p>
            </>
          )}
        </div>

        <div style={{ marginBottom: 'var(--space-6)' }}>
          <h3 style={{ marginBottom: 'var(--space-4)' }}>{t.upload}</h3>
          <ImageUpload
            onFile={handleFile}
            preview={uploadPreview}
            onClear={clearFile}
            loading={processing}
          />
        </div>

        <div style={{ marginBottom: 'var(--space-5)' }}>
          <h3 style={{ marginBottom: 'var(--space-3)' }}>{t.strength}</h3>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
            {(
              [
                ['light', t.strengthLight],
                ['standard', t.strengthStandard],
                ['strong', t.strengthStrong],
              ] as const
            ).map(([key, label]) => (
              <button
                key={key}
                type="button"
                className={`radio-pill${strength === key && !customAdvanced ? ' active' : ''}`}
                disabled={!canRun || processing}
                onClick={() => applyStrength(key)}
              >
                {label}
              </button>
            ))}
          </div>
          <p className="form-hint" style={{ marginTop: 'var(--space-3)' }}>
            {t.strengthHint}
            {customAdvanced ? ` · ${t.strengthCustomNote}` : ''}
          </p>
        </div>

        <div style={{ marginBottom: 'var(--space-6)' }}>
          <Accordion title={t.advancedTitle}>
            <div className="form-group" style={{ marginBottom: 'var(--space-4)' }}>
              <label className="form-label" htmlFor="adv-steps">
                {t.steps}
              </label>
              <input
                id="adv-steps"
                className="form-input"
                type="number"
                min={1}
                max={200}
                value={steps}
                disabled={!canRun || processing}
                onChange={(e) => {
                  setCustomAdvanced(true)
                  setSteps(Number(e.target.value) || STRENGTH_PRESETS.standard.steps)
                }}
              />
              <p className="form-hint">{t.stepsHint}</p>
            </div>

            <div className="form-group" style={{ marginBottom: 'var(--space-4)' }}>
              <label className="form-label" htmlFor="adv-eps">
                {t.eps}
              </label>
              <input
                id="adv-eps"
                className="form-input"
                type="number"
                min={0.01}
                max={0.25}
                step={0.01}
                value={eps}
                disabled={!canRun || processing}
                onChange={(e) => {
                  setCustomAdvanced(true)
                  setEps(Number(e.target.value) || STRENGTH_PRESETS.standard.eps)
                }}
              />
              <p className="form-hint">{t.epsHint}</p>
            </div>

            <button
              type="button"
              className="btn btn-secondary"
              disabled={!canRun || !file || processing}
              onClick={() => void runProtect('preview')}
              style={{ width: '100%' }}
            >
              {busy === 'preview' ? t.previewing : t.preview}
            </button>
          </Accordion>
        </div>

        <button
          type="button"
          className="btn btn-primary btn-lg"
          disabled={!canRun || !file || processing}
          onClick={() => void runProtect('final')}
          style={{ width: '100%' }}
        >
          {busy === 'run' ? t.processing : t.start}
        </button>

        {error ? (
          <p style={{ marginTop: 'var(--space-4)', color: 'var(--color-danger, #b00020)' }}>
            {error}
          </p>
        ) : null}

        {resultUrl ? (
          <div style={{ marginTop: 'var(--space-8)' }}>
            <h3 style={{ marginBottom: 'var(--space-4)' }}>
              {resultKind === 'preview' ? t.previewResult : t.result}
            </h3>
            {metrics ? (
              <p style={{ marginBottom: 'var(--space-3)', fontSize: '0.9rem', opacity: 0.85 }}>
                {metrics.psnr != null
                  ? t.metricsPsnr.replace('{n}', String(metrics.psnr))
                  : null}
                {metrics.psnr != null && metrics.elapsed_sec != null ? ' · ' : null}
                {metrics.elapsed_sec != null
                  ? t.metricsTime.replace('{n}', String(metrics.elapsed_sec))
                  : null}
              </p>
            ) : null}
            <img
              src={resultUrl}
              alt=""
              style={{
                width: '100%',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--color-border)',
              }}
            />
            <button
              type="button"
              className="btn btn-secondary"
              style={{ marginTop: 'var(--space-4)' }}
              onClick={downloadResult}
            >
              {t.download}
            </button>
          </div>
        ) : null}

        <p style={{ marginTop: 'var(--space-8)', textAlign: 'center' }}>
          <Link to="/protect">{t.backProtect}</Link>
        </p>
      </div>
    </div>
  )
}
