import { inspectReport } from './inspectReport'

export const inspect = {
  betaBadge: 'BETA',
  title: '鉴AI辅助',
  metaDescription:
    '精卫 Jingwei 鉴AI辅助（BETA）：上传图片查看署名凭证、文件结构与像素统计等辅助线索，不下最终鉴定结论，仅供创作者参考。',
  subtitle: '上传图片，查看辅助分析报告里的各项线索（不下最终结论）',
  principlesCard: {
    title: '分析说明',
    intro: '本页会生成一份分析报告，列出图片文件里能读到的线索：署名凭证、保存信息、文件结构、像素统计。',
  },
  unlock: {
    intro: '鉴AI辅助为封闭内测功能，请输入管理员提供的内测码后使用。',
    codeLabel: '内测码',
    codePlaceholder: '输入内测码',
    checking: '验证中…',
    enter: '进入内测',
    invalid: '内测码无效',
  },
  principles: {
    expand: '展开这块是怎么工作的？',
    collapse: '收起这块是怎么工作的？',
    bodyLead:
      '本页会生成一份分析报告，列出图片文件里能读到的线索：署名凭证、保存信息、文件结构、像素统计。这里不会直接下「是不是 AI 画的」这类结论，下面各项需自行对照。',
    bodyBullet1: '每项内容会列出基本分析，并说明查到了什么。右上角标红的是比较硬的线索。',
    bodyBullet2:
      '某项没查到，不等于反过来能证明什么。从社交平台下载的图，很多信息会被平台处理掉，这只能叫「查不到」，不能叫「一定是人画的」。',
    interpretationLabel: '读证提示',
    statsHint: '统计提示（仅供参考）',
    metricsTitle: '原始测量值',
  },
  actions: {
    recheck: '重新检测',
    checking: '检测中…',
  },
  loading: {
    reading: '正在读取来源凭证与元数据…',
    failed: '检测失败',
    network: '网络错误',
  },
  strengthLabels: {
    strong: '硬证据',
    medium: '结构线索',
    weak: '统计参考',
  },
  summaryHint: '上面三个数字是有明确指向的线索条数，不是 AI 概率。',
  summaryDetail: '上面三个数字是有明确指向的线索条数。有些项虽然查了但算不出结论，不会计入这三个数字。这里也不是「AI 概率」。只有标红「与 AI 相关」才是比较硬的关联。',
  itemStatus: {
    forensicsFound: '有提示·仅参考',
    forensicsNotFound: '无异常提示',
    found: '有记录',
    notFound: '未发现',
  },
  meaning: {
    aiRelevant: '本项：出现与 AI 生图相关的客观线索（请对照其他项）',
    found: '本项：有记录，详见读证提示',
    notFound: '本项：未发现此项线索',
  },
  report: inspectReport,
} as const
