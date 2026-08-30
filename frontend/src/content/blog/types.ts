export interface BlogFigure {
  /** 单张配图 */
  kind: 'single'
  src: string
  alt: string
  caption?: string
}

export interface BlogCompareFigure {
  /** 加水印后 vs AI 试图修复后 */
  kind: 'compare'
  protectedSrc: string
  aiRestoredSrc: string
  protectedAlt: string
  aiRestoredAlt: string
  protectedLabel: string
  aiRestoredLabel: string
  caption?: string
}

export interface BlogHoloFigure {
  /** 成品闪卡：可悬停的箔面 + 导出短视频，不放静帧拆解 */
  kind: 'holo'
  cardSrc: string
  videoSrc: string
  alt: string
  caption?: string
}

export type BlogMedia = BlogFigure | BlogCompareFigure | BlogHoloFigure

export interface BlogSection {
  heading: string
  paragraphs: readonly string[]
  media?: readonly BlogMedia[]
}

export interface BlogIntro {
  kicker: string
  title: string
  lead: string
  updated: string
}

export interface BlogPost {
  slug: string
  datePublished: string
  dateModified: string
  metaTitle: string
  metaDescription: string
  intro: BlogIntro
  /** 头图（可选） */
  heroMedia?: BlogMedia
  /** 正文段落（作者信式连续 prose） */
  paragraphs: readonly string[]
  /** 可选分节标题 + 段落 + 配图 */
  sections?: readonly BlogSection[]
  relatedLinks: readonly { to: string; label: string }[]
}

export interface BlogIndexCopy {
  canonical: string
  metaTitle: string
  metaDescription: string
  title: string
  lead: string
}

export function buildArticleJsonLd(post: BlogPost, canonical: string): Record<string, unknown> {
  const bodyText = [
    post.intro.lead,
    ...post.paragraphs,
    ...(post.sections?.flatMap(s => [
      s.heading,
      ...s.paragraphs,
      ...(s.media?.map(m => {
        if (m.kind === 'compare') return m.caption ?? m.protectedAlt
        return m.caption ?? m.alt
      }) ?? []),
    ]) ?? []),
  ].join('\n\n')

  return {
    '@context': 'https://schema.org',
    '@type': 'Article',
    headline: post.intro.title,
    description: post.metaDescription,
    url: canonical,
    datePublished: post.datePublished,
    dateModified: post.dateModified,
    inLanguage: ['zh-Hans', 'zh-Hant', 'en', 'ja'],
    author: { '@type': 'Organization', name: 'Jingwei', url: 'https://jwprotect.com/about' },
    publisher: { '@type': 'Organization', name: 'Jingwei', url: 'https://jwprotect.com/' },
    articleBody: bodyText,
    mainEntityOfPage: canonical,
  }
}
