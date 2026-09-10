/** Jingwei Protocol — copy, flag glossary, story, limits, belief, and letters. */

import { SITE_URL } from '../lib/site'

export const JW_PROTOCOL_CANONICAL = `${SITE_URL}/protocol`
export const JW_PROTOCOL_META_DESCRIPTION =
  '精卫声明 JW：机器可读的图像归属与使用意愿，频域隐形水印，创作类型与 NO-TR/NO-ED 限制，与 CC 及 C2PA 的关系。'
export const JW_PROTOCOL_DATE_MODIFIED = '2026-06-14'

// ─── CC 符号与共识语言 ─────────────────────────────────────────────

export const JW_CC_SYMBOL_HISTORY = {
  kicker: 'Before JW',
  title: '从 © 到 CC：符号如何改变使用方式',
  lead: '在 JW 之前，人类已经用符号把「可以怎么用」这件事，说清楚了整整一代人。',
  paragraphs: [
    '版权符号 © 最早来自印刷时代——它告诉读者：这页文字有主人。但「禁止一切」之外，创作者还需要一种方式说：「你可以用，但要署名」「可以分享，但不能改图卖钱」。',
    '2002 年，Creative Commons（CC）把这套意愿做成了一组全球通用的图标：BY、NC、ND、SA……不必读法律条文，看一眼徽章，就知道作者开放了什么、保留了什么。',
    '这套符号很快改变了生态：Flickr 可以按 CC 筛选、维基百科默认开放、搜索引擎能识别授权类型、转载时有了统一的署名格式。当足够多的人采用同一套符号，平台就有了依据——可以显示授权、可以拦截越界使用、可以在「使用前」而不是「侵权后」做出判断。',
    '共识的力量在于规模：单独一张图上的声明很脆弱，当成千上万张图都写着同一种语言，工具、平台与使用者就会开始默认尊重它。',
    'AI 时代出现了新的空白：作品被截图、重编码、送进训练集时，文件旁的 CC 标签会消失；我们需要一种写进像素、机器读得到、还能跟着图像一起被转发的声明。JW 延续的是同一条路——用可见的符号形成共识，用隐形的编码让共识在传播中留下来。',
  ],
}

// ─── 精卫填海故事（单一来源，避免 SHORT + FULL 重复渲染）────────────────

export type JwStoryParagraph = { text: string; lead?: boolean }

export const JW_STORY_ZH: JwStoryParagraph[] = [
  { text: `中国传说里，一位名叫精卫的少女溺于浩瀚的东海，化身为鸟——渺小如一片羽毛，意志却坚不可摧。` },
  { text: `她誓以一山一石填平大海，使其不再伤人。日复一日，她衔起一颗石子，投入那怒吼的波涛。` },
  { text: `今日，海换了形态——它是无尽的数据之流，是未经询问就被复制、改图、再传播，一路被抹去出处的作品。面对这道新的海，我们或许和精卫一样渺小。` },
  {
    text: `JW 就是你投下的那颗石子——一枚水印，一份机器读得到的归属声明。单独一颗看似微不足道；但我们持之以恒地一起投下，终能让这片海重新有了边界，容得下每一位创作者的姓名。`,
    lead: true,
  },
]

/** 单行摘要（meta、卡片预览等），取自第一段，勿与正文段落叠用。 */
export const JW_STORY_TEASER_ZH = JW_STORY_ZH[0].text

export const JW_STORY = [
  `In Chinese legend, a young girl named Jingwei drowned in the vast East Sea and was reborn as a bird—tiny as a feather, yet unbreakable in will.`,
  `She vowed to fill the sea with mountain stones so it could never harm anyone again. Day after day, she carried one stone and cast it into the roaring waves.`,
  `Today the sea has changed form. It is now an endless flood of data: works copied, altered, and redistributed without consent, with attribution erased along the way. Facing this new sea, we may feel as small as Jingwei.`,
  `JW is your stone—a watermark and a machine-readable ownership declaration. One stone looks small. But if enough creators keep throwing stones together, this sea can regain boundaries, with room for every creator's name.`,
]

export const JW_STORY_TEASER = JW_STORY[0]

/** @deprecated 使用 JW_STORY_ZH */
export const JW_STORY_FULL_ZH = JW_STORY_ZH

