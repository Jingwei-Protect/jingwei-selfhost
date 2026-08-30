import { HoloCard } from '../holo-card/HoloCard'
import { useLocale } from '../i18n/LocaleContext'
import type { BlogMedia } from '../content/blog/types'

export default function BlogMediaBlock({ media }: { media: BlogMedia }) {
  const { messages: m } = useLocale()

  if (media.kind === 'holo') {
    return (
      <figure className="blog-figure blog-figure--holo">
        <div className="blog-holo-stack">
          <div className="blog-holo-cell">
            <span className="blog-figure-pair-label">{m.blogPage.holoCardLabel}</span>
            <div className="blog-holo-frame">
              <HoloCard className="blog-holo-card">
                <img src={media.cardSrc} alt={media.alt} />
              </HoloCard>
            </div>
            <p className="blog-holo-hint">{m.blogPage.holoHoverHint}</p>
          </div>
          <div className="blog-holo-cell">
            <span className="blog-figure-pair-label">{m.blogPage.holoVideoLabel}</span>
            <div className="blog-holo-frame">
              <video
                className="blog-holo-video"
                src={media.videoSrc}
                controls
                playsInline
                muted
                loop
                autoPlay
                preload="metadata"
              />
            </div>
          </div>
        </div>
        {media.caption ? <figcaption>{media.caption}</figcaption> : null}
      </figure>
    )
  }

  if (media.kind === 'single') {
    return (
      <figure className="blog-figure">
        <div className="jw-sample-mark">
          <img src={media.src} alt={media.alt} loading="lazy" decoding="async" />
        </div>
        {media.caption ? <figcaption>{media.caption}</figcaption> : null}
      </figure>
    )
  }

  return (
    <figure className="blog-figure blog-figure--compare">
      <div className="blog-figure-pair">
        <div className="blog-figure-pair-cell">
          <div className="jw-sample-mark">
            <img src={media.protectedSrc} alt={media.protectedAlt} loading="lazy" decoding="async" />
          </div>
          <span className="blog-figure-pair-label">{media.protectedLabel}</span>
        </div>
        <div className="blog-figure-pair-cell">
          <div className="jw-sample-mark">
            <img src={media.aiRestoredSrc} alt={media.aiRestoredAlt} loading="lazy" decoding="async" />
          </div>
          <span className="blog-figure-pair-label">{media.aiRestoredLabel}</span>
        </div>
      </div>
      {media.caption ? <figcaption>{media.caption}</figcaption> : null}
    </figure>
  )
}
