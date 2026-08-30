/**
 * Localize inspect evidence-report items from stable ids + derived variants.
 * API display strings are Chinese-only; frontend resolves copy by locale.
 */

import type { Messages } from '../i18n/messages/types'

export type Strength = 'strong' | 'medium' | 'weak'

export interface EvidenceItem {
  id: string
  category: string
  category_label: string
  strength: Strength
  strength_label: string
  found: boolean
  title: string
  detail: Record<string, unknown>
  note?: string | null
  interpretation?: string | null
  meaning_line?: string | null
  ai_relevant?: boolean
  status_label?: string | null
}

type ReportMessages = Messages['inspect']['report']

export function resolveItemVariant(item: EvidenceItem): string {
  const d = item.detail
  switch (item.id) {
    case 'ai_metadata':
      return item.found ? 'found' : 'not_found'
    case 'c2pa': {
      if (d.available === false) return 'unavailable'
      if (!item.found) return 'not_found'
      if (d.declares_ai && d.signature_valid === false) return 'ai_doubtful'
      if (item.ai_relevant) return 'ai_declared'
      return 'has_chain'
    }
    case 'exif_camera':
      if (item.found) return 'found'
      if (d.fields && typeof d.fields === 'object' && Object.keys(d.fields as object).length > 0) {
        return 'partial'
      }
      return 'none'
    case 'file_structure': {
      if (d.error) return 'read_error'
      const clues = d.clues
      if (!Array.isArray(clues) || clues.length === 0) return 'no_clues'
      if (d.shell_only) return 'app_shell'
      if (d.embedded_thumbnail) return 'has_thumbnail'
      const colorMgmt = d.color_management
      if (Array.isArray(colorMgmt)) {
        if (colorMgmt.length > 0) return 'has_color_png'
        if (d.format === 'png') return 'no_color_png'
      }
      if (d.has_adobe_marker) return 'adobe'
      return 'generic'
    }
    case 'pixel_forensics':
      if (d.error) return 'error'
      return item.found ? 'anomaly' : 'normal'
    default:
      return item.found ? 'found' : 'not_found'
  }
}

function joinTools(detail: Record<string, unknown>): string {
  const tools = detail.tools
  if (!Array.isArray(tools) || tools.length === 0) return '—'
  const names = tools.filter((t): t is string => typeof t === 'string')
  if (names.length <= 3) return names.join(', ')
  return `${names.slice(0, 3).join(', ')}…`
}

function joinApps(detail: Record<string, unknown>): string {
  const apps = detail.app_segments
  if (!Array.isArray(apps) || apps.length === 0) return '—'
  return apps.filter((a): a is string => typeof a === 'string').join(', ')
}

function interpolate(template: string, vars: Record<string, string>): string {
  return template.replace(/\{(\w+)\}/g, (_, key: string) => vars[key] ?? `{${key}}`)
}

function variantCopy(
  report: ReportMessages,
  itemId: string,
  variant: string,
  detail: Record<string, unknown>,
): {
  title: string
  status: string
  meaning: string
  interpretation: string
  note: string
} | null {
  const items = report.items as Record<
    string,
    {
      title: string
      variants: Record<
        string,
        { status: string; meaning: string; interpretation: string; note: string }
      >
    }
  >
  const block = items[itemId]
  if (!block) return null
  const v = block.variants[variant]
  if (!v) return null

  const vars: Record<string, string> = {}
  if (itemId === 'ai_metadata' && variant === 'found') {
    vars.tools = joinTools(detail)
  }
  if (itemId === 'file_structure' && variant === 'app_shell') {
    vars.apps = joinApps(detail)
  }

  return {
    title: block.title,
    status: v.status,
    meaning: interpolate(v.meaning, vars),
    interpretation: interpolate(v.interpretation, vars),
    note: interpolate(v.note, vars),
  }
}

export function localizeCategoryLabel(
  category: string,
  report: ReportMessages,
): string {
  const categories = report.categories as Record<string, string>
  return categories[category] ?? category
}

export function localizeStrengthBadge(
  item: EvidenceItem,
  report: ReportMessages,
  strengthLabels: Messages['inspect']['strengthLabels'],
): string {
  if (item.id === 'file_structure' && item.detail.shell_only) {
    return report.strengthBadge.shellRecord
  }
  return strengthLabels[item.strength] ?? item.strength
}

export function localizeReportItem(
  item: EvidenceItem,
  report: ReportMessages,
): {
  title: string
  statusLabel: string
  meaningLine: string
  interpretation: string | null
  note: string | null
} {
  const variant = resolveItemVariant(item)
  const copy = variantCopy(report, item.id, variant, item.detail)
  if (!copy) {
    return {
      title: item.title,
      statusLabel: item.status_label ?? '',
      meaningLine: item.meaning_line ?? '',
      interpretation: item.interpretation ?? null,
      note: item.note ?? null,
    }
  }
  return {
    title: copy.title,
    statusLabel: copy.status,
    meaningLine: copy.meaning,
    interpretation: copy.interpretation,
    note: copy.note,
  }
}

export function localizeForensicsHints(
  detail: Record<string, unknown>,
  report: ReportMessages,
): string[] {
  const hints: string[] = []
  const noise = detail.noise_residual_std
  const peak = detail.frequency_peak_ratio
  if (typeof noise === 'number' && noise < 0.6) {
    hints.push(report.hints.lowNoise)
  }
  if (typeof peak === 'number' && peak > 250) {
    hints.push(report.hints.highPeak)
  }
  return hints
}

export function localizeFileStructureClues(
  detail: Record<string, unknown>,
  report: ReportMessages,
): string[] {
  const clues: string[] = []
  if (detail.embedded_thumbnail) {
    clues.push(report.clues.embeddedThumbnail)
  }
  if (detail.has_adobe_marker) {
    clues.push(report.clues.adobeMarker)
  }
  const apps = detail.app_segments
  if (Array.isArray(apps) && apps.some(a => a !== 'APP0/JFIF')) {
    clues.push(interpolate(report.clues.appSegments, {
      apps: apps.filter((a): a is string => typeof a === 'string').join(', '),
    }))
  }
  const colorMgmt = detail.color_management
  if (Array.isArray(colorMgmt) && colorMgmt.length > 0) {
    clues.push(interpolate(report.clues.colorManagement, {
      chunks: colorMgmt.filter((c): c is string => typeof c === 'string').join(', '),
    }))
  } else if (detail.format === 'png' && detail.chunks) {
    clues.push(report.clues.noColorManagement)
  }
  return clues
}