/** @deprecated 使用 JW_STORY_TEASER_ZH，勿与 JW_STORY_ZH 同页叠用 */
export const JW_STORY_SHORT_ZH = JW_STORY_TEASER_ZH

/** @deprecated 使用 JW_STORY */
export const JW_STORY_FULL = JW_STORY

/** @deprecated 使用 JW_STORY_TEASER */
export const JW_STORY_SHORT = JW_STORY_TEASER

// ─── 創作類型 ─────────────────────────────────────────────────────

export type JwCreationType = 'OC' | 'AI'

export const JW_CREATION_OPTIONS: { id: JwCreationType; label: string; labelZh: string; desc: string; descZh: string }[] = [
  {
    id: 'OC',
    label: 'OC — Original Creation',
    labelZh: '原创作品',
    desc: 'This work is originally created by the named human creator (any medium).',
    descZh: '本作品由署名创作者独立创作（不限创作媒介）。',
  },
  {
    id: 'AI',
    label: 'AI — AI-Assisted',
    labelZh: 'AI 协作',
    desc: 'AI tools were used in the process; the human creator retains authorship and sets the restrictions.',
    descZh: '创作过程使用了 AI 工具辅助；人类创作者仍为著作权人，并设定使用限制。',
  },
]

// ─── 使用限制（精簡到 2 枚核心旗標）─────────────────────────────

/**
 * 設計考量：
 *
 * - 原本後端有 5 枚旗標（NO-TR / NO-ED / NO-RM / NO-RX / NO-NC），但 NO-RM 屬於同義反覆
 *   （違反協議者本來就違規）、NO-RX 與 NO-NC 屬於傳統著作權概念，會稀釋「為 AI 時代而生」
 *   的訊息，也讓徽章變長。
 * - 因此使用者面對的、徽章上展示的、協議頁說明的，只保留 2 枚直擊 AI 時代痛點的旗標：
 *     · NO-TR — 禁止 AI 訓練
 *     · NO-ED — 禁止 AI 改圖
 * - 後端 bit 位保留不動（向後相容已嵌入舊圖的 payload）。驗證舊圖若帶有其它三枚旗標，
 *   仍會透過 `JW_RESTRICTION_LEGACY_LABELS` 顯示中文名，方便閱讀。
 */
export const JW_RESTRICTION_FLAGS: {
  id: string
  bit: number
  abbrev: string
  label: string
  labelZh: string
  desc: string
  descZh: string
}[] = [
  {
    id: 'NO-TR',
    bit: 0,
    abbrev: 'NO-TR',
    label: 'No AI Training',
    labelZh: '未授权 AI 训练',
    desc: 'The creator has not authorized this image for AI model training or fine-tuning.',
    descZh: '创作者未授权将此图像用于训练或微调 AI 模型。',
  },
  {
    id: 'NO-ED',
    bit: 1,
    abbrev: 'NO-ED',
    label: 'No AI Edit',
    labelZh: '未授权 AI 改图',
    desc: 'The creator has not authorized AI-based modification of this image (inpainting, img2img, full redraw, etc.). Human study or imitation is not covered by this flag.',
    descZh: '创作者未授权使用 AI 工具修改此图像（如 inpainting、img2img、整图重绘等）。人类的临摹与学习不在此限。',
  },
]

/** 旧版旗标的中文展示名（仅供验证页显示已嵌入的旧图，新建图不再使用）。 */
export const JW_RESTRICTION_LEGACY_LABELS: Record<string, string> = {
  'NO-RM': '禁止去除水印（旧）',
  'NO-RX': '禁止衍生创作（旧）',
  'NO-NC': '禁止商业使用（旧）',
}

/** 取得限制縮寫對應的中文標籤（含新版 + 舊版相容）。 */
export function jwRestrictionLabel(abbrev: string): string {
  const found = JW_RESTRICTION_FLAGS.find(f => f.abbrev === abbrev)
  if (found) return found.labelZh
  return JW_RESTRICTION_LEGACY_LABELS[abbrev] || abbrev
}

// ─── 介紹文案 ─────────────────────────────────────────────────────

export const JW_PROTECT_INTRO = `启用精卫声明，将你的创作归属与使用意愿嵌入图像——包括隐形频域水印与可选的可见徽章。创作者姓名来自下方「版权元数据」栏位，会写入 manifest 和文件元数据。建议输出 PNG 以保留隐形水印层。`

