import { getMessages } from '../i18n/messages'
import type { Locale } from '../i18n/types'

const CODE_PREFIX = 'client:'

export function formatClientError(locale: Locale, err: unknown, fallback = ''): string {
  const raw = err instanceof Error ? err.message : typeof err === 'string' ? err : ''
  if (!raw) return fallback

  const msgs = getMessages(locale).clientErrors

  if (raw === `${CODE_PREFIX}network`) return msgs.networkFailed
  if (raw === `${CODE_PREFIX}holo_network`) return msgs.holoNetworkFailed
  if (raw === `${CODE_PREFIX}holo_result_expired`) return msgs.holoResultExpired
  if (raw === `${CODE_PREFIX}holo_too_large`) return msgs.holoTooLarge
  if (raw === `${CODE_PREFIX}api_not_found`) return msgs.apiNotFound
  if (raw === `${CODE_PREFIX}load_file`) return msgs.loadFileFailed
  if (raw.startsWith(`${CODE_PREFIX}http:`)) {
    const status = raw.slice(`${CODE_PREFIX}http:`.length)
    return msgs.requestFailed.replace('{status}', status || '?')
  }

  return raw || fallback
}
