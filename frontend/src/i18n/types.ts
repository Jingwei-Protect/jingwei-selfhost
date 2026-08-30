export type Locale = 'zh-Hans' | 'zh-Hant' | 'en' | 'ja'

export const LOCALES: Locale[] = ['zh-Hans', 'zh-Hant', 'en', 'ja']

export const LOCALE_LABELS: Record<Locale, string> = {
  'zh-Hans': '简体',
  'zh-Hant': '繁體',
  en: 'EN',
  ja: '日本語',
}

export const LOCALE_HTML_LANG: Record<Locale, string> = {
  'zh-Hans': 'zh-CN',
  'zh-Hant': 'zh-TW',
  en: 'en',
  ja: 'ja',
}

/** JW 协议等使用 label/desc（非 labelZh）字段的语言 */
export function localeUsesLatinJwFields(locale: Locale): boolean {
  return locale === 'en' || locale === 'ja'
}

export function localeDateTag(locale: Locale): string {
  if (locale === 'en') return 'en-US'
  if (locale === 'ja') return 'ja-JP'
  if (locale === 'zh-Hant') return 'zh-TW'
  return 'zh-CN'
}

export function localeListSeparator(locale: Locale): string {
  return locale === 'en' ? ', ' : '、'
}

export function localeSchemaLanguage(locale: Locale): string {
  if (locale === 'en') return 'en'
  if (locale === 'ja') return 'ja'
  if (locale === 'zh-Hant') return 'zh-Hant'
  return 'zh-Hans'
}

export const STORAGE_KEY = 'jingwei-locale'
