/**
 * 精卫声明符号系统 — 5 个统一视觉的圆形符号。
 *
 *   JW   精卫声明标识（协议前缀，表示本组合属于精卫声明系统）
 *   OC   原创作品 (Original Creation)
 *   AI   AI 辅助创作 (AI Assisted)
 *   NO-TR 未授权用于训练 (No Training)
 *   NO-ED 未授权 AI 编辑 (No AI Editing)
 *
 * 设计原则（依用户参考图）：
 *  - 相同圆形、相同线条粗细、相同字重
 *  - 限制类（NO-TR / NO-ED）使用斜线表示「禁止」语义
 *  - 简洁易读，小尺寸 (16px) 仍可辨识
 *  - 中性无歧义，避免具象图形，适用全球语言环境
 */

import type { CSSProperties } from 'react'

export type JwIconType = 'JW' | 'OC' | 'AI' | 'NO-TR' | 'NO-ED'

interface Props {
  type: JwIconType
  size?: number
  /** 主色（圆+文字）。默认 currentColor，跟随外层 color 继承。 */
  color?: string
  /** 斜线颜色（仅 NO-TR / NO-ED 用到）。默认与主色一致（黑）。 */
  strikeColor?: string
  /** 实心反白版（黑底白字） */
  inverted?: boolean
  className?: string
  title?: string
  style?: CSSProperties
}

const INNER_LABEL: Record<JwIconType, string> = {
  JW: 'JW',
  OC: 'OC',
  AI: 'AI',
  'NO-TR': 'TR',
  'NO-ED': 'ED',
}

const FULL_LABEL: Record<JwIconType, string> = {
  JW: 'JW · 精卫声明',
  OC: 'OC · 原创作品',
  AI: 'AI · AI 辅助创作',
  'NO-TR': 'NO-TR · 未授权 AI 训练',
  'NO-ED': 'NO-ED · 未授权 AI 编辑',
}

export function JwIcon({
  type,
  size = 64,
  color,
  strikeColor,
  inverted = false,
  className,
  title,
  style,
}: Props) {
  const isRestriction = type === 'NO-TR' || type === 'NO-ED'
  const text = INNER_LABEL[type]
  const a11yTitle = title ?? FULL_LABEL[type]

  // 反白：黑底白字白圈
  const fg = inverted ? '#ffffff' : (color ?? 'currentColor')
  const bg = inverted ? '#1a1a1a' : 'transparent'
  // 斜线默认与主色相同（黑色），保持单色风格
  const strike = strikeColor ?? fg

  // 字号：2 字母用 38，3 字母（仅 JW/OC/AI 都是 2 字）保留弹性
  const fontSize = text.length <= 2 ? 38 : 32

  return (
    <svg
      viewBox="0 0 100 100"
      width={size}
      height={size}
      className={className}
      style={{ display: 'inline-block', flexShrink: 0, ...style }}
      role="img"
      aria-label={a11yTitle}
    >
      <title>{a11yTitle}</title>
      {/* 圆形背景/边框 */}
      <circle
        cx="50"
        cy="50"
        r="44"
        fill={bg}
        stroke={fg}
        strokeWidth="4.5"
      />
      {/* 中心文字 */}
      <text
        x="50"
        y="52"
        textAnchor="middle"
        dominantBaseline="central"
        fontFamily="ui-sans-serif, system-ui, -apple-system, 'Helvetica Neue', Arial, sans-serif"
        fontWeight="900"
        fontSize={fontSize}
        fill={fg}
        letterSpacing="-1"
      >
        {text}
      </text>
      {/* 斜线（仅限制类） */}
      {isRestriction && (
        <line
          x1="20"
          y1="20"
          x2="80"
          y2="80"
          stroke={strike}
          strokeWidth="6"
          strokeLinecap="round"
        />
      )}
    </svg>
  )
}

/**
 * 一行展示多个 JW 符号（徽章组合）。
 *
 * 用法：
 *   <JwBadgeRow types={['JW', 'OC', 'NO-TR']} />
 */
export function JwBadgeRow({
  types,
  size = 36,
  gap = 4,
  inverted = false,
  className,
}: {
  types: JwIconType[]
  size?: number
  gap?: number
  inverted?: boolean
  className?: string
}) {
  return (
    <span
      className={className}
      style={{ display: 'inline-flex', alignItems: 'center', gap }}
    >
      {types.map((t, i) => (
        <JwIcon key={`${t}-${i}`} type={t} size={size} inverted={inverted} />
      ))}
    </span>
  )
}

export default JwIcon
