import type { Locale } from '../i18n/types'
import { getMessages } from '../i18n/messages'

const CODE_KEYS = {
  disp_text_required: 'dispTextRequired',
  logo_file_required: 'logoFileRequired',
  beta_code_required: 'betaCodeRequired',
  beta_code_invalid: 'betaCodeInvalid',
  beta_not_open: 'betaNotOpen',
  server_error: 'serverError',
  output_failed: 'outputFailed',
  preview_failed: 'previewFailed',
  holo_capture_unavailable: 'holoCaptureUnavailable',
  holo_capture_failed: 'holoCaptureFailed',
} as const

type ApiErrorCode = keyof typeof CODE_KEYS

export function translateApiError(
  locale: Locale,
  code: string | undefined | null,
  fallback?: string | null,
): string {
  if (!code || !(code in CODE_KEYS)) {
    return fallback?.trim() || ''
  }
  const key = CODE_KEYS[code as ApiErrorCode]
  const msg = getMessages(locale).apiErrors[key]
  if (typeof msg === 'string' && msg.includes('{detail}') && fallback) {
    const detail = fallback.replace(/^[^:：]+[:：]\s*/, '').trim()
    return msg.replace('{detail}', detail || fallback)
  }
  return msg
}
