import { PALETTE, SPONSOR_PALETTE } from './constants'
import { useLocale } from '../../i18n/LocaleContext'

interface Props {
  color: string
  onColorChange: (c: string) => void
  brushSize: number
  onBrushSizeChange: (n: number) => void
  brushOpacity: number
  onBrushOpacityChange: (n: number) => void
}

function norm(c: string) {
  return c.trim().toLowerCase()
}

export default function NameplatePalette({
  color,
  onColorChange,
  brushSize,
  onBrushSizeChange,
  brushOpacity,
  onBrushOpacityChange,
}: Props) {
  const { messages: m } = useLocale()
  const t = m.components.nameplate
  const active = norm(color)
  const inPreset = [...SPONSOR_PALETTE, ...PALETTE].some(c => norm(c) === active)

  return (
    <aside className="np-right-panel">
      <div className="np-palette-sponsor">
        <span className="np-palette-sponsor-label">{t.sponsorPaletteLabel}</span>
        <div className="np-palette np-palette-sponsor-row">
          {SPONSOR_PALETTE.map(c => (
            <button
              key={c}
              type="button"
              className={`np-swatch np-swatch-sponsor${active === norm(c) ? ' selected' : ''}`}
              style={{ background: c }}
              onClick={() => onColorChange(c)}
              title={c}
            />
          ))}
        </div>
      </div>

      <div className="np-palette-custom">
        <label className="np-color-picker-label">
          <input
            type="color"
            className="np-color-picker-input"
            value={active.match(/^#[0-9a-f]{6}$/) ? active : '#1d1d1f'}
            onChange={e => onColorChange(e.target.value)}
            title={t.customColor}
          />
          <span className="np-color-picker-text">{t.customColor}</span>
        </label>
        {!inPreset && (
          <span
            className="np-color-current-swatch selected"
            style={{ background: color }}
            title={color}
          />
        )}
      </div>

      <div className="np-palette">
        {PALETTE.map(c => (
          <button
            key={c}
            type="button"
            className={`np-swatch${active === norm(c) ? ' selected' : ''}`}
            style={{ background: c }}
            onClick={() => onColorChange(c)}
            title={c}
          />
        ))}
      </div>

      <div className="np-size-section">
        <label className="np-size-label">{t.brush}</label>
        <div className="np-size-track-wrap">
          <input
            type="range"
            min={1}
            max={20}
            value={brushSize}
            onChange={e => onBrushSizeChange(Number(e.target.value))}
            className="np-size-slider"
          />
        </div>
        <span className="np-size-value">{brushSize}px</span>
      </div>

      <div className="np-size-section">
        <label className="np-size-label">{t.brushOpacity}</label>
        <div className="np-size-track-wrap">
          <input
            type="range"
            min={5}
            max={100}
            value={brushOpacity}
            onChange={e => onBrushOpacityChange(Number(e.target.value))}
            className="np-size-slider"
          />
        </div>
        <span className="np-size-value">{brushOpacity}%</span>
      </div>
    </aside>
  )
}
