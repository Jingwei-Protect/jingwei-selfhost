import type { Locale } from './types'
import { localeUsesLatinJwFields } from './types'
import { deepTraditionalize, localizeText } from './traditionalize'

import * as faqZh from '../content/faq'
import * as faqEn from '../content/en/faq'
import * as legalZh from '../content/legalTerms'
import * as legalEn from '../content/en/legalTerms'
import * as privacyZh from '../content/privacy'
import * as privacyEn from '../content/en/privacy'
import * as jwZh from '../content/jingweiProtocol'
import * as jwEn from '../content/en/jingweiProtocol'
import * as authorLetterZh from '../content/authorLetter'
import * as authorLetterEn from '../content/en/authorLetter'
import * as faqJa from '../content/ja/faq'
import * as legalJa from '../content/ja/legalTerms'
import * as privacyJa from '../content/ja/privacy'
import * as jwJa from '../content/ja/jingweiProtocol'
import * as authorLetterJa from '../content/ja/authorLetter'

import * as matrixZh from '../content/guide/watermarkMatrix'
import * as matrixEn from '../content/en/guide/watermarkMatrix'
import * as matrixJa from '../content/ja/guide/watermarkMatrix'

import * as blogZh from '../content/blog/zh-Hans/posts'
import * as blogEn from '../content/blog/en/posts'
import * as blogJa from '../content/blog/ja/posts'

export function getFaqBundle(locale: Locale) {
  if (locale === 'en') return faqEn
  if (locale === 'ja') return faqJa
  if (locale === 'zh-Hant') return deepTraditionalize(faqZh)
  return faqZh
}

export function getLegalBundle(locale: Locale) {
  if (locale === 'en') return legalEn
  if (locale === 'ja') return legalJa
  if (locale === 'zh-Hant') return deepTraditionalize(legalZh)
  return legalZh
}

export function getPrivacyBundle(locale: Locale) {
  if (locale === 'en') return privacyEn
  if (locale === 'ja') return privacyJa
  if (locale === 'zh-Hant') return deepTraditionalize(privacyZh)
  return privacyZh
}

export function getJwBundle(locale: Locale) {
  if (locale === 'en') return jwEn
  if (locale === 'ja') return jwJa
  if (locale === 'zh-Hant') return deepTraditionalize(jwZh)
  return jwZh
}

export function getAuthorLetterBundle(locale: Locale) {
  if (locale === 'en') return authorLetterEn
  if (locale === 'ja') return authorLetterJa
  if (locale === 'zh-Hant') return deepTraditionalize(authorLetterZh)
  return authorLetterZh
}

export function getMatrixBundle(locale: Locale) {
  if (locale === 'en') return matrixEn
  if (locale === 'ja') return matrixJa
  if (locale === 'zh-Hant') return deepTraditionalize(matrixZh)
  return matrixZh
}

export function getBlogBundle(locale: Locale) {
  if (locale === 'en') return blogEn
  if (locale === 'ja') return blogJa
  if (locale === 'zh-Hant') return deepTraditionalize(blogZh)
  return blogZh
}

export function jwRestrictionLabel(locale: Locale, abbrev: string): string {
  const bundle = getJwBundle(locale)
  const found = bundle.JW_RESTRICTION_FLAGS.find(f => f.abbrev === abbrev)
  if (found) {
    return localeUsesLatinJwFields(locale) ? found.label : found.labelZh
  }
  return bundle.JW_RESTRICTION_LEGACY_LABELS[abbrev] || abbrev
}

export function jwCreationLabel(locale: Locale, id: string): string {
  const opt = getJwBundle(locale).JW_CREATION_OPTIONS.find(o => o.id === id)
  if (!opt) return id
  return localeUsesLatinJwFields(locale) ? opt.label : opt.labelZh
}

export { localizeText }
