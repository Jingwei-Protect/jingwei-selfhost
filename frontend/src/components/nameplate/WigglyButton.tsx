import type { ButtonHTMLAttributes, ReactNode } from 'react'

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  active?: boolean
  icon?: boolean
  children: ReactNode
}

export default function WigglyButton({ active, icon, className = '', children, ...rest }: Props) {
  const cls = [
    'np-wbtn',
    icon ? 'np-wbtn-icon' : '',
    active ? 'active' : '',
    className,
  ].filter(Boolean).join(' ')

  return (
    <button type="button" className={cls} {...rest}>
      {children}
    </button>
  )
}
