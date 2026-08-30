import * as OpenCC from 'opencc-js'
import type { Locale } from './types'

const converter = OpenCC.Converter({ from: 'cn', to: 'tw' })

export function toTraditional(text: string): string {
  return converter(text)
}

export function localizeText(locale: Locale, zhHans: string, en: string, ja?: string): string {
  if (locale === 'ja') return ja ?? en
  if (locale === 'en') return en
  if (locale === 'zh-Hant') return toTraditional(zhHans)
  return zhHans
}

export function deepTraditionalize<T>(value: T): T {
  if (typeof value === 'string') return toTraditional(value) as T
  if (Array.isArray(value)) return value.map(deepTraditionalize) as T
  if (value && typeof value === 'object') {
    const out: Record<string, unknown> = {}
    for (const [k, v] of Object.entries(value)) {
      out[k] = deepTraditionalize(v)
    }
    return out as T
  }
  return value
}
