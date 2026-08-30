/** Guide / matrix compare pairs: protected vs AI repair attempt.

Filenames on disk were assigned before a visual audit (2026-08-30).
Map by *what the pixels show*, not by the filename:

- ``ascii-*`` = red horizontal bars with the word jingwei → blur **bar**
- ``dots-*`` = green/purple brush smudges → blur **block**
- ``moire-*`` = full-frame grid / character field → ASCII
- ``blur-block-*`` = unprotected puppy (no blur) → do not use
- ``blur-bar-*`` = tiled jingwei text → not a face lock; unused until re-exported
*/
export interface GuideComparePair {
  id: string
  layerName: string
  protectedSrc: string
  aiRestoredSrc: string
  protectedAlt: string
  aiRestoredAlt: string
  note?: string
}

const BASE = '/showcase/guide'

export const GUIDE_COMPARE_PAIRS: readonly GuideComparePair[] = [
  {
    id: 'disp-tile',
    layerName: '位移水印 · 铺满重复',
    protectedSrc: `${BASE}/disp-repeat-protected.png`,
    aiRestoredSrc: `${BASE}/disp-repeat-ai-restored.png`,
    protectedAlt: '位移水印铺满重复 — 精卫加水印效果',
    aiRestoredAlt: '位移水印铺满重复 — AI 试图修复后（红框标注残留与失真）',
    note: 'AI 抹除署名时，被推歪的像素结构难以无痕还原，红框处易留涂抹或色块。',
  },
  {
    id: 'disp-scatter',
    layerName: '位移水印 · 随机分散',
    protectedSrc: `${BASE}/disp-scatter-protected.png`,
    aiRestoredSrc: `${BASE}/disp-scatter-ai-restored.png`,
    protectedAlt: '位移水印随机分散 — 精卫加水印效果',
    aiRestoredAlt: '位移水印随机分散 — AI 试图修复后',
    note: '字符打散后，局部重绘更难对齐原图纹理。',
  },
  {
    id: 'disp-repeat',
    layerName: '位移水印 · 集中整词',
    protectedSrc: `${BASE}/disp-tile-protected.png`,
    aiRestoredSrc: `${BASE}/disp-tile-ai-restored.png`,
    protectedAlt: '位移水印集中整词 — 精卫加水印效果',
    aiRestoredAlt: '位移水印集中整词 — AI 试图修复后',
  },
  {
    id: 'text-tile',
    layerName: '平铺文字',
    protectedSrc: `${BASE}/text-tile-protected.png`,
    aiRestoredSrc: `${BASE}/text-tile-ai-restored.png`,
    protectedAlt: '平铺文字可见层 — 精卫加水印效果',
    aiRestoredAlt: '平铺文字 — AI 试图修复后',
  },
  {
    id: 'emboss',
    layerName: '浮雕纹理',
    protectedSrc: `${BASE}/emboss-protected.png`,
    aiRestoredSrc: `${BASE}/emboss-ai-restored.png`,
    protectedAlt: '浮雕纹理 — 精卫加水印效果',
    aiRestoredAlt: '浮雕纹理 — AI 试图修复后',
    note: '全图轻微立体斜线纹；不太适合极简平涂，但可抬高 AI 局部修复成本。',
  },
  {
    id: 'blur-bar',
    layerName: '模糊条',
    protectedSrc: `${BASE}/ascii-protected.png`,
    aiRestoredSrc: `${BASE}/ascii-ai-restored.png`,
    protectedAlt: '模糊条 — 精卫加水印效果',
    aiRestoredAlt: '模糊条 — AI 试图修复后',
    note: '横向半透明条带，适合人像、交付预览、挡住关键信息。',
  },
  {
    id: 'blur-block',
    layerName: '模糊块',
    protectedSrc: `${BASE}/dots-protected.png`,
    aiRestoredSrc: `${BASE}/dots-ai-restored.png`,
    protectedAlt: '模糊块 — 精卫加水印效果',
    aiRestoredAlt: '模糊块 — AI 试图修复后',
    note: '画笔涂抹的色块模糊，和「一条模糊带」不是同一层。',
  },
  {
    id: 'ascii',
    layerName: 'ASCII 水印',
    protectedSrc: `${BASE}/moire-protected.png`,
    aiRestoredSrc: `${BASE}/moire-ai-restored.png`,
    protectedAlt: 'ASCII 字符可见层 — 精卫加水印效果',
    aiRestoredAlt: 'ASCII 水印 — AI 试图修复后',
    note: '满屏浅字符网格。摩尔纹、脸部浮雕锁请在保护页预览，矩阵样图待单独重导。',
  },
  {
    id: 'halftone',
    layerName: '半调网点',
    protectedSrc: `${BASE}/halftone-protected.png`,
    aiRestoredSrc: `${BASE}/halftone-ai-restored.png`,
    protectedAlt: '半调网点 — 精卫加水印效果',
    aiRestoredAlt: '半调网点 — AI 试图修复后',
    note: '细点压进背景高频；AI 平坦化后常留不自然块面。',
  },
] as const

/** 首页精选：浮雕 + 位移集中整词 + 位移铺满（三列并排） */
export const HOME_SHOWCASE_IDS = ['emboss', 'disp-repeat', 'disp-tile'] as const

export function getGuidePair(id: string): GuideComparePair | undefined {
  return GUIDE_COMPARE_PAIRS.find(p => p.id === id)
}
