import { GUIDE_COMPARE_PAIRS, type GuideComparePair } from '../../guide/showcaseAssets'

export type { GuideComparePair }

export { GUIDE_COMPARE_PAIRS, HOME_SHOWCASE_IDS } from '../../guide/showcaseAssets'

export const MATRIX_CANONICAL = 'https://jwprotect.com/guide/watermark-matrix'
export const MATRIX_DATE_MODIFIED = '2026-08-30'

export const MATRIX_META_TITLE = 'Visible layers vs AI wash-out | Jingwei test matrix'
export const MATRIX_META_DESCRIPTION =
  'From the user guide: visible layers, protected vs AI restoration attempts, with annotated problem areas. Displacement, halftone, emboss, blur bar, blur block, ASCII, tiled text. Moire and face-emboss: preview on Protect until re-exported.'

export const MATRIX_INTRO = {
  title: 'Visible layers vs AI wash-out',
  lead:
    'Side-by-side pairs from the Jingwei user guide: protected (left) vs after an AI watermark-removal / local repair attempt (right). Red boxes mark smears, blocks, or misaligned structure. Samples are documentation only. Do not reuse them as your art.',
  updated: 'August 2026 (sample pairs corrected)',
  tableCaption: 'Invisible & tracking layers (text summary)',
  compareCaption: 'Visible layers — full guide comparisons',
  colProtected: 'After Jingwei protection',
  colAiRestored: 'After AI repair attempt',
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
    layer: 'Jingwei Declaration (JW)',
    category: 'invisible',
    normalView: 'Invisible; Verify reads footer strip and declaration fields',
    afterAiWash: 'Often survives light compression; full AI repaint may remove it',
    verify: 'partial',
    verifyLabel: 'Medium–strong',
  },
  {
    id: 'dwt',
    layer: 'DWT frequency watermark',
    category: 'invisible',
    normalView: 'Invisible; Verify can extract attribution',
    afterAiWash: 'Local repaint may weaken; heavy repaint may erase',
    verify: 'partial',
    verifyLabel: 'Medium',
  },
  {
    id: 'lsb',
    layer: 'LSB steganography',
    category: 'invisible',
    normalView: 'Invisible; sensitive to lossy pipelines',
    afterAiWash: 'JPEG re-save and screenshots often break it',
    verify: 'weak',
    verifyLabel: 'Weak–medium',
  },
  {
    id: 'track',
    layer: 'Tracking anchors',
    category: 'track',
    normalView: 'Invisible; may match after crop/scale',
    afterAiWash: 'Full repaint may break; cropped images may still trace',
    verify: 'partial',
    verifyLabel: 'Medium',
  },
]

const EN_LAYER_NAMES: Record<string, { layerName: string; note?: string }> = {
  'disp-tile': { layerName: 'Displacement · tiled repeat', note: 'Pushed pixels are hard to restore cleanly; red boxes show smears or blocks.' },
  'disp-scatter': { layerName: 'Displacement · scattered chars', note: 'Scattered marks misalign under local repaint.' },
  'disp-repeat': { layerName: 'Displacement · grouped word' },
  'text-tile': { layerName: 'Tiled text overlay' },
  emboss: { layerName: 'Emboss texture', note: 'Not ideal for flat color fills; raises local repair cost.' },
  'blur-bar': { layerName: 'Blur bar', note: 'Horizontal translucent bands; portraits, delivery previews, covering key text.' },
  'blur-block': { layerName: 'Blur block', note: 'Brush-painted patches. Not the same layer as a blur bar.' },
  ascii: { layerName: 'ASCII characters', note: 'Full-frame faint character grid. Moire and face-emboss samples will be re-exported from Protect.' },
  halftone: { layerName: 'Halftone dots', note: 'Fine dots in high frequencies; flattening leaves unnatural patches.' },
}

export function getMatrixComparisons(): readonly GuideComparePair[] {
  return GUIDE_COMPARE_PAIRS.map(p => {
    const en = EN_LAYER_NAMES[p.id]
    if (!en) return p
    return {
      ...p,
      layerName: en.layerName,
      note: en.note ?? p.note,
      protectedAlt: `${en.layerName} — after Jingwei protection`,
      aiRestoredAlt: `${en.layerName} — after AI repair attempt`,
    }
  })
}

export const MATRIX_FAQ = [
  {
    q: 'What do the red boxes mean?',
    a: 'From the user guide: they highlight smears, color blocks, misalignment, or watermark remnants after AI repair.',
  },
  {
    q: 'Can visible layers be verified?',
    a: 'They raise theft and wash-out cost. Add JW / DWT invisible layers and check on Verify.',
  },
  {
    q: 'Which visible layer should I pick?',
    a: 'Common stack: displacement or halftone + JW + frequency watermark. See the blog post on choosing visible layers.',
  },
] as const

export const MATRIX_DISCLAIMER =
  'Images from July 2026 guide material and internal tests. AI tools change: preview on Protect and verify your own files. Samples are documentation only (SAMPLES-LICENSE.md).'

export const MATRIX_CTA = {
  title: 'Try it on your work',
  body: 'Protect in about 30 seconds, then verify. Live preview and eraser refinement on the Protect page.',
  links: [
    { to: '/protect', label: 'Protect a work' },
    { to: '/verify', label: 'Verify watermark' },
    { to: '/blog/how-to-use-jingwei-visible-layers', label: 'Choose visible layers' },
    { to: '/faq', label: 'FAQ' },
  ] as const,
}

export const MATRIX_STATUS_LABELS: Record<MatrixVerifyStatus, string> = {
  strong: 'Strong',
  partial: 'Medium',
  weak: 'Weak',
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
    isPartOf: { '@type': 'WebSite', name: 'Jingwei', url: 'https://jwprotect.com' },
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
