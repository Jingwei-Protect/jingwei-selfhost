import { Link } from 'react-router-dom'
import { useLocale } from '../i18n/LocaleContext'
import { usePageMeta } from '../hooks/usePageMeta'

export default function HomePage() {
  const { locale, messages: m } = useLocale()
  const zh = locale.startsWith('zh')
  usePageMeta(
    zh ? '精卫自托管 · 保护与验证' : 'Jingwei self-host · Protect & Verify',
    zh
      ? '在自己电脑上运行精卫：保护图片、验证声明。图不会发到 jwprotect.com。'
      : 'Run Jingwei on your machine: protect images and verify marks. Nothing is sent to jwprotect.com.',
  )
  return (
    <div className="page-home container" style={{ padding: '2rem 1rem 4rem' }}>
      <p className="text-sm" style={{ opacity: 0.7 }}>
        {zh ? '这不是官网。官网：' : 'This is not the official website. Official tool: '}
        <a href="https://jwprotect.com">jwprotect.com</a>
      </p>
      <h1 className="am-display" style={{ marginTop: '1rem' }}>
        {m.common.siteName}
      </h1>
      <p style={{ maxWidth: 640, lineHeight: 1.7 }}>
        {zh
          ? '本仓库是自己电脑上的保护 + 验证。用 Docker 启动后，图片留在本机。'
          : 'This repository is Protect + Verify on your computer. After Docker starts, images stay local.'}
      </p>
      <p style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginTop: '1.5rem' }}>
        <Link className="btn btn-primary" to="/protect">{zh ? '去保护' : 'Protect'}</Link>
        <Link className="btn btn-secondary" to="/verify">{zh ? '去验证' : 'Verify'}</Link>
        <Link className="btn btn-secondary" to="/guide/watermark-matrix">{zh ? '图层对照' : 'Layer matrix'}</Link>
      </p>
      <p className="text-sm" style={{ marginTop: '1rem', maxWidth: 640, lineHeight: 1.7, opacity: 0.8 }}>
        {zh
          ? '如果精卫对你有用，可以支持官方（打赏给精卫，不是给这台电脑的部署者）：'
          : 'If Jingwei is useful, you can support the official project (not whoever is running this machine): '}
        <a href="https://ko-fi.com/jingwei2026" target="_blank" rel="noreferrer">
          {zh ? 'Ko-fi 支持精卫' : 'Support Jingwei on Ko-fi'}
        </a>
      </p>
      <h2 style={{ marginTop: '3rem' }}>{zh ? '署名·快速：狗（纹理）' : 'Quick Credit: puppy (texture)'}</h2>
      <p className="text-sm" style={{ maxWidth: 720, lineHeight: 1.65 }}>
        Auto sees fur/flowers as texture, so it nudges host pixels into the name (not a pasted color stamp).
        {' '}自动把毛发和花瓣当成纹理，用轻位移把署名写进像素里，不是贴一层色块。
      </p>
      <p style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <img src="/showcase/credit/credit-dog-before.png" alt="Puppy before" style={{ maxWidth: '48%', height: 'auto' }} />
        <img src="/showcase/credit/credit-dog-after.png" alt="Puppy after" style={{ maxWidth: '48%', height: 'auto' }} />
      </p>
      <img src="/showcase/credit/credit-dog-where.png" alt="Where the mark sits" style={{ maxWidth: '100%', height: 'auto' }} />
      <h2 style={{ marginTop: '3rem' }}>{zh ? '署名·快速：猫（平涂）' : 'Quick Credit: cat (flat color)'}</h2>
      <p className="text-sm" style={{ maxWidth: 720, lineHeight: 1.65 }}>
        Flat color fields get a very light full-frame speckle plus a faint dotted name. From far away it still reads as the painting.
        {' '}平涂走浅字符：远看还是原画，近看才有浅网点。
      </p>
      <p style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <img src="/showcase/credit/credit-cat-before.png" alt="Cat before" style={{ maxWidth: '48%', height: 'auto' }} />
        <img src="/showcase/credit/credit-cat-after.png" alt="Cat after" style={{ maxWidth: '48%', height: 'auto' }} />
      </p>
      <img src="/showcase/credit/credit-cat-where.png" alt="Where the signature sits" style={{ maxWidth: '100%', height: 'auto' }} />
      <p className="text-sm" style={{ marginTop: '2rem', opacity: 0.75 }}>
        {zh
          ? '样图仅供说明，不能当自己的作品用。详见仓库 SAMPLES-LICENSE.md。'
          : 'Sample images are documentation only — not your art. See SAMPLES-LICENSE.md.'}
      </p>
    </div>
  )
}
