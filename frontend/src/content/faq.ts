/**
 * FAQ — single source for /faq SEO page + FAQPage JSON-LD.
 *
 * Content-expansion plan (keep one page for now):
 * - Prefer a single /faq with FAQPage schema chunks (current).
 * - If a Q cluster grows enough for unique search intent, split later to
 *   /faq/glaze-vs-jingwei, /faq/privacy, /faq/verification and add each to
 *   frontend/public/seo/routes.json + sitemap.xml + SPA_FALLBACK_PATHS.
 *
 * GEO: questions match search phrasing; first paragraph is a standalone
 * 40–60 word answer; JSON-LD text equals visible copy.
 * Voice: stop-slop (hardikpandya/stop-slop) — cut filler, no 大幅度/特注,
 * no "不是 X 而是 Y" 套话.
 */

import { CONTACT_EMAIL, SITE_NAME, SITE_URL } from '../lib/site'

export const FAQ_META_TITLE = `常见问题 FAQ | ${SITE_NAME} · 防 AI 洗图 · 可追踪水印`

export const FAQ_META_DESCRIPTION =
  '精卫是什么？和 Glaze、Nightshade 有何不同？会保存图片吗？截图还能验证吗？署名·快速怎么用？样图能否挪用？2026 年 8 月更新。'

export const FAQ_DATE_MODIFIED = '2026-08-30'

export const FAQ_INTRO = {
  title: '常见问题',
  lead: `${SITE_NAME} 给插画、摄影、设计用的图片归属保护。发稿或交付前打开 jwprotect.com/protect，写入 JW 声明和可选可见防盗层。单张大约 30 秒，不跑深度学习，处理完从服务器删除。下面按搜索里常见的问法说明能做什么、不能做什么。`,
  updated: '2026 年 8 月 30 日',
}

export type FaqAnswerBlock =
  | string
  | { type: 'list'; items: string[] }

export interface FaqItem {
  id: string
  question: string
  answer: FaqAnswerBlock[]
  relatedLinks?: readonly { to: string; label: string }[]
}

export interface FaqCategory {
  id: string
  title: string
  items: FaqItem[]
}

export function faqPlainAnswer(blocks: FaqAnswerBlock[]): string {
  return blocks
    .map(b => {
      if (typeof b === 'string') return b
      return b.items.map(i => `· ${i}`).join('\n')
    })
    .join('\n')
}

