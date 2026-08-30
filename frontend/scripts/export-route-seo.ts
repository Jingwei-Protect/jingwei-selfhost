/**
 * Export crawler-visible route meta + FAQ JSON-LD into public/seo/.
 * Run before `vite build` so FastAPI can inject per-route SEO for non-JS crawlers.
 */

import { mkdirSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { buildArticleJsonLd, type BlogPost } from '../src/content/blog/types'
import {
  getAuthorLetterBundle,
  getBlogBundle,
  getFaqBundle,
  getJwBundle,
  getLegalBundle,
  getMatrixBundle,
  getPrivacyBundle,
} from '../src/i18n/contentBridge'
import { getMessages } from '../src/i18n/messages'
import { LOCALES, type Locale } from '../src/i18n/types'
import { SITE_NAME, SITE_URL } from '../src/lib/site'

const OUT_DIR = join(import.meta.dirname, '..', 'public', 'seo')

type RouteSeoEntry = {
  title: string
  description: string
  robots?: string
  jsonLdFile?: string
  shellHeading?: string
  shellParagraphs?: string[]
}

type RoutesSeo = Record<string, Partial<Record<Locale, RouteSeoEntry>>>

function blogShellParagraphs(post: BlogPost): string[] {
  return [
    post.intro.lead,
    ...post.paragraphs,
    ...(post.sections?.flatMap(s => [s.heading, ...s.paragraphs]) ?? []),
  ].filter(Boolean)
}

function buildRouteMeta(path: string, locale: Locale): RouteSeoEntry | null {
  const m = getMessages(locale)
  const faq = getFaqBundle(locale)
  const jw = getJwBundle(locale)
  const letter = getAuthorLetterBundle(locale)
  const privacy = getPrivacyBundle(locale)
  const legal = getLegalBundle(locale)
  const blog = getBlogBundle(locale)
  const matrix = getMatrixBundle(locale)

  if (path === 'blog') {
    return {
      title: blog.BLOG_INDEX.metaTitle,
      description: blog.BLOG_INDEX.metaDescription,
      shellHeading: blog.BLOG_INDEX.title,
      shellParagraphs: [blog.BLOG_INDEX.lead],
    }
  }

  if (path.startsWith('blog/')) {
    const slug = path.slice('blog/'.length)
    const post = blog.BLOG_POSTS.find(p => p.slug === slug)
    if (!post) return null
    const canonical = `${SITE_URL}/blog/${post.slug}`
    return {
      title: post.metaTitle,
      description: post.metaDescription,
      jsonLdFile: `blog-${post.slug}-${locale}.json`,
      shellHeading: post.intro.title,
      shellParagraphs: blogShellParagraphs(post),
    }
  }

  if (path === 'guide/watermark-matrix') {
    const tableSummary = matrix.MATRIX_TABLE.map(
      row => `${row.layer}. ${row.normalView} ${row.afterAiWash}`,
    )
    return {
      title: matrix.MATRIX_META_TITLE,
      description: matrix.MATRIX_META_DESCRIPTION,
      jsonLdFile: `matrix-jsonld-${locale}.json`,
      shellHeading: matrix.MATRIX_INTRO.title,
      shellParagraphs: [matrix.MATRIX_INTRO.lead, ...tableSummary],
    }
  }

  switch (path) {
    case 'faq': {
      const topQuestions = faq.FAQ_CATEGORIES.flatMap(c => c.items.map(i => i.question)).slice(0, 5)
      return {
        title: faq.FAQ_META_TITLE,
        description: faq.FAQ_META_DESCRIPTION,
        jsonLdFile: `faq-jsonld-${locale}.json`,
        shellHeading: faq.FAQ_INTRO.title,
        shellParagraphs: [
          faq.FAQ_INTRO.lead,
          topQuestions.join(' · '),
          faq.FAQ_META_DESCRIPTION,
        ].filter(Boolean),
      }
    }
    case 'protocol':
      return {
        title: `${m.protocol.pageTitle} · ${SITE_NAME}`,
        description: jw.JW_PROTOCOL_META_DESCRIPTION,
        shellHeading: m.protocol.pageTitle,
        shellParagraphs: [jw.JW_PROTOCOL_META_DESCRIPTION],
      }
    case 'about':
      return {
        title: letter.AUTHOR_LETTER_META_TITLE,
        description: letter.AUTHOR_LETTER_META_DESCRIPTION,
        shellHeading: letter.AUTHOR_LETTER_INTRO.title,
        shellParagraphs: [
          letter.AUTHOR_LETTER_INTRO.lead,
          letter.AUTHOR_LETTER_META_DESCRIPTION,
        ],
      }
    case 'protect':
      return {
        title: `${m.protect.pageTitle} · ${SITE_NAME}`,
        description: m.protect.metaDescription,
        shellHeading: m.protect.pageTitle,
        shellParagraphs: [
          m.protect.pageLead,
          m.protect.metaDescription,
          `${m.protect.process.upload}: ${m.protect.process.uploadDesc}`,
          `${m.protect.process.write}: ${m.protect.process.writeDesc}`,
          `${m.protect.process.download}: ${m.protect.process.downloadDesc}`,
        ],
      }
    case 'verify':
      return {
        title: `${m.verify.pageTitle} · ${SITE_NAME}`,
        description: m.verify.metaDescription,
        shellHeading: m.verify.pageTitle,
        shellParagraphs: [m.verify.pageLead, m.verify.metaDescription],
      }
    case 'inspect':
      return {
        title: `${m.inspect.title} · ${SITE_NAME}`,
        description: m.inspect.metaDescription,
        shellHeading: m.inspect.title,
        shellParagraphs: [m.inspect.metaDescription],
      }
    case 'delivery':
      return {
        title: `${m.delivery.title} · ${SITE_NAME}`,
        description: m.delivery.subtitle,
        shellHeading: m.delivery.title,
        shellParagraphs: [m.delivery.subtitle],
      }
    case 'privacy': {
      const summary = privacy.PRIVACY_SECTIONS.find(s => s.id === 'summary')
      const lead =
        summary && 'paragraphs' in summary && summary.paragraphs?.[0]
          ? summary.paragraphs[0]
          : privacy.PRIVACY_TITLE
      return {
        title: `${privacy.PRIVACY_TITLE} · ${SITE_NAME}`,
        description: lead,
        shellHeading: privacy.PRIVACY_TITLE,
        shellParagraphs: [lead],
      }
    }
    case 'terms':
      return {
        title: `${legal.LEGAL_TERMS_TITLE} · ${SITE_NAME}`,
        description: legal.LEGAL_TERMS_INTRO[0] ?? legal.LEGAL_TERMS_TITLE,
        shellHeading: legal.LEGAL_TERMS_TITLE,
        shellParagraphs: [legal.LEGAL_TERMS_INTRO[0] ?? legal.LEGAL_TERMS_TITLE],
      }
    case 'community':
      return {
        title: `${m.common.nav.community} · ${SITE_NAME}`,
        description: m.community.terms.intro,
        robots: 'noindex, follow',
        shellHeading: m.common.nav.community,
        shellParagraphs: [m.community.terms.intro],
      }
    default:
      return null
  }
}

function writeJsonLd(path: string, payload: unknown) {
  writeFileSync(path, `${JSON.stringify(payload, null, 2)}\n`, 'utf-8')
}

function main() {
  mkdirSync(OUT_DIR, { recursive: true })
  const routes: RoutesSeo = {}
  const blogSlugs = new Set<string>()
  for (const locale of LOCALES) {
    for (const post of getBlogBundle(locale).BLOG_POSTS) {
      blogSlugs.add(post.slug)
    }
  }

  const routePaths = [
    'faq',
    'protocol',
    'about',
    'protect',
    'verify',
    'inspect',
    'delivery',
    'privacy',
    'terms',
    'community',
    'blog',
    'guide/watermark-matrix',
    ...[...blogSlugs].map(slug => `blog/${slug}`),
  ] as const

  for (const path of routePaths) {
    routes[path] = {}
    for (const locale of LOCALES) {
      const meta = buildRouteMeta(path, locale)
      if (!meta) continue
      routes[path]![locale] = meta

      if (path === 'faq' && meta.jsonLdFile) {
        const faq = getFaqBundle(locale)
        writeJsonLd(join(OUT_DIR, meta.jsonLdFile), faq.buildFaqJsonLd())
      }

      if (path.startsWith('blog/') && meta.jsonLdFile) {
        const slug = path.slice('blog/'.length)
        const post = getBlogBundle(locale).BLOG_POSTS.find(p => p.slug === slug)
        if (post) {
          writeJsonLd(
            join(OUT_DIR, meta.jsonLdFile),
            buildArticleJsonLd(post, `${SITE_URL}/blog/${post.slug}`),
          )
        }
      }

      if (path === 'guide/watermark-matrix' && meta.jsonLdFile) {
        const matrix = getMatrixBundle(locale)
        writeJsonLd(join(OUT_DIR, meta.jsonLdFile), {
          '@context': 'https://schema.org',
          '@type': 'WebPage',
          name: matrix.MATRIX_INTRO.title,
          description: matrix.MATRIX_META_DESCRIPTION,
          url: matrix.MATRIX_CANONICAL,
          dateModified: matrix.MATRIX_DATE_MODIFIED,
          inLanguage: locale,
          isPartOf: { '@type': 'WebSite', name: SITE_NAME, url: SITE_URL },
        })
      }
    }
  }

  // Non-marketing / experimental routes: unique titles + noindex (avoid soft-404).
  const noindexRoutes: Record<string, { title: string; description: string; robots?: string }> = {
    'adv-protect': {
      title: `实验性对抗保护 · ${SITE_NAME}`,
      description: '实验性对抗保护页面（需本地开启）。默认不面向搜索引擎收录。',
      robots: 'noindex, follow',
    },
    support: {
      title: `支持精卫 · ${SITE_NAME}`,
      description: '支持与赞助页面。',
      robots: 'noindex, follow',
    },
    'support/return': {
      title: `支付返回 · ${SITE_NAME}`,
      description: '支付流程返回页。',
      robots: 'noindex, nofollow',
    },
    feedback: {
      title: `反馈 · ${SITE_NAME}`,
      description: '用户反馈表单。',
      robots: 'noindex, follow',
    },
    messages: {
      title: `站内消息 · ${SITE_NAME}`,
      description: '登录用户消息箱。',
      robots: 'noindex, nofollow',
    },
    'admin/sea': {
      title: `管理 · ${SITE_NAME}`,
      description: '管理员页面。',
      robots: 'noindex, nofollow',
    },
    'admin/feedback': {
      title: `管理 · ${SITE_NAME}`,
      description: '管理员页面。',
      robots: 'noindex, nofollow',
    },
    'admin/announcements': {
      title: `管理 · ${SITE_NAME}`,
      description: '管理员页面。',
      robots: 'noindex, nofollow',
    },
    'admin/users': {
      title: `管理 · ${SITE_NAME}`,
      description: '管理员页面。',
      robots: 'noindex, nofollow',
    },
    'preview/sea-ripples': {
      title: `预览 · ${SITE_NAME}`,
      description: '内部预览页。',
      robots: 'noindex, nofollow',
    },
    'preview/anchor-lab': {
      title: `预览 · ${SITE_NAME}`,
      description: '内部预览页。',
      robots: 'noindex, nofollow',
    },
    'anchor-lab': {
      title: `锚点实验 · ${SITE_NAME}`,
      description: '实验工具页，不面向搜索收录。',
      robots: 'noindex, nofollow',
    },
    'blog/how-jingwei-visible-layers-work': {
      title: '精卫怎么用：五种可见层怎么选 | 精卫博客',
      description: '已迁移至 /blog/how-to-use-jingwei-visible-layers 。',
      robots: 'noindex, follow',
    },
  }
  for (const [path, meta] of Object.entries(noindexRoutes)) {
    routes[path] = {}
    for (const locale of LOCALES) {
      routes[path]![locale] = {
        title: meta.title,
        description: meta.description,
        robots: meta.robots ?? 'noindex, follow',
        shellHeading: meta.title.split(' · ')[0] ?? meta.title,
        shellParagraphs: [meta.description],
      }
    }
  }

  writeFileSync(
    join(OUT_DIR, 'routes.json'),
    `${JSON.stringify({ siteUrl: SITE_URL, generatedAt: new Date().toISOString().slice(0, 10), routes }, null, 2)}\n`,
    'utf-8',
  )
  console.log(`Wrote route SEO bundle to ${OUT_DIR}`)
}

main()
