import { GUIDE_COMPARE_PAIRS, type GuideComparePair } from '../../guide/showcaseAssets'

export type { GuideComparePair }

export { GUIDE_COMPARE_PAIRS, HOME_SHOWCASE_IDS } from '../../guide/showcaseAssets'

export const MATRIX_CANONICAL = 'https://jwprotect.com/guide/watermark-matrix'
export const MATRIX_DATE_MODIFIED = '2026-08-30'

export const MATRIX_META_TITLE = '可視レイヤー vs AI 洗い落とし実測 | 精卫'
export const MATRIX_META_DESCRIPTION =
  '使用ガイド由来：可視レイヤー「保護後 vs AI 修復試行後」の对比。位移・ハーフトーン・エンボス・ぼかし帯・ぼかし块・ASCII・文字タイル。モアレと顔エンボスは保護ページでプレビュー。'

export const MATRIX_INTRO = {
  title: '可視レイヤー vs AI 洗い落とし実測',
  lead:
    '精卫使用ガイドの对比図：左が加水印後、右が AI による除去・局部修復の試行後（赤枠は問題域）。可視層は原図をきれいに持ち去るコストを上げます。見本は説明用で、自分の絵として使ってはいけません。',
  updated: '2026年8月（对比図を修正）',
  tableCaption: '不可視・追跡レイヤー（文字说明）',
  compareCaption: '可視レイヤー完整对比（ガイドより）',
  colProtected: '精卫加水印後',
  colAiRestored: 'AI 修復試行後',
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
    layer: 'JW 宣言',
    category: 'invisible',
    normalView: '目視不可。検証ページでフッター帯と宣言を読取',
    afterAiWash: '軽い圧縮・スクショは残りやすい。全面再描画では消失の可能性',
    verify: 'partial',
    verifyLabel: '中〜強',
  },
  {
    id: 'dwt',
    layer: 'DWT 周波数透かし',
    category: 'invisible',
    normalView: '不可視。検証ページで署名を抽出',
    afterAiWash: '局部再描画で弱まる。重度では消失',
    verify: 'partial',
    verifyLabel: '中',
  },
  {
    id: 'lsb',
    layer: 'LSB ステガノ',
    category: 'invisible',
    normalView: '不可視。可逆性のない経路に弱い',
    afterAiWash: 'JPEG 再保存・スクショで失われやすい',
    verify: 'weak',
    verifyLabel: '弱〜中',
  },
  {
    id: 'track',
    layer: '追跡アンカー',
    category: 'track',
    normalView: '不可視。切り抜き後もマッチ試行可',
    afterAiWash: '全面再描画で無効化の可能性',
    verify: 'partial',
    verifyLabel: '中',
  },
]

const JA_LAYER_NAMES: Record<string, { layerName: string; note?: string }> = {
  'disp-tile': { layerName: '位移 · 全面タイル', note: 'ずれたピクセルは无痕復元が困難。赤枠は塗り残しや色块。' },
  'disp-scatter': { layerName: '位移 · ランダム分散' },
  'disp-repeat': { layerName: '位移 · 集中文字' },
  'text-tile': { layerName: '文字タイル' },
  emboss: { layerName: 'エンボス纹理' },
  'blur-bar': { layerName: 'ぼかし帯', note: '横方向の半透明帯。人像・納品プレビュー・重要情報向け。' },
  'blur-block': { layerName: 'ぼかし块', note: 'ブラシで塗った块。ぼかし帯とは別レイヤー。' },
  ascii: { layerName: 'ASCII 透かし', note: '画面全体の浅い文字グリッド。モアレと顔エンボスの独立サンプルは保護ページから再出力予定。' },
  halftone: { layerName: 'ハーフトーン网点' },
}

export function getMatrixComparisons(): readonly GuideComparePair[] {
  return GUIDE_COMPARE_PAIRS.map(p => {
    const ja = JA_LAYER_NAMES[p.id]
    if (!ja) return p
    return {
      ...p,
      layerName: ja.layerName,
      note: ja.note ?? p.note,
      protectedAlt: `${ja.layerName} — 保護後`,
      aiRestoredAlt: `${ja.layerName} — AI 修復試行後`,
    }
  })
}

export const MATRIX_FAQ = [
  { q: '赤枠は何を示しますか？', a: 'ガイド标注：AI 修復後に残る塗り残し・色块・構造ずれ・透かし残留です。' },
  { q: '可視レイヤーは検証できますか？', a: '洗い落としコストを上げる用途です。JW / DWT 等の不可視層を併用し、検証ページで確認してください。' },
  { q: 'どの可視層を選べばよいですか？', a: '常用：位移またはハーフトーン + JW + 周波数透かし。ブログ「五种可见层」参照。' },
] as const

export const MATRIX_DISCLAIMER =
  '2026年7月ガイド素材に基づく对比。AI ツールは更新されます。ご自身の作品でプレビュー・検証してください。見本は説明用です（SAMPLES-LICENSE.md）。'

export const MATRIX_CTA = {
  title: '自分の作品で試す',
  body: '約30秒で保護し、検証ページで確認。保護ページでライブプレビューと消しゴム精修が可能です。',
  links: [
    { to: '/protect', label: '作品を保護' },
    { to: '/verify', label: '透かしを検証' },
    { to: '/blog/how-to-use-jingwei-visible-layers', label: '可視レイヤーの選び方' },
    { to: '/faq', label: 'FAQ' },
  ] as const,
}

export const MATRIX_STATUS_LABELS: Record<MatrixVerifyStatus, string> = {
  strong: '強',
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
    isPartOf: { '@type': 'WebSite', name: '精卫', url: 'https://jwprotect.com' },
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
