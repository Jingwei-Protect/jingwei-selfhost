/** Shared SVG filters for hand-drawn wobble edges */
export default function WigglyDefs() {
  return (
    <svg aria-hidden="true" className="np-svg-defs" focusable="false">
      <defs>
        <filter id="np-wobble" x="-8%" y="-8%" width="116%" height="116%">
          <feTurbulence type="fractalNoise" baseFrequency="0.04" numOctaves="2" result="noise" />
          <feDisplacementMap in="SourceGraphic" in2="noise" scale="2.5" xChannelSelector="R" yChannelSelector="G" />
        </filter>
      </defs>
    </svg>
  )
}
