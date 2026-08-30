import { useEffect } from 'react'

function upsertMeta(name: string, content: string) {
  let el = document.querySelector<HTMLMetaElement>(`meta[name="${name}"]`)
  if (!el) {
    el = document.createElement('meta')
    el.setAttribute('name', name)
    document.head.appendChild(el)
  }
  el.content = content
}

/** 更新浏览器标签标题与 meta description（无需额外依赖） */
export function usePageMeta(title: string, description?: string, robots?: string) {
  useEffect(() => {
    document.title = title
    if (description) upsertMeta('description', description)
    if (robots) upsertMeta('robots', robots)
  }, [title, description, robots])
}