export const JW_PROTECT_PIXEL_REWARD = {
  title: '保护作品，提升精卫之海每日配额',
  bullets: [
    '登录后，每成功为一张图完成 JW 声明保护，都会计入你的 JW 作品数。',
    '首次启用：每日可领取从 10 格提升至 50 格。',
    '每多保护一张：每日可再 +5 格，上限 150 格/天。',
    '到「精卫之海」点击「领取今日配额」即可到账（每天一次）。',
  ],
  loginHint: '未登录也可保护图片，但不会累计配额——请先登录账号。',
}

export const JW_PNG_HINT = `启用 JW 声明时建议选择 PNG 格式。JPEG 压缩可能削弱隐形水印层。`

/** 保护页 · 手动调节说明（统一用语：叠加可见层） */
export const JW_STEALTH_MODE_HINT =
  '自己逐项开关每一层并调参数。不自动套配方。Logo 可自调位置、大小、深浅。'

// ─── 保护限度（诚实说明）─────────────────────────────────────────

export const JW_PROTECT_LIMITS = {
  title: '关于这层保护能做什么、不能做什么',
  paragraphs: [
    '精卫声明会在你的图像中嵌入一份机器读得到的归属与意愿——创作者署名、创作类型与使用偏好都写在频域之中，肉眼几乎看不见。它的设计目标是抵抗常见的社群媒体压缩、截图与轻度编辑，让作品在被转发、转存的过程中仍能被辨识。',
  ],
  bullets: [
    {
      strong: '它不是绝对的锁。',
      body: '任何隐形水印都可能被高强度的重绘、深度修补或专门设计的去除工具削弱甚至清除。我们持续优化抗性，但无法承诺 100% 留存。',
    },
    {
      strong: '若你的目标是「现在就让人不敢盗用」，',
      body: '仅靠隐形层是不够的。若要自己配层，请改用手动调节并叠加可见层（位移水印、脸部浮雕锁、浮雕纹理等），尤其是会影响主体轮廓的水印——让擅自取用的人必须付出明显的还原成本，才有劝退效果。',
    },
  ],
}

export const JW_DWT_RELATION = {
  protectHint:
    '精卫声明会在有细节的区域写入隐形信息，大色块底色会尽量保持原样；写入失败时会自动尝试备用方式。建议输出 PNG。',
  verifyJwNote:
    '频域归属信息已通过精卫声明检出；本图未使用单独的 DWT 追踪层。',
  verifyStandaloneDwtTitle: 'DWT 频域水印',
  verifyStandaloneDwtHint:
    '机器可读的独立追踪文字层，与精卫声明的归属 manifest 分开设置。',
}

export type JwImageKind = 'flat' | 'mixed' | 'rich'

export type JwWriteHint = {
  kind: JwImageKind
  flat_ratio: number
  texture_ratio: number
  summary: string
  suggest: string
  credit_disp_x?: number
  credit_disp_y?: number
  credit_disp_w?: number
  credit_disp_h?: number
}

export const JW_INVISIBLE_INTRO =
  '系统会在不易看出变化的区域自动写入精卫声明；大色块较多的图建议开启底部白边并选用 PNG。'

/** @deprecated API always uses auto; kept for typing legacy responses */
export type JwEmbedPriority = 'auto' | 'color' | 'balanced' | 'verify'

export const JW_EMBED_METHOD_LABEL: Record<string, string> = {
  invisible: '隐形写入',
  lsb: '备用写入',
}

// ─── 驗證限度（誠實說明）─────────────────────────────────────────

export const JW_VERIFY_LIMITS = {
  title: '关于验证结果的可信度',
  paragraphs: [
    '本页面会尝试从你上传的图像中提取所有精卫保护层，并读取文件中的 C2PA Content Credentials（若存在）。若检出，代表这张图确实经精卫声明处理过，或携带可验证的来源凭证，可作为创作者署名与权属主张的辅助佐证。',
  ],
  bullets: [
    {
      strong: '未检出 ≠ 一定没被处理过。',
      body: '强度足够的全图重绘（例如整图重生成、深度修补）会在像素层面重建图像，这类操作会把绝大多数隐形水印一并抹去。我们无法为已被这样处理过的图像保留证据。',
    },
    {
      strong: '检出有置信度差异。',
      body: '高置信度且完整解码（含 checksum）可信度最高；C2PA 密码学签名可信度高于频域水印；模糊匹配仅供参考。遇到争议时，仍须结合元数据、创作过程记录、原始文件等其他证据。',
    },
  ],
}

