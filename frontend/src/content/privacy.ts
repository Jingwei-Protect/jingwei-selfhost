import { CONTACT_EMAIL } from '../lib/site'

export const PRIVACY_TITLE = '隐私政策'
export const PRIVACY_UPDATED = '最后更新：2026 年 6 月'
export const PRIVACY_DATE_MODIFIED = '2026-06-14'

export type PrivacySectionBody =
  | string
  | {
      type: 'termsLink'
      before: string
      linkLabel: string
      linkTo: string
      after: string
    }
  | {
      type: 'contact'
      before: string
      email: string
    }

export interface PrivacySection {
  id: string
  title: string
  body?: PrivacySectionBody
  paragraphs?: string[]
  bullets?: string[]
}

export const PRIVACY_SECTIONS: PrivacySection[] = [
  {
    id: 'relation',
    title: '与法律条款的关系',
    body: {
      type: 'termsLink',
      before: '本页说明我们如何处理你的数据。关于版权承诺、技术局限、非 AI 声明等完整法律条款，请阅读',
      linkLabel: '《用户服务与免责声明》',
      linkTo: '/terms',
      after: '。',
    },
  },
  {
    id: 'summary',
    title: '一句话摘要',
    paragraphs: [
      '你上传用于「保护 / 验证 / 鉴定」的图片只在服务器内存中处理的几秒内停留，处理完成立即从磁盘删除，不入库、不留档、不用于任何模型训练。如果你使用账号与「精卫之海」等社区功能，我们会保存你的账号资料与你公开创作的内容，直到你删除它们。',
    ],
  },
  {
    id: 'controller',
    title: '个人信息处理者与数据存储地',
    paragraphs: [
      '本服务由 精卫 Jingwei 团队运营，并作为你个人信息的处理者。我们的服务器部署于香港云服务器。对中国大陆用户而言，数据存储与处理发生在中国大陆境外（香港），即构成跨境处理；你使用本服务即表示了解并同意上述跨境存储安排。如有疑问可通过本页底部邮箱联系我们。',
    ],
  },
  {
    id: 'collect',
    title: '我们收集什么',
    bullets: [
      '账号资料：邮箱、密码（PBKDF2-SHA256 哈希后存储，明文不保存）、昵称/用户名（用于站内公开展示）。',
      '支持记录：通过 Stripe 回传的订单号、金额及支付回调数据，用于发放与核对配额。',
      '社区创作内容：你在「精卫之海」绘制的像素、作品存档（草稿/成稿）、感谢墙铭牌图片，均与你的账号关联并长期保存，直到你删除。',
      '留言与反馈：你主动提交的反馈标题、正文、可选联系邮箱与可选截图文件名。',
      '站点访问统计：首页会累计网站总访问次数（匿名汇总数字，不识别具体访客，不与账号或上传图片关联，不为此单独记录 IP 或使用 Cookie）。',
      '网络日志：为防止滥用与排障，服务器访问日志会记录请求 IP、时间与接口，最多保留 30 天后自动删除。',
      '上传图片：仅用于完成你当次请求的「保护 / 验证 / 鉴定」，处理完成后立即删除，不保存。',
    ],
  },
  {
    id: 'not',
    title: '我们不做什么',
    bullets: [
      '不长期保存用于保护/验证/鉴定的上传原图、处理后图、对比图。',
      '不将你的作品或图片用于任何 AI 模型训练。',
      '不向任何第三方出售或提供你的作品与账号信息（执法部门依法调取除外）。',
      '不在网页中嵌入第三方追踪/广告代码；网页字体已自托管，不向 Google 等外部 CDN 发起请求。',
    ],
  },
  {
    id: 'retention',
    title: '数据保留与删除',
    bullets: [
      '上传图片：处理完成即删除，不保留。',
      '网络日志（含 IP）：最多保留 30 天，到期自动删除。',
      '账号与创作内容：保留至你主动删除。',
      '注销即彻底删除：注销账号时，我们会彻底删除你的账号资料、铭牌、「精卫之海」像素与作品存档、留言反馈，以及你认领的赞助订单记录，不再保留或匿名化留存。',
    ],
  },
  {
    id: 'third',
    title: '第三方',
    bullets: [
      'Stripe：支持发生时由 Stripe 向我们推送订单 Webhook，包含订单号与金额。',
    ],
  },
  {
    id: 'minors',
    title: '未成年人',
    paragraphs: [
      '本服务面向成年创作者。若你未满 14 周岁，请在监护人同意并指导下使用；我们不会有意收集不满 14 周岁儿童的个人信息。如监护人发现相关情况，可通过本页邮箱联系我们删除。',
    ],
  },
  {
    id: 'rights',
    title: '你的权利',
    paragraphs: [
      '你可以随时查阅、更正或删除你的个人信息，也可直接注销账号一并删除上述全部数据。如需行使权利，请通过本页底部的联系邮箱与我们联系。',
    ],
  },
  {
    id: 'contact',
    title: '联系',
    body: {
      type: 'contact',
      before: '如对本政策或数据处理有疑问，请联系：',
      email: CONTACT_EMAIL,
    },
  },
]
