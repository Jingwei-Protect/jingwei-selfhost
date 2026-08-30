import { GUIDE_COMPARE_PAIRS, type GuideComparePair } from './showcaseAssets'

export type { GuideComparePair }

export { GUIDE_COMPARE_PAIRS, HOME_SHOWCASE_IDS } from './showcaseAssets'

export const MATRIX_CANONICAL = 'https://jwprotect.com/guide/watermark-matrix'
export const MATRIX_DATE_MODIFIED = '2026-08-30'

export const MATRIX_META_TITLE = '各层水印 vs AI 洗图实测 | 精卫 Jingwei'
export const MATRIX_META_DESCRIPTION =
  '使用指南实测：可见层「加水印后 vs AI 试图修复后」对比图。位移、半调、浮雕、模糊条、模糊块、ASCII、平铺文字。摩尔纹与脸部浮雕锁请在保护页预览。'

export const MATRIX_INTRO = {
  title: '各层水印 vs AI 洗图实测',
  lead:
    '以下对比图均来自精卫使用指南：左列为加水印后的效果，右列为 AI 试图去水印 / 局部修复后的效果（红框标注问题区域）。可见层用来抬高还原原图的成本。样图仅供说明，禁止当自己的图使用。',
  updated: '2026 年 8 月更正配图',
  tableCaption: '隐形层与追踪层（文字说明）',
  compareCaption: '可见层完整对比（来自使用指南）',
  colProtected: '精卫加水印效果',
  colAiRestored: 'AI 试图修复后效果',
}

export type MatrixVerifyStatus = 'strong' | 'partial' | 'weak' | 'na'

export interface MatrixTableRow {
  id: string
  layer: string
  category: 'invisible' | 'visible' | 'track'
  normalView: string
  afterAiWash: string
  verify: MatrixVerifyStatus
  verifyLabel: string
}

export const MATRIX_TABLE: MatrixTableRow[] = [
  {
    id: 'jw',
    layer: '精卫声明 JW',
    category: 'invisible',
    normalView: '肉眼不可见；验证页可读页脚条与声明字段',
    afterAiWash: '轻度压缩、截图通常仍在；全图 AI 重绘可能抹掉',
    verify: 'partial',
    verifyLabel: '中–强（视攻击强度）',
  },
  {
    id: 'dwt',
    layer: 'DWT 频域水印',
    category: 'invisible',
    normalView: '不可见；验证页可提取署名信息',
    afterAiWash: '局部重绘可能削弱；重度重绘可能丢失',
    verify: 'partial',
    verifyLabel: '中（抗压缩较好）',
  },
  {
    id: 'lsb',
    layer: 'LSB 隐写',
    category: 'invisible',
    normalView: '不可见；对无损链路较敏感',
    afterAiWash: 'JPEG 重存、截图后易失效',
    verify: 'weak',
    verifyLabel: '弱–中（需无损链路）',
  },
  {
    id: 'track',
    layer: '追踪锚点',
    category: 'track',
    normalView: '不可见；裁剪/缩放后仍可尝试匹配',
    afterAiWash: '全图重绘可能失效；裁切图可能仍可追踪',
    verify: 'partial',
    verifyLabel: '中（视裁剪与重绘范围）',
  },
]

/** 可见层：与 GUIDE_COMPARE_PAIRS 一一对应 */
export function getMatrixComparisons(): readonly GuideComparePair[] {
  return GUIDE_COMPARE_PAIRS
}

export const MATRIX_FAQ = [
  {
    q: '对比图里的红框是什么？',
    a: '来自使用指南标注：指出 AI 试图修复后仍留下的涂抹、色块、结构错位或水印残留区域。',
  },
  {
    q: '可见层能「验证」吗？',
    a: '可见层主要提高盗用与洗图成本。归属验证请叠加 JW / DWT 等隐形层，并在验证页自检。',
  },
  {
    q: '怎么选可见层？',
    a: '常用组合：位移或半调 + JW + 频域水印。人像可加模糊条或脸部浮雕锁。详见博客《精卫怎么用：五种可见层怎么选》。',
  },
] as const

export const MATRIX_DISCLAIMER =
  '对比图来自 2026 年 7 月内部测试与使用指南素材；AI 工具更新后表现可能变化。请对你自己的作品在保护页预览、验证页实测。样图仅供说明，禁止当自己的图使用（SAMPLES-LICENSE.md）。'

export const MATRIX_CTA = {
  title: '想亲自试一张？',
  body: '上传作品约 30 秒完成保护，再到验证页检查。保护页支持实时预览与橡皮擦精修。',
  links: [
    { to: '/protect', label: '开始保护作品' },
    { to: '/verify', label: '验证水印' },
    { to: '/blog/how-to-use-jingwei-visible-layers', label: '五种可见层怎么选' },
    { to: '/faq', label: '常见问题' },
  ] as const,
}

export const MATRIX_STATUS_LABELS: Record<MatrixVerifyStatus, string> = {
  strong: '强',
  partial: '中',
  weak: '弱',
  na: '—',
}

export function buildMatrixJsonLd(): Record<string, unknown> {
  return {
    '@context': 'https://schema.org',
    '@type': 'WebPage',
    name: MATRIX_INTRO.title,
    description: MATRIX_META_DESCRIPTION,
    url: MATRIX_CANONICAL,
    dateModified: MATRIX_DATE_MODIFIED,
    inLanguage: ['zh-Hans', 'zh-Hant', 'en', 'ja'],
    isPartOf: { '@type': 'WebSite', name: '精卫 Jingwei', url: 'https://jwprotect.com' },
    mainEntity: {
      '@type': 'FAQPage',
      mainEntity: MATRIX_FAQ.map(item => ({
        '@type': 'Question',
        name: item.q,
        acceptedAnswer: { '@type': 'Answer', text: item.a },
      })),
    },
  }
}
