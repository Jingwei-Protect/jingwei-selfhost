import type { Locale } from '../types'
import { deepTraditionalize } from '../traditionalize'
import en from './en/index'
import ja from './ja/index'
import type { Messages } from './types'
import zhHans from './zh-Hans/index'

const CATALOG: Record<Locale, Messages> = {
  'zh-Hans': zhHans,
  'zh-Hant': deepTraditionalize(zhHans),
  en,
  ja,
}

export function getMessages(locale: Locale): Messages {
  return CATALOG[locale] ?? zhHans
}

export type { Messages }
