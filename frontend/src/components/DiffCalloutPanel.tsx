export interface DiffHotspot {
  /** 0–100，相对图片宽度 */
  x: number
  /** 0–100，相对图片高度 */
  y: number
  label: string
}

export interface DiffCalloutPanelProps {
  imageSrc: string
  imageAlt: string
  caption: string
  hotspots?: readonly DiffHotspot[]
}

/** 圈出差异区域：标注图 + 可选 SVG 热区圆环 */
export default function DiffCalloutPanel({ imageSrc, imageAlt, caption, hotspots }: DiffCalloutPanelProps) {
  return (
    <figure className="diff-callout">
      <div className="diff-callout-frame">
        <img className="diff-callout-img" src={imageSrc} alt={imageAlt} loading="lazy" />
        {hotspots && hotspots.length > 0 ? (
          <svg className="diff-callout-svg" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden>
            {hotspots.map((spot, i) => (
              <g key={i}>
                <circle cx={spot.x} cy={spot.y} r="4.5" className="diff-callout-ring" />
                <circle cx={spot.x} cy={spot.y} r="2" className="diff-callout-dot" />
              </g>
            ))}
          </svg>
        ) : null}
      </div>
      <figcaption className="diff-callout-caption">{caption}</figcaption>
      {hotspots && hotspots.length > 0 ? (
        <ul className="diff-callout-list">
          {hotspots.map((spot, i) => (
            <li key={i}>{spot.label}</li>
          ))}
        </ul>
      ) : null}
    </figure>
  )
}