export const JW_C2PA_NOTE = {
  title: 'C2PA 与精卫',
  bullets: [
    {
      strong: '互补关系。',
      body: 'C2PA 写在文件 metadata，社媒转发易丢失；精卫 JW 写在像素频域，两者可并存、互为补充。验证时 C2PA 优先、JW 兜底。',
    },
    {
      strong: '受信证书。',
      body: '若要让 Adobe / 社交平台显示「Content Credentials」，通常需要受信 CA 颁发的 C2PA 或 CAWG 身份证书；开发测试可用工具自带测试证书，浏览器与平台不一定信任。',
    },
  ],
}

// ─── 為何要做（核心信念）─────────────────────────────────────────

export const JW_CORE_BELIEF = {
  title: '为什么仍然值得嵌入「精卫声明」水印',
  paragraphs: [
    '隐形水印不是不会被破坏的锁。AI 重绘、深度修补、强压缩和去水印工具，都可能削弱甚至抹掉它。仅靠隐形水印，无法保证作品在所有传播和二次处理后都留存标记，所以我们推荐叠加可见声明层。',
    '精卫更重要的目标，是推动统一、机器可读的创作者声明。创作者的「拒绝训练」「拒绝 AI 改图」若只写在简介、主页或图内文字里，往往缺乏统一、机器可读的格式，平台和模型很难在规模上稳定识别并执行，因此这些意愿很少像 CC 授权那样被写进可自动遵守的规则。我们希望精卫声明符号像 CC 授权符号一样，逐步被平台、搜索引擎和 AI 模型接纳，成为可读取、可尊重的公共标记。我们深知单靠防御很难追上 AI 的迭代，只有让创作者意愿被平台接纳，才更可能从根源上减少侵权。',
    '精卫声明，就是我们投下的第一颗石子。',
  ],
}

/** 保护页 / 验证页底部摘要 — 完整版见 /protocol */
export const JW_CORE_BELIEF_SUMMARY = {
  title: '为什么仍然值得嵌入「精卫声明」水印',
  paragraphs: [
    '隐形水印不是不会被破坏的锁。AI 重绘、深度修补、强压缩和去水印工具，都可能削弱甚至抹掉它。仅靠隐形水印，无法保证作品在所有传播和二次处理后都留存标记，所以我们推荐叠加可见声明层。',
    '精卫更重要的目标，是推动统一、机器可读的创作者声明。创作者的「拒绝训练」「拒绝 AI 改图」若只写在简介、主页或图内文字里，往往缺乏统一、机器可读的格式，平台和模型很难在规模上稳定识别并执行，因此这些意愿很少像 CC 授权那样被写进可自动遵守的规则。我们希望精卫声明符号像 CC 授权符号一样，逐步被平台、搜索引擎和 AI 模型接纳，成为可读取、可尊重的公共标记。我们深知单靠防御很难追上 AI 的迭代，只有让创作者意愿被平台接纳，才更可能从根源上减少侵权。',
    '精卫声明，就是我们投下的第一颗石子。',
  ],
  linkLabel: '阅读完整精卫声明 →',
  linkTo: '/protocol',
}

// ─── 工具自身的承诺 ─────────────────────────────────────────────

export const JW_TOOL_PROMISE = {
  title: '我们的工具，不使用任何 AI 模型',
  paragraphs: [
    '本工具的所有水印——隐形频域水印（DWT / DCT / Block-DC）、可见徽章、位移与脸部浮雕——都是用经典的数字信号处理算法实现的，完全不依赖任何 AI 模型，也不需要联网推理。',
    '你的图像在你的浏览器里上传，进入我们的服务器后只用于嵌入水印并立刻返回结果。',
    '我们绝不会把你的作品送进任何 AI 训练集、生成式模型，或任何形式的「机器学习数据集」——既不为我们自己，也不为第三方。',
    '我们的角色，只是替你在作品里写下一句机器读得到的、关于「这是谁的」的句子。如何被使用、能否被 AI 学习，永远是你的决定。',
  ],
}