export const FAQ_CATEGORIES: FaqCategory[] = [
  {
    id: 'what',
    title: '精卫是什么',
    items: [
      {
        id: 'what-is-jingwei',
        question: '精卫是什么？怎么保护图片？',
        answer: [
          `${SITE_NAME} 是面向个人创作者的图片归属保护工具。你在 jwprotect.com 上传 PNG、JPEG 或 WebP，写入可验证的 JW 声明，并可叠可见防盗层。单张大约 30 秒，不用注册。`,
          '保护页默认「署名·快速」。要自己开关位移、浮雕、模糊条等层，改用「手动调节」。验证请到验证页上传本次下载的 PNG。',
        ],
        relatedLinks: [
          { to: '/protect', label: '打开保护页' },
          { to: '/protocol', label: '阅读 JW 声明' },
        ],
      },
      {
        id: 'why-jingwei-vs-glaze-nightshade',
        question: '精卫和 Glaze、Nightshade 有什么区别？',
        answer: [
          'Glaze 和 Nightshade 主要对付作品上网后被批量爬去训练。精卫主要对付别人已经拿到你的文件、拿去 AI 改图、融图或局部重绘。三者可以一起用。',
          {
            type: 'list',
            items: [
              'Glaze / Nightshade：本地客户端，常要较强显卡，单张更慢，画面扰动更明显',
              '精卫：浏览器打开，经典图像处理，不加载深度学习模型',
              '共同限制：都不能保证以后所有工具都失败。请留原文件',
            ],
          },
        ],
        relatedLinks: [{ to: '/protect', label: '开始保护作品' }],
      },
      {
        id: 'no-retain-no-ai',
        question: '精卫会保存我的图片吗？会用 AI 处理吗？',
        answer: [
          '不会长期保存，也不会用 AI 处理。保护、验证、鉴AI辅助上传的图处理完立即从服务器删除，不建作品库，不拿去训练或商业分析。',
          '嵌入算法是经典图像处理与数字信号处理。不调用深度学习，不加载 .pth、.onnx、.ckpt。详见隐私政策。',
        ],
        relatedLinks: [
          { to: '/privacy', label: '隐私政策' },
          { to: '/terms', label: '用户服务条款' },
        ],
      },
    ],
  },
  {
    id: 'effect',
    title: '效果与局限',
    items: [
      {
        id: 'ai-fusion-limits',
        question: '打了水印就能永久防止 AI 融图和训练吗？',
        answer: [
          '不能。强压缩、反复转存、针对性去除，都可以削弱或清掉隐形层。可见层会抬高还原成本，但不对未来所有工具打包票。',
          'JW 声明希望做成类似 Creative Commons 的机器可读意愿标记，方便平台识别。这是长期方向，不能替代法律保护。',
        ],
        relatedLinks: [{ to: '/protocol', label: '了解 JW 声明' }],
      },
      {
        id: 'anti-ai-edit',
        question: '精卫能防止 AI 改图和融图吗？',
        answer: [
          '精卫针对「对方已经拿到你的图、上传 AI 工具改图或融图」。多层扰动和可见防盗层会让还原变脏、变难，抬高盗用成本。',
          '效果随原图、工具和后处理变化。2026 年 8 月的实测对比见实测矩阵页。',
        ],
        relatedLinks: [
          { to: '/protect', label: '选择保护选项' },
          { to: '/guide/watermark-matrix', label: '看实测矩阵' },
        ],
      },
      {
        id: 'quality-formats',
        question: '精卫支持哪些图片格式？会不会影响画质？',
        answer: [
          '上传支持 PNG、JPEG、WebP。开了 JW 等隐形频域层时，请导出 PNG。JPEG 有损压缩会削弱隐形信号。',
          'JW、DWT、LSB 默认尽量不影响日常观看，强度高了可能有轻微纹理。位移、浮雕、模糊条会刻意改画面。EXIF、C2PA 一般不影响观感。可先用中度或轻度预览再导出。',
        ],
      },
    ],
  },
  {
    id: 'verify',
    title: '验证与追踪',
    items: [
      {
        id: 'screenshot-verify',
        question: '截图或从社交平台重新下载的图，还能验证水印吗？',
        answer: [
          '部分能。JW 声明和追踪巩固层针对截图、平台压缩、二次保存做了冗余。实测路径：保护后截图，发社交平台，再下载后验证。',
          '多数情况仍能读到署名，但不能保证每次完整读出。验证页会分 JW、DWT、LSB、锚点报告置信度。争议请留未经传播的原始导出文件。',
        ],
        relatedLinks: [{ to: '/verify', label: '前往验证页' }],
      },
      {
        id: 'how-to-verify',
        question: '怎么验证图片有没有精卫水印？',
        answer: [
          '打开 jwprotect.com/verify，上传待查图，不用登录。系统检测 JW 声明、DWT、LSB、EXIF/IPTC、C2PA，并给出各层置信度。',
          '未检出不证明没被处理过。检出可作为「经过精卫保护或带相关元数据」的辅助佐证。请上传 PNG 成品，不要上传闪卡视频截图。',
        ],
        relatedLinks: [{ to: '/verify', label: '打开验证页' }],
      },
      {
        id: 'source-inspection',
        question: '鉴AI辅助能判断一张图是不是 AI 画的吗？',
        answer: [
          '不能下最终结论。鉴AI辅助输出成分表：文件里有没有 AI 工具元数据、相机 EXIF、C2PA 凭证。你自己综合判断。',
          '社交平台下载或截图常会丢掉这些信息。「查不到」不等于「一定是人画的」。',
        ],
        relatedLinks: [{ to: '/inspect', label: '鉴AI辅助（BETA）' }],
      },
    ],
  },
  {
    id: 'usage',
    title: '使用与设置',
    items: [
      {
        id: 'quick-credit',
        question: '署名·快速是什么？日常发图怎么用？',
        answer: [
          '署名·快速是保护页默认模式。填创作者姓名后，写入可验证的隐形 JW 声明，并按画面选浅字符或轻位移字。上传 Logo 只打一枚浅印。日常发稿大约 30 秒，不用注册。',
          '它和手动调节不共用滑条。要自己开关每一层、指定 Logo 位置，或叠铺满位移、浮雕、脸部锁，请改用手动调节。验证请上传本次下载的 PNG。',
        ],
        relatedLinks: [
          { to: '/protect', label: '打开保护页' },
          { to: '/blog/quick-credit-mode', label: '署名·快速怎么用' },
        ],
      },
      {
        id: 'holo-card',
        question: '闪卡是什么？下载的视频能用来验证吗？',
        answer: [
          '闪卡把保护后的静图做成会反光的镭射卡面，导出大约 6 秒的 MP4，方便发社交或给客户看。虹彩和细纹只出现在反光带里。',
          '闪卡不能代替验证。验证页请上传 PNG 成品。悬停保护页样卡即可预览箔面。',
        ],
        relatedLinks: [
          { to: '/protect', label: '保护并下载闪卡' },
          { to: '/blog/jingwei-holo-card', label: '闪卡介绍' },
        ],
      },
      {
        id: 'watermark-font',
        question: '水印字体可以换吗？',
        answer: [
          '目前只用开放版权字体，不能换其他字体。你可以调大小、位置和可见层样式。若以后接入更多字体，会在保护页和本页同步更新。',
        ],
      },
      {
        id: 'jw-declaration',
        question: 'JW 精卫声明是什么？必须开吗？',
        answer: [
          'JW（Jingwei Protocol）把创作类型（原创 / AI 协作）、使用限制（例如未授权 AI 训练、未授权 AI 改图）和创作者姓名，以机器可读方式写入图像，并可显示可见徽章。',
          '我们希望 JW 像 CC 标记一样被平台识别。这需要行业共识，不是强制选项。若要保留隐形层，请导出 PNG。',
        ],
        relatedLinks: [{ to: '/protocol', label: '阅读 JW 声明全文' }],
      },
      {
        id: 'delivery-feature',
        question: '约稿交付是做什么的？',
        answer: [
          '创作者上传成稿并设查看密码，生成加密交付包。客户在本站「查看画稿」页上传该包、输入密码，按住屏幕或鼠标才逐步看清，松手即散开。',
          '查看过程有缓慢移动的浮水印（查看者标识），降低截图直接拿到完整高清成稿的机会。手机浏览器支持按住查看，复杂操作仍建议用电脑。',
        ],
        relatedLinks: [{ to: '/delivery', label: '约稿交付' }],
      },
      {
        id: 'sample-images-license',
        question: '官网和仓库里的猫、狗、矩阵样图，能当自己的图用吗？',
        answer: [
          '不能。这些样图只用来说明保护效果。代码按 MIT 授权，样图版权仍归原作者与精卫，禁止当封面、商用素材、训练数据或二次创作底图。',
          '另存为挡不住。授权挡的是「MIT 等于可以拿走商用」。请用你自己的作品在保护页实测。',
        ],
        relatedLinks: [
          { to: '/guide/watermark-matrix', label: '看实测矩阵' },
          { to: '/protect', label: '用自己的图保护' },
        ],
      },
    ],
  },
  {
    id: 'roadmap',
    title: '产品路线',
    items: [
      {
        id: 'open-source-and-app',
        question: '精卫开源了吗？会做手机 App 吗？',
        answer: [
          '网站产品仓库目前未对外切开。功能稳定后，计划把保护与验证做成可自建的开源包（Docker 优先），方便社区审查。社区、捐赠、约稿交付仍留在产品站。',
          '手机 App 需要重做交互，还要过应用商店审核，目前没有计划。优先把网页版做稳。',
        ],
      },
    ],
  },
]

export const FAQ_ALL_ITEMS: FaqItem[] = FAQ_CATEGORIES.flatMap(c => c.items)

export function buildFaqJsonLd(): Record<string, unknown> {
  return {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    url: FAQ_CANONICAL,
    dateModified: FAQ_DATE_MODIFIED,
    mainEntity: FAQ_ALL_ITEMS.map(item => ({
      '@type': 'Question',
      name: item.question,
      acceptedAnswer: {
        '@type': 'Answer',
        text: faqPlainAnswer(item.answer),
      },
    })),
  }
}

export const FAQ_CTA = {
  title: '还有其他问题？',
  body: `欢迎通过反馈页留言，或邮件联系 ${CONTACT_EMAIL}。保护作品请前往保护页，验证水印请前往验证页。`,
  links: [
    { to: '/protect', label: '开始保护作品' },
    { to: '/verify', label: '验证水印' },
    { to: '/about', label: '阅读作者信' },
    { to: '/protocol', label: '阅读 JW 声明' },
    { to: '/feedback?from=faq', label: '留言反馈' },
  ] as const,
}

export const FAQ_CANONICAL = `${SITE_URL}/faq`
