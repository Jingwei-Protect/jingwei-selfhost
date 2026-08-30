import { useCallback, useRef, useState, type ReactNode } from 'react'
import { useLocale } from '../i18n/LocaleContext'

interface Props {
  onFile: (file: File) => void
  preview?: string | null
  onClear?: () => void
  height?: number
  label?: string
  overlay?: ReactNode
  loading?: boolean
}

export default function ImageUpload({ onFile, preview, onClear, height = 280, label, overlay, loading }: Props) {
  const { messages: m } = useLocale()
  const t = m.components.imageUpload
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)

  const handleFile = useCallback((f: File) => {
    if (f.type.startsWith('image/')) onFile(f)
  }, [onFile])

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0])
  }, [handleFile])

  if (preview) {
    return (
      <div className="image-preview preview-with-overlay" style={{ maxHeight: height }}>
        <img src={preview} alt={String(t.previewAlt)} style={{ maxHeight: height, objectFit: 'contain', width: '100%' }} />
        {overlay}
        {loading && (
          <div className="preview-loading-overlay">
            <span className="spinner" />
            <span>{t.processing}</span>
          </div>
        )}
        {onClear && (
          <button className="remove-btn" onClick={onClear} title={String(t.remove)}>×</button>
        )}
      </div>
    )
  }

  return (
    <>
      <div
        className={`upload-area${dragging ? ' dragging' : ''}`}
        onClick={() => inputRef.current?.click()}
        onDragOver={e => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        style={{ minHeight: height }}
      >
        <div className="icon">↑</div>
        <p><strong>{label || t.uploadDefault}</strong></p>
        <p style={{ marginTop: 4 }}>{t.uploadHint}</p>
      </div>
      <input
        ref={inputRef}
        type="file"
        accept="image/png,image/jpeg,image/webp,.png,.jpg,.jpeg,.webp"
        style={{ display: 'none' }}
        onChange={e => { if (e.target.files?.[0]) handleFile(e.target.files[0]) }}
      />
    </>
  )
}
