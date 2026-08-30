import iconPencil from '../../assets/paint-icons/pencil.png'
import iconMarker from '../../assets/paint-icons/marker.png'
import iconEraser from '../../assets/paint-icons/eraser.png'
import iconSpray from '../../assets/paint-icons/spray.png'
import iconLine from '../../assets/paint-icons/line.png'
import iconRect from '../../assets/paint-icons/rect.png'
import iconEllipse from '../../assets/paint-icons/ellipse.png'
import iconStar from '../../assets/paint-icons/star.png'
import iconHeart from '../../assets/paint-icons/heart.png'
import iconSparkleStamp from '../../assets/paint-icons/sparkle-stamp.png'
import iconGlowBrush from '../../assets/paint-icons/glow-brush.png'
import iconUndo from '../../assets/paint-icons/undo.png'
import iconRedo from '../../assets/paint-icons/redo.png'
import iconEyedropper from '../../assets/paint-icons/eyedropper.png'
import iconBucket from '../../assets/paint-icons/bucket.png'

export const CANVAS_W = 270
export const CANVAS_H = 108
/** 与画布一致；感谢墙卡片外框为 5:2（CSS aspect-ratio） */
export const CANVAS_ASPECT = CANVAS_W / CANVAS_H

/** 上传图片作为铭牌底图：累计支持 ¥68（deep 档）起 */
export const UPLOAD_IMAGE_MIN_TIER = 'deep' as const
export const UPLOAD_IMAGE_MIN_YUAN = 68
/** 客户端挑选文件上限；保存时仍受 API data URL ~200KB 约束 */
export const UPLOAD_IMAGE_MAX_BYTES = 512_000
export const UPLOAD_IMAGE_ACCEPT = 'image/png,image/jpeg,image/webp'
export const BG_COLOR = '#ffffff'
export const MAX_HISTORY = 50

/** xy4X 老师赞助色（感谢墙调色盘首行） */
export const SPONSOR_PALETTE = [
  '#ff6b6b', '#ffd93d', '#6bcb77', '#4d96ff', '#9b5de5',
] as const

/** 25 swatches — 5 columns × 5 rows, organized by hue family */
export const PALETTE = [
  // Row 1: monochrome
  '#1d1d1f', '#4a4a4a', '#808080', '#c0c0c0', '#ffffff',
  // Row 2: warm reds → oranges → yellows
  '#c0392b', '#ff3b30', '#ff9500', '#ffcc00', '#ffe066',
  // Row 3: greens → teals
  '#a8e06c', '#34c759', '#1e8449', '#7fdbca', '#5dade2',
  // Row 4: blues → purples
  '#87ceeb', '#3a78d8', '#007aff', '#5856d6', '#9b59b6',
  // Row 5: pinks / browns / pastels
  '#e91e63', '#ff69b4', '#ffc0cb', '#c8a2c8', '#a0522d',
]

export type Tool =
  | 'pencil' | 'marker' | 'eraser' | 'spray'
  | 'glow'
  | 'line' | 'rect' | 'ellipse'
  | 'star' | 'heart' | 'sparkle'
  | 'eyedropper'
  | 'fill'

/** 工具的最低 tier 要求（不在表中即所有人可用） */
export const TOOL_TIER_REQUIREMENTS: Partial<Record<Tool, 'sustained' | 'deep' | 'patron'>> = {
  glow: 'deep',
}

export const TOOLS: { id: Tool; icon: string; title: string }[] = [
  { id: 'pencil', icon: iconPencil, title: '铅笔' },
  { id: 'marker', icon: iconMarker, title: '画笔' },
  { id: 'eraser', icon: iconEraser, title: '橡皮擦' },
  { id: 'fill', icon: iconBucket, title: '油漆桶' },
  { id: 'spray', icon: iconSpray, title: '喷枪' },
  { id: 'glow', icon: iconGlowBrush, title: '闪光画笔' },
  { id: 'eyedropper', icon: iconEyedropper, title: '采色器（点画布取色）' },
  { id: 'line', icon: iconLine, title: '直线' },
  { id: 'rect', icon: iconRect, title: '矩形' },
  { id: 'ellipse', icon: iconEllipse, title: '椭圆' },
  { id: 'star', icon: iconStar, title: '星星画笔（拖动留下星星轨迹）' },
  { id: 'heart', icon: iconHeart, title: '爱心画笔（拖动留下爱心轨迹）' },
  { id: 'sparkle', icon: iconSparkleStamp, title: '闪光盖章（单击）' },
]

export const HISTORY_TOOLS = [
  { id: 'undo' as const, icon: iconUndo, title: '撤销' },
  { id: 'redo' as const, icon: iconRedo, title: '重做' },
]
