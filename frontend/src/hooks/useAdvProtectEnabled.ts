import { useEffect, useState } from 'react'

export function useAdvProtectEnabled(): boolean {
  const [enabled, setEnabled] = useState(false)
  useEffect(() => {
    let cancelled = false
    fetch('/api/adv-protect/status')
      .then((res) => res.json())
      .then((body) => {
        if (!cancelled && body && body.enabled) setEnabled(true)
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [])
  return enabled
}
