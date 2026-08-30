/**
 * 作者信 — /about SEO 长文页（单一来源）
 * 正文为作者提供的原文
 */

import { CONTACT_EMAIL, SITE_NAME, SITE_URL } from '../lib/site'

export const AUTHOR_LETTER_CANONICAL = `${SITE_URL}/about`

export const AUTHOR_LETTER_META_TITLE = `作者信 · 为什么做 ${SITE_NAME} | 艺术品弧光与创作意义`

export const AUTHOR_LETTER_META_DESCRIPTION =
  '精卫 Jingwei 作者信：本雅明式的艺术品弧光、AI 时代信任危机、从保存作品到保存人的痕迹，以及投下一颗石子的意义。'

/** ISO 8601，供 JSON-LD 与 <time datetime> */
export const AUTHOR_LETTER_DATE_PUBLISHED = '2026-06-01'
export const AUTHOR_LETTER_DATE_MODIFIED = '2026-06-14'

export const AUTHOR_LETTER_INTRO = {
  kicker: '作者的话',
  title: '作者信',
  lead: `写给每一位可能点开这里的创作者。这不是产品说明书，而是我做 ${SITE_NAME} 的原因。`,
  updated: '2026 年 6 月',
}

export const AUTHOR_LETTER_PARAGRAPHS: readonly string[] = [
  '十年前，当我理所当然地接受碎片信息、电影与摄影时，我并没有真正理解一个世纪前的本雅明。我不曾理解他所描绘的艺术作品只能属于某个时刻、某个地点、某个原作的、难以言说却真实存在的弧光。也不曾真正忧虑过，当一件艺术品可以被无限次、几乎无损地复刻时，这种弧光会如何一点点消散。',
  '直到我被一脚踹进这场 AI 时代的信任危机里。',
  '无数作品被无限地传播，被无限地裁切、压缩、转发、再上传。但真正让我不安的，是创作者在这个过程中变得越来越容易被抹去。作品还在流动，它与作者之间的联系却越来越淡。到了最后，连人本身都被抽离了，只剩下可被调用的风格、表面和结果。',
  '在这个复制几乎没有成本的新时代里，在无限繁殖的信息中，所有人质疑着所有信息里的含活人量，然后竞争着做出更像人却不能有某个真人痕迹的作品。',
  '绘画好像总是在每一个时代里最早感受到冲击的，AI 时代也是如此。但也许，答案也会最先从它这里长出来。摄影出现时，人们曾以为绘画会被取代。机械印刷与互联网改变传播方式时，也有人担心艺术会被不断复制的媒介稀释。可艺术并没有因此终结。恰恰相反，它总是在每一次冲击之后，重新逼近那个更核心的问题：那些始终无法被复制、无法被传播形式取代的弧光，究竟来自哪里？',
  '作为一个画得不怎么好的爱好者，现在每当我想动笔时，总会想：既然AI可以在一秒钟内生成更准确、更精致的图像，那我为什么还要开始？这份犹豫令我最为不安，这场信任危机最令我恐惧的是，我们是否仍然相信，一个缓慢、不完美、甚至充满犹豫的创作过程，本身仍然有意义。',
  '如果过去我们试图保存的是艺术品的弧光，那么在今天，也许更难的是保存人的弧光。我想，人的弧光或许正来自于在犹豫、选择、坚持、推翻与重来中留下来的痕迹，来自于即使知道结果可以被瞬间替代，仍然选择开始的冲动。精卫Jingwei就是在这样的背景下出现的。它不是为了阻止技术，也不是为了拒绝未来。它只是想让作品在流动的过程中，仍然有机会带着"这是由一个具体的人类创造的印记，以及这个人希望它被怎样对待"的信息一起流动。哪怕这种保留并不完美，哪怕它只能多留下一个微弱但清晰的痕迹，我也仍然觉得值得去做。',
  '很多今天看似理所当然的规则，其实最初都只是少数人的坚持，然后才慢慢变成大家共同遵循的语言。版权制度如此，CC标志如此，所有关于署名、授权和边界的努力也如此。',
  '精卫知道大海不会被她填平，却仍然衔石落海。西西弗斯知道巨石会再次滚落，却仍然一次次将它推上山顶。上帝造就巴别塔，让语言分散、方向分裂，但在世界不同的角落、不同的时空里，总有人在做着相似的事。不是因为他们能走向同一个结果，而是因为他们在不同的地方，都做出了相似的选择。对我来说，这正是我们人类笨拙的英雄主义。而这，就是人类群星闪耀时。',
  '而精卫Jingwei，就是我的那颗石子。',
]

export const AUTHOR_LETTER_CTA = {
  title: '若你愿意接过这颗石子',
  links: [
    { to: '/protect', label: '开始保护作品' },
    { to: '/protocol', label: '阅读 JW 声明' },
    { to: '/faq', label: '常见问题' },
  ] as const,
  contact: `有疑问欢迎邮件联系 ${CONTACT_EMAIL}`,
}

export function buildAuthorLetterJsonLd(): Record<string, unknown> {
  const body = AUTHOR_LETTER_PARAGRAPHS.join('\n\n')
  return {
    '@context': 'https://schema.org',
    '@type': 'Article',
    headline: AUTHOR_LETTER_INTRO.title,
    description: AUTHOR_LETTER_META_DESCRIPTION,
    url: AUTHOR_LETTER_CANONICAL,
    inLanguage: 'zh-Hans',
    datePublished: AUTHOR_LETTER_DATE_PUBLISHED,
    dateModified: AUTHOR_LETTER_DATE_MODIFIED,
    author: {
      '@type': 'Organization',
      name: SITE_NAME,
      url: SITE_URL,
    },
    publisher: {
      '@type': 'Organization',
      name: SITE_NAME,
      url: SITE_URL,
    },
    articleBody: body,
    about: [
      '图像归属保护',
      'AI 时代创作者',
      '艺术品弧光',
      '本雅明',
      'JW 声明',
      'Creative Commons',
    ],
  }
}