// ─── Angie 的理念信（三版風格，目前頁面採用版本 A）─────────────

export type LetterStyle = 'narrative' | 'declaration' | 'poetic'

export interface JwLetter {
  id: LetterStyle
  styleLabel: string
  title: string
  paragraphs: string[]
  signature: string
}

export const JW_LETTER_VERSIONS: JwLetter[] = [
  {
    id: 'narrative',
    styleLabel: '叙事 · 温度',
    title: '写在最后 — 给看到这里的你',
    paragraphs: [
      '我是 Angie。',
      '开始写精卫之前，我并没有想要与谁为敌。我也用 AI——它帮我写程序、整理思路、甚至给我陪伴。',
      '但有一天我看到一位朋友的画，被人用 AI 改了发型、换了表情、抹掉署名后流到别的平台，再被指控「抄袭了 AI」。那是她画了三个礼拜的作品。',
      '那一刻我想，技术可以走得这么快，但「这是某个人花了时间做出来的」这句话，不应该在路上就被弄丢。',
      '精卫声明做的事情很小——只是在每张图里留下一句机器读得到的话：「这是人类创作，请辨识它、请尊重它。」它不会阻止所有事情，也挡不住最决绝的还原。它只是让那句话有机会被听见。',
      '如果你愿意把它放进你的下一张作品，我会把这当成一颗同样被投下的石子。',
      '没有海能填得完。但每一颗石子，都让海退了一点点。',
    ],
    signature: '— Angie，2026 年于某个写不出来但想了很久的深夜',
  },
  {
    id: 'declaration',
    styleLabel: '冷静 · 宣言',
    title: '致看到这里的你',
    paragraphs: [
      '我做精卫，不是为了与谁为敌。',
      '我承认 AI 是这个时代少数真正改变了所有人工作方式的东西，包含我自己。它也常常帮到我。',
      '但有一件事我希望被记得：那张画、那段文字、那首歌——背后是某个具体的人，花了具体的时间做出来的。',
      '精卫声明只做一件很小的事：在每张图里留下一句机器读得到的话，「这是人类创作，请辨识并尊重它」。',
      '它挡不住所有事情。但有一天，当足够多的图都留下这句话，没有人——包括 AI——能继续假装听不见。',
      '一颗石子很小。一颗一颗下去，海会记得。',
    ],
    signature: '— Angie，2026',
  },
  {
    id: 'poetic',
    styleLabel: '诗意 · 隐喻',
    title: '石子',
    paragraphs: [
      '我常常想起那只鸟。',
      '她没有想过要胜过大海。她只是每天，衔起一颗石子，飞过去，松开喙，看著它落下，再回头。',
      '我猜她也知道，海是填不平的。但她做的不是计算，是坚持。是一种——我不知道怎麼用更好的字——「我来过、我看见、我不认可」的姿势。',
      '今天的海换了形态，但海还是海。我们的时间、选择、心意被冲刷、被收进不会被询问的地方、被另一些东西重新生成出来，再也找不回原本的名字。',
      '精卫声明，是我能做出来的、最像那颗石子的东西。它不会让海退去，也不会让 AI 停下。它只是替你，把你的名字写在你的作品里，写得稍微深一点，深到下一道浪不那麼容易把它抹去。',
      '如果你也愿意，把这颗石子接过去——我们大概永远不会把海填平，但每一颗落下去的石子，都让海多认识一个人类。',
    ],
    signature: '— Angie，2026 年某个写不出来的深夜',
  },
]

/** 声明页底部展示的信件版本。想换风格只需改这个 id。 */
export const JW_ACTIVE_LETTER_ID: LetterStyle = 'narrative'

export function getActiveLetter(): JwLetter {
  return JW_LETTER_VERSIONS.find(v => v.id === JW_ACTIVE_LETTER_ID) ?? JW_LETTER_VERSIONS[0]
}

// ─── 徽章字串預覽 ─────────────────────────────────────────────────

/** Example badge strings (logo + abbrev placeholders, bottom-right). */
export function formatBadgePreview(creation: JwCreationType, restrictions: string[]): string {
  const parts = ['JW', creation, ...restrictions.slice(0, 3)]
  return parts.join(' · ')
}
