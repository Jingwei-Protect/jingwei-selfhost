import type { Locale } from '../i18n/types'
import { LOCALES } from '../i18n/types'
import { SITE_URL } from './site'

/**
 * hreflang codes — keep in sync with sitemap.xml and api/spa_seo.py.
 * Use BCP-47 script subtags for Chinese (zh-Hans / zh-Hant).
 */
export const HREFLANG_CODES: Record<Locale, string> = {
  'zh-Hans': 'zh-Hans',
  'zh-Hant': 'zh-Hant',
  en: 'en',
  ja: 'ja',
}

export const OG_LOCALE_CODES: Record<Locale, string> = {
  'zh-Hans': 'zh_CN',
  'zh-Hant': 'zh_TW',
  en: 'en_US',
  ja: 'ja_JP',
}

const LANG_QUERY = 'lang'

/** 规范化路径：保证以 / 开头、无尾斜杠（根路径除外） */
export function normalizePathname(pathname: string): string {
  if (!pathname || pathname === '/') return '/'
  return pathname.endsWith('/') ? pathname.slice(0, -1) : pathname
}

/** 带语言参数的完整 URL（供 hreflang 使用） */
export function localePageUrl(pathname: string, locale: Locale): string {
  const path = normalizePathname(pathname)
  const base = path === '/' ? SITE_URL : `${SITE_URL}${path}`
  const url = new URL(base)
  url.searchParams.set(LANG_QUERY, locale)
  return url.toString()
}

/** 无语言参数的 canonical URL（x-default） */
export function canonicalPageUrl(pathname: string): string {
  const path = normalizePathname(pathname)
  return path === '/' ? `${SITE_URL}/` : `${SITE_URL}${path}`
}

export function hreflangAlternates(pathname: string): Array<{ hreflang: string; href: string }> {
  const alts = LOCALES.map(locale => ({
    hreflang: HREFLANG_CODES[locale],
    href: localePageUrl(pathname, locale),
  }))
  alts.push({ hreflang: 'x-default', href: canonicalPageUrl(pathname) })
  return alts
}

/** 从 URL 读取 ?lang= */
export function readLocaleFromSearch(search: string): Locale | null {
  const raw = new URLSearchParams(search).get(LANG_QUERY)
  if (raw === 'zh-Hans' || raw === 'zh-Hant' || raw === 'en' || raw === 'ja') return raw
  return null
}

export function readLocaleFromWindow(): Locale | null {
  if (typeof window === 'undefined') return null
  return readLocaleFromSearch(window.location.search)
}

/** 将 locale 写入当前 URL（不刷新页面） */
export function replaceLocaleInUrl(locale: Locale): void {
  if (typeof window === 'undefined') return
  const url = new URL(window.location.href)
  url.searchParams.set(LANG_QUERY, locale)
  window.history.replaceState(null, '', url)
}

/** sitemap 用的主要公开页面 */
export const SITEMAP_PUBLIC_PATHS = [
  '/',
  '/protect',
  '/verify',
  '/inspect',
  '/about',
  '/protocol',
  '/faq',
  '/blog',
  '/blog/quick-credit-mode',
  '/blog/jingwei-holo-card',
  '/blog/why-ai-image-theft-is-easy',
  '/blog/how-to-use-jingwei-visible-layers',
  '/guide/watermark-matrix',
  '/delivery',
  '/privacy',
  '/terms',
] as const
