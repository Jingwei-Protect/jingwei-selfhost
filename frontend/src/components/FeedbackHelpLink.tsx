import type { FeedbackPageSource } from '../lib/auth'
import { useLocale } from '../i18n/LocaleContext'

type Props = {
  from: FeedbackPageSource
  context?: Record<string, string | number | boolean | null | undefined>
  className?: string
  align?: 'left' | 'center' | 'right'
}

export default function FeedbackHelpLink({ className = '', align = 'center' }: Props) {
  const { messages: m } = useLocale()
  return (
    <p className={`feedback-help-link feedback-help-link--${align} ${className}`.trim()}>
      <a href="https://jwprotect.com/feedback" target="_blank" rel="noreferrer">
        {m.components.feedbackHelpLink.ask}
      </a>
    </p>
  )
}
