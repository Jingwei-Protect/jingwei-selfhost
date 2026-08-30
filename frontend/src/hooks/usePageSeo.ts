import { useEffect } from 'react'
import { usePageMeta } from './usePageMeta'

const DEFAULT_CANONICAL = 'https://jwprotect.com/'

/**
 * 设置页面 title、meta description 与 canonical URL。
 * 离开页面时恢复进入前的 canonical。
 */
export function usePageSeo(options: {
  title: string
  description?: string
  canonical: string
  robots?: string
}) {
  const { title, description, canonical, robots } = options
  usePageMeta(title, description, robots)

  useEffect(() => {
    let link = document.querySelector<HTMLLinkElement>('link[rel="canonical"]')
    const prevCanonical = link?.href ?? ''
    if (!link) {
      link = document.createElement('link')
      link.rel = 'canonical'
      document.head.appendChild(link)
    }
    link.href = canonical

    return () => {
      if (link) link.href = prevCanonical || DEFAULT_CANONICAL
    }
  }, [canonical])
}
