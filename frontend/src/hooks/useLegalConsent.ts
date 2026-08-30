import { useCallback, useState } from 'react'
import { LEGAL_CONSENT_SESSION_KEY } from '../content/legalTerms'

function readStoredConsent(): boolean {
  try {
    return sessionStorage.getItem(LEGAL_CONSENT_SESSION_KEY) === '1'
  } catch {
    return false
  }
}

export function useLegalConsent() {
  const [accepted, setAccepted] = useState(readStoredConsent)
  const [checked, setChecked] = useState(false)

  const accept = useCallback(() => {
    try {
      sessionStorage.setItem(LEGAL_CONSENT_SESSION_KEY, '1')
    } catch {
      /* ignore */
    }
    setAccepted(true)
  }, [])

  return { accepted, checked, setChecked, accept }
}
