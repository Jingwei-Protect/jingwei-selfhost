import { useState, type ReactNode } from 'react'

interface Props {
  title: string
  defaultOpen?: boolean
  children: ReactNode
}

export default function Accordion({ title, defaultOpen = false, children }: Props) {
  const [open, setOpen] = useState(defaultOpen)

  return (
    <div className={`accordion${open ? ' open' : ''}`}>
      <div className="accordion-header" onClick={() => setOpen(!open)}>
        <span>{title}</span>
        <span className="accordion-chevron">▼</span>
      </div>
      {open && <div className="accordion-body">{children}</div>}
    </div>
  )
}
