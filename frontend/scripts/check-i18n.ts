/**
 * 比对 zh-Hans / en / ja 文案目录的 key 树与漏翻情况。
 * zh-Hant 由 OpenCC 运行时生成，不参与检查。
 *
 * 用法: npm run i18n:check [-- --strict] [-- --json]
 */
import { mkdirSync, writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'

import enCatalog from '../src/i18n/messages/en/index.ts'
import jaCatalog from '../src/i18n/messages/ja/index.ts'
import zhHansCatalog from '../src/i18n/messages/zh-Hans/index.ts'

import * as enAuthorLetter from '../src/content/en/authorLetter.ts'
import * as enFaq from '../src/content/en/faq.ts'
import * as enLegal from '../src/content/en/legalTerms.ts'
import * as enPrivacy from '../src/content/en/privacy.ts'
import * as enJw from '../src/content/en/jingweiProtocol.ts'
import * as jaAuthorLetter from '../src/content/ja/authorLetter.ts'
import * as jaFaq from '../src/content/ja/faq.ts'
import * as jaLegal from '../src/content/ja/legalTerms.ts'
import * as jaPrivacy from '../src/content/ja/privacy.ts'
import * as jaJw from '../src/content/ja/jingweiProtocol.ts'

type Catalog = Record<string, unknown>

interface Issue {
  level: 'error' | 'warn' | 'info'
  code: string
  path: string
  message: string
}

/** 允许为空的路径（英文 Total: N 等格式） */
const EMPTY_OK = new Set([
  'admin.users.totalSuffix',
])

/** 允许 ja 与 en 相同的路径（品牌名、技术缩写等） */
const JA_SAME_AS_EN_OK = new Set([
  'common.nav.inspectBeta',
  'common.siteName',
  'home.heroChar',
  'auth.navAuth.loading',
])

function isLangLabelPath(path: string): boolean {
  return path.startsWith('common.lang.')
}

/** content/ja 对比 content/en：跳过元数据与中文字段 */
function shouldSkipContentPath(path: string): boolean {
  if (/labelZh|descZh|_ZH|\.ZH|Canonical|DATE_|SESSION_KEY|linkTo$|\.id$|\.abbrev$/.test(path)) return true
  if (/^[A-Z_]+$/.test(path.split('.').pop() ?? '')) return false
  return false
}

function compareContentJa(bundle: string, enMod: Catalog, jaMod: Catalog): Issue[] {
  const enFlat = flattenStrings(enMod)
  const jaFlat = flattenStrings(jaMod)
  const issues: Issue[] = []

  for (const path of enFlat.keys()) {
    if (!jaFlat.has(path)) {
      issues.push({
        level: 'error',
        code: 'content-missing-key',
        path: `${bundle}.${path}`,
        message: 'ja 长文内容缺少 key',
      })
    }
  }
  for (const path of jaFlat.keys()) {
    if (!enFlat.has(path)) {
      issues.push({
        level: 'warn',
        code: 'content-extra-key',
        path: `${bundle}.${path}`,
        message: 'ja 长文内容多出 key',
      })
    }
  }
  for (const [path, enValue] of enFlat) {
    if (shouldSkipContentPath(path)) continue
    const jaValue = jaFlat.get(path)
    if (jaValue === undefined) continue
    if (jaValue.trim() === '' && enValue.trim() !== '') {
      issues.push({
        level: 'error',
        code: 'content-empty',
        path: `${bundle}.${path}`,
        message: 'ja 长文内容为空',
      })
    }
    if (jaValue === enValue && enValue.length > 4 && !isAsciiOnly(enValue)) {
      issues.push({
        level: 'warn',
        code: 'content-ja-same-as-en',
        path: `${bundle}.${path}`,
        message: 'ja 长文与 en 完全相同，疑似漏翻',
      })
    }
  }
  return issues
}

const CONTENT_BUNDLES: Array<[string, Catalog, Catalog]> = [
  ['faq', enFaq, jaFaq],
  ['legal', enLegal, jaLegal],
  ['privacy', enPrivacy, jaPrivacy],
  ['jw', enJw, jaJw],
  ['authorLetter', enAuthorLetter, jaAuthorLetter],
]

/** 仅含 ASCII 符号/数字/空白的值视为无需翻译 */
function isAsciiOnly(value: string): boolean {
  return /^[\x00-\x7F]*$/.test(value)
}

function flattenStrings(value: unknown, prefix = ''): Map<string, string> {
  const out = new Map<string, string>()
  if (typeof value === 'string') {
    if (prefix) out.set(prefix, value)
    return out
  }
  if (Array.isArray(value)) {
    value.forEach((item, index) => {
      for (const [k, v] of flattenStrings(item, `${prefix}[${index}]`)) out.set(k, v)
    })
    return out
  }
  if (value && typeof value === 'object') {
    for (const [key, child] of Object.entries(value as Catalog)) {
      const path = prefix ? `${prefix}.${key}` : key
      for (const [k, v] of flattenStrings(child, path)) out.set(k, v)
    }
  }
  return out
}

function compareLocale(
  base: Map<string, string>,
  target: Map<string, string>,
  enRef: Map<string, string>,
  locale: 'en' | 'ja',
): Issue[] {
  const issues: Issue[] = []
  for (const path of base.keys()) {
    if (!target.has(path)) {
      issues.push({
        level: 'error',
        code: 'missing-key',
        path,
        message: `${locale} 缺少 key（基准 zh-Hans 有）`,
      })
    }
  }
  for (const path of target.keys()) {
    if (!base.has(path)) {
      issues.push({
        level: 'warn',
        code: 'extra-key',
        path,
        message: `${locale} 多出 key（基准 zh-Hans 无）`,
      })
    }
  }
  for (const [path, baseValue] of base) {
    const targetValue = target.get(path)
    if (targetValue === undefined) continue
    if (targetValue.trim() === '' && !EMPTY_OK.has(path)) {
      issues.push({
        level: 'error',
        code: 'empty-value',
        path,
        message: `${locale} 文案为空`,
      })
    }
    if (locale === 'en' && targetValue === baseValue && !isAsciiOnly(baseValue)) {
      issues.push({
        level: 'info',
        code: 'en-same-as-zh-Hans',
        path,
        message: 'en 与 zh-Hans 完全相同（若为品牌/缩写可忽略）',
      })
    }
    if (locale === 'ja' && targetValue === enRef.get(path) && !JA_SAME_AS_EN_OK.has(path) && !isLangLabelPath(path)) {
      if (!isAsciiOnly(targetValue)) {
        issues.push({
          level: 'warn',
          code: 'ja-same-as-en',
          path,
          message: 'ja 与 en 完全相同，疑似漏翻（可用机翻对照）',
        })
      }
    }
  }
  return issues
}

function summarize(issues: Issue[]) {
  const counts = { error: 0, warn: 0, info: 0 }
  for (const issue of issues) counts[issue.level]++
  return counts
}

function main(): void {
  const args = new Set(process.argv.slice(2))
  const strict = args.has('--strict')
  const jsonOut = args.has('--json')

  const base = flattenStrings(zhHansCatalog)
  const enFlat = flattenStrings(enCatalog)
  const jaFlat = flattenStrings(jaCatalog)

  const issues = [
    ...compareLocale(base, enFlat, enFlat, 'en'),
    ...compareLocale(base, jaFlat, enFlat, 'ja'),
    ...CONTENT_BUNDLES.flatMap(([name, enMod, jaMod]) => compareContentJa(name, enMod, jaMod)),
  ].sort((a, b) => a.path.localeCompare(b.path) || a.code.localeCompare(b.code))

  const counts = summarize(issues)
  const report = {
    checkedAt: new Date().toISOString(),
    baseLocale: 'zh-Hans',
    targetLocales: ['en', 'ja'],
    skippedLocales: ['zh-Hant (OpenCC runtime)'],
    keyCount: {
      'zh-Hans': base.size,
      en: enFlat.size,
      ja: jaFlat.size,
    },
    counts,
    issues,
  }

  if (jsonOut) {
    const outPath = resolve('../exports/i18n-check-report.json')
    mkdirSync(dirname(outPath), { recursive: true })
    writeFileSync(outPath, `${JSON.stringify(report, null, 2)}\n`, 'utf8')
    console.log(`JSON 报告已写入 ${outPath}`)
  }

  console.log('i18n 文案检查（UI: 基准 zh-Hans · 长文: 基准 en）')
  console.log(`  keys: zh-Hans=${base.size}  en=${enFlat.size}  ja=${jaFlat.size}`)
  console.log(`  结果: ${counts.error} 错误 / ${counts.warn} 警告 / ${counts.info} 提示`)
  console.log('  注: zh-Hant 由 OpenCC 自动生成，未纳入对比')
  console.log('')

  const show = issues.filter(i => i.level !== 'info' || args.has('--verbose'))
  for (const issue of show) {
    const tag = issue.level === 'error' ? 'ERR' : issue.level === 'warn' ? 'WRN' : 'INF'
    console.log(`[${tag}] ${issue.path}`)
    console.log(`       ${issue.message}`)
  }

  if (show.length === 0) {
    console.log('未发现错误或警告。')
  } else if (!jsonOut && counts.warn > 0) {
    console.log('')
    console.log('提示: 在 Cursor/VS Code 安装 i18n Ally Next，可并排对照并机翻日语。')
  }

  const failed = counts.error > 0 || (strict && counts.warn > 0)
  process.exit(failed ? 1 : 0)
}

main()
