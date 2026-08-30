import { TOOLS, HISTORY_TOOLS, TOOL_TIER_REQUIREMENTS } from './constants'
import { TIER_LOCKED_HINT, TIER_ORDER } from './frameStyles'
import type { Tool } from './constants'
import type { SponsorTier } from './types'
import WigglyButton from './WigglyButton'

function meetsTier(user: SponsorTier, required: SponsorTier): boolean {
  return TIER_ORDER[user] >= TIER_ORDER[required]
}

interface Props {
  tool: Tool
  onToolChange: (t: Tool) => void
  canUndo: boolean
  canRedo: boolean
  onUndo: () => void
  onRedo: () => void
  userTier?: SponsorTier
}

export default function NameplateToolbar({
  tool,
  onToolChange,
  canUndo,
  canRedo,
  onUndo,
  onRedo,
  userTier = 'supporter',
}: Props) {
  return (
    <aside className="np-tools">
      {TOOLS.map(t => {
        const req = TOOL_TIER_REQUIREMENTS[t.id]
        const locked = !!req && !meetsTier(userTier, req)
        const title = locked ? `${t.title}（${TIER_LOCKED_HINT}）` : t.title
        return (
          <WigglyButton
            key={t.id}
            icon
            active={tool === t.id}
            className={`np-tool-btn${locked ? ' np-tool-btn-locked' : ''}`}
            title={title}
            disabled={locked}
            onClick={() => !locked && onToolChange(t.id)}
          >
            <img src={t.icon} alt="" className="np-tool-img" draggable={false} />
            {locked && <span className="np-tool-lock" aria-hidden="true">🔒</span>}
          </WigglyButton>
        )
      })}
      <div className="np-tool-separator" />
      <WigglyButton
        icon
        className="np-tool-btn"
        title={HISTORY_TOOLS[0].title}
        disabled={!canUndo}
        onClick={onUndo}
      >
        <img src={HISTORY_TOOLS[0].icon} alt="" className="np-tool-img" draggable={false} />
      </WigglyButton>
      <WigglyButton
        icon
        className="np-tool-btn"
        title={HISTORY_TOOLS[1].title}
        disabled={!canRedo}
        onClick={onRedo}
      >
        <img src={HISTORY_TOOLS[1].icon} alt="" className="np-tool-img" draggable={false} />
      </WigglyButton>
    </aside>
  )
}
