interface Props {
  label: string
  hint?: string
  min: number
  max: number
  step: number
  value: number
  onChange: (v: number) => void
  unit?: string
}

export default function Slider({ label, hint, min, max, step, value, onChange, unit }: Props) {
  return (
    <div className="form-group">
      <label className="form-label">
        {label}
        <span style={{ float: 'right', fontFamily: 'var(--font-mono)', fontWeight: 400, color: 'var(--color-text-tertiary)' }}>
          {value}{unit || ''}
        </span>
      </label>
      <input
        type="range"
        className="form-slider"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={e => onChange(Number(e.target.value))}
      />
      {hint && <span className="form-hint">{hint}</span>}
    </div>
  )
}
