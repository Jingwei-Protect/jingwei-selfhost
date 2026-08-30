import { readLocaleFromWindow } from '../lib/i18nSeo'
import type { Locale } from './types'
import { STORAGE_KEY } from './types'

const TRADITIONAL_ZH = new Set(['TW', 'HK', 'MO'])
const SIMPLIFIED_ZH_TZ = new Set(['Asia/Shanghai', 'Asia/Chongqing', 'Asia/Urumqi', 'Asia/Harbin'])
const TRADITIONAL_ZH_TZ = new Set(['Asia/Taipei', 'Asia/Hong_Kong', 'Asia/Macau'])

function isLocale(value: string | null | undefined): value is Locale {
  return value === 'zh-Hans' || value === 'zh-Hant' || value === 'en' || value === 'ja'
}

function localeFromLanguageTag(tag: string): Locale | null {
  const raw = tag.trim().replace(/_/g, '-')
  const lower = raw.toLowerCase()
  if (lower === 'zh-cn' || lower === 'zh-hans' || lower.startsWith('zh-cn')) return 'zh-Hans'
  if (
    lower === 'zh-tw' || lower === 'zh-hk' || lower === 'zh-mo'
    || lower === 'zh-hant' || lower.startsWith('zh-tw')
    || lower.startsWith('zh-hk') || lower.startsWith('zh-mo')
  ) {
    return 'zh-Hant'
  }
  if (lower === 'zh') return localeFromGenericZh()
  if (lower.startsWith('zh-')) return localeFromGenericZh()
  if (lower.startsWith('en')) return 'en'
  if (lower === 'ja' || lower.startsWith('ja-')) return 'ja'
  return null
}

function localeFromGenericZh(): Locale {
  try {
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone
    if (TRADITIONAL_ZH_TZ.has(tz)) return 'zh-Hant'
    if (SIMPLIFIED_ZH_TZ.has(tz)) return 'zh-Hans'
  } catch {
    /* ignore */
  }
  return 'zh-Hans'
}

function navigatorLanguageTags(): string[] {
  return navigator.languages?.length
    ? [...navigator.languages]
    : [navigator.language]
}

/** True when the browser exposes a supported locale in language tags. */
function browserLanguagesIncludeSupported(): boolean {
  for (const tag of navigatorLanguageTags()) {
    if (localeFromLanguageTag(tag)) return true
  }
  return false
}

function localeFromNavigator(): Locale {
  for (const tag of navigatorLanguageTags()) {
    const hit = localeFromLanguageTag(tag)
    if (hit) return hit
  }
  return 'en'
}

function localeFromCountry(country: string | null | undefined): Locale | null {
  const code = (country || '').toUpperCase()
  if (!code) return null
  if (code === 'CN') return 'zh-Hans'
  if (code === 'JP') return 'ja'
  if (TRADITIONAL_ZH.has(code)) return 'zh-Hant'
  return null
}

export function readSavedLocale(): Locale | null {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    return isLocale(saved) ? saved : null
  } catch {
    return null
  }
}

export function saveLocale(locale: Locale): void {
  try {
    localStorage.setItem(STORAGE_KEY, locale)
  } catch {
    /* ignore */
  }
}

/** Browser-only fallback when geo hint is unavailable. */
export function detectLocaleFromBrowser(): Locale {
  const fromUrl = readLocaleFromWindow()
  if (fromUrl) return fromUrl
  return localeFromNavigator()
}

/** Resolve initial locale: URL ?lang= → saved preference → browser language → geo fallback. */
export async function resolveInitialLocale(): Promise<Locale> {
  const fromUrl = readLocaleFromWindow()
  if (fromUrl) return fromUrl

  const saved = readSavedLocale()
  if (saved) return saved

  const browser = detectLocaleFromBrowser()
  if (browserLanguagesIncludeSupported()) return browser

  try {
    const res = await fetch('/api/public/locale-hint', { credentials: 'same-origin' })
    if (res.ok) {
      const data = await res.json() as { locale?: string; country?: string }
      const geo = localeFromCountry(data.country) || (isLocale(data.locale) ? data.locale : null)
      if (geo) return geo
    }
  } catch {
    /* offline / dev without API */
  }

  return browser
}
