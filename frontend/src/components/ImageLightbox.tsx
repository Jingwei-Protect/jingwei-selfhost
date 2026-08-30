import { useEffect, useCallback } from 'react'

interface ImageLightboxProps {
  src: string | null
  alt?: string
  caption?: string
  onClose: () => void
}

/**
 * Full-screen image viewer with Escape-to-close and click-outside-to-close.
 * The image scales to fit the viewport while preserving its aspect ratio.
 */
export default function ImageLightbox({ src, alt, caption, onClose }: ImageLightboxProps) {
  const handleKey = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    },
    [onClose],
  )

  useEffect(() => {
    if (!src) return
    document.addEventListener('keydown', handleKey)
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', handleKey)
      document.body.style.overflow = prevOverflow
    }
  }, [src, handleKey])

  if (!src) return null

  return (
    <div
      className="image-lightbox-backdrop"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="图像全屏查看"
    >
      <button
        type="button"
        className="image-lightbox-close"
        aria-label="关闭"
        onClick={(e) => {
          e.stopPropagation()
          onClose()
        }}
      >
        ×
      </button>
      <div className="image-lightbox-stage" onClick={(e) => e.stopPropagation()}>
        {caption ? <p className="image-lightbox-caption">{caption}</p> : null}
        <img
          className="image-lightbox-img"
          src={src}
          alt={alt || 'preview'}
        />
      </div>
      <div className="image-lightbox-hint">点击任意处或按 Esc 关闭</div>
    </div>
  )
}
