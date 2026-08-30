import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import {
  getAuthorLetterBundle,
  getBlogBundle,
  getFaqBundle,
  getJwBundle,
  getLegalBundle,
  getMatrixBundle,
  getPrivacyBundle,
  localizeText,
} from './contentBridge'
import { replaceLocaleInUrl } from '../lib/i18nSeo'
import { detectLocaleFromBrowser, resolveInitialLocale, saveLocale } from './detectLocale'
import { getMessages, type Messages } from './messages'
import type { Locale } from './types'
import { LOCALE_HTML_LANG } from './types'

interface LocaleContextValue {
  locale: Locale
  messages: Messages
  faq: ReturnType<typeof getFaqBundle>
  authorLetter: ReturnType<typeof getAuthorLetterBundle>
  legal: ReturnType<typeof getLegalBundle>
  privacy: ReturnType<typeof getPrivacyBundle>
  jw: ReturnType<typeof getJwBundle>
  matrix: ReturnType<typeof getMatrixBundle>
  blog: ReturnType<typeof getBlogBundle>
  t: (zhHans: string, en: string) => string
  setLocale: (locale: Locale) => void
  ready: boolean
}

const LocaleContext = createContext<LocaleContextValue | null>(null)

export function LocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(() => detectLocaleFromBrowser())
  const [ready, setReady] = useState(false)

  useEffect(() => {
    let cancelled = false
    void resolveInitialLocale().then(resolved => {
      if (!cancelled) {
        setLocaleState(resolved)
        setReady(true)
      }
    })
    return () => {
      cancelled = true
    }
  }, [])

  const setLocale = useCallback((next: Locale) => {
    saveLocale(next)
    setLocaleState(next)
    replaceLocaleInUrl(next)
  }, [])

  useEffect(() => {
    document.documentElement.lang = LOCALE_HTML_LANG[locale]
  }, [locale])

  const value = useMemo((): LocaleContextValue => {
    const t = (zhHans: string, en: string, ja?: string) => localizeText(locale, zhHans, en, ja)
    return {
      locale,
      messages: getMessages(locale),
      faq: getFaqBundle(locale),
      authorLetter: getAuthorLetterBundle(locale),
      legal: getLegalBundle(locale),
      privacy: getPrivacyBundle(locale),
      jw: getJwBundle(locale),
      matrix: getMatrixBundle(locale),
      blog: getBlogBundle(locale),
      t,
      setLocale,
      ready,
    }
  }, [locale, ready, setLocale])

  return (
    <LocaleContext.Provider value={value}>
      {children}
    </LocaleContext.Provider>
  )
}

export function useLocale(): LocaleContextValue {
  const ctx = useContext(LocaleContext)
  if (!ctx) {
    throw new Error('useLocale must be used within LocaleProvider')
  }
  return ctx
}
