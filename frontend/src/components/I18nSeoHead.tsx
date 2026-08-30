import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { useLocale } from '../i18n/LocaleContext'
import {
  canonicalPageUrl,
  HREFLANG_CODES,
  OG_LOCALE_CODES,
  hreflangAlternates,
  normalizePathname,
} from '../lib/i18nSeo'
import type { Locale } from '../i18n/types'
import { LOCALES } from '../i18n/types'

const HREFLANG_ATTR = 'data-jw-hreflang'
const OG_LOCALE_ATTR = 'data-jw-og-locale'

function upsertMeta(property: string, content: string, attr: string): void {
  let el = document.querySelector<HTMLMetaElement>(`meta[${attr}="${property}"]`)
  if (!el) {
    el = document.createElement('meta')
    el.setAttribute(attr, property)
    document.head.appendChild(el)
  }
  el.content = content
}

/** 移除动态写入的 hreflang，以及 index.html 中的静态 hreflang，避免首页重复。 */
function removeHreflangLinks(): void {
  document.querySelectorAll('link[rel="alternate"][hreflang]').forEach(node => node.remove())
}

function removeJwOgLocaleAlternates(): void {
  document.querySelectorAll(`meta[property="og:locale:alternate"][${OG_LOCALE_ATTR}]`).forEach(node => node.remove())
}

/**
 * 按当前路由写入 hreflang 与 og:locale，供多语言 SEO。
 */
export default function I18nSeoHead() {
  const { pathname } = useLocation()
  const { locale } = useLocale()

  useEffect(() => {
    const path = normalizePathname(pathname)
    removeHreflangLinks()

    let canonical = document.querySelector<HTMLLinkElement>('link[rel="canonical"]')
    const prevCanonical = canonical?.href ?? ''
    if (!canonical) {
      canonical = document.createElement('link')
      canonical.rel = 'canonical'
      document.head.appendChild(canonical)
    }
    canonical.href = canonicalPageUrl(path)

    for (const alt of hreflangAlternates(path)) {
      const link = document.createElement('link')
      link.rel = 'alternate'
      link.hreflang = alt.hreflang
      link.href = alt.href
      link.setAttribute(HREFLANG_ATTR, '1')
      document.head.appendChild(link)
    }

    upsertMeta('og:locale', OG_LOCALE_CODES[locale], 'property')
    removeJwOgLocaleAlternates()
    for (const code of LOCALES) {
      if (code === locale) continue
      const el = document.createElement('meta')
      el.setAttribute('property', 'og:locale:alternate')
      el.content = OG_LOCALE_CODES[code]
      el.setAttribute(OG_LOCALE_ATTR, '1')
      document.head.appendChild(el)
    }

    return () => {
      removeHreflangLinks()
      removeJwOgLocaleAlternates()
      if (canonical) canonical.href = prevCanonical || 'https://jwprotect.com/'
    }
  }, [pathname, locale])

  return null
}

export function ogLocaleFor(locale: Locale): string {
  return OG_LOCALE_CODES[locale]
}

export function hreflangFor(locale: Locale): string {
  return HREFLANG_CODES[locale]
}
