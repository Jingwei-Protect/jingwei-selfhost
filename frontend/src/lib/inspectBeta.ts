const STORAGE_KEY = 'jingwei_inspect_beta_code_v1'

export function getStoredInspectBetaCode(): string | null {
  try {
    return sessionStorage.getItem(STORAGE_KEY)
  } catch {
    return null
  }
}

export function setStoredInspectBetaCode(code: string): void {
  sessionStorage.setItem(STORAGE_KEY, code.trim())
}

export function clearStoredInspectBetaCode(): void {
  sessionStorage.removeItem(STORAGE_KEY)
}

export function inspectBetaHeaders(): Record<string, string> {
  const code = getStoredInspectBetaCode()
  return code ? { 'X-Inspect-Beta-Code': code } : {}
}

export async function unlockInspectBeta(
  code: string,
): Promise<{ ok: boolean; error?: string; error_code?: string }> {
  const res = await fetch('/api/inspect/beta-unlock', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code: code.trim() }),
  })
  const data = await res.json().catch(() => ({}))
  if (res.ok && data.ok) {
    if (code.trim()) setStoredInspectBetaCode(code)
    return { ok: true }
  }
  return { ok: false, error: data.error, error_code: data.error_code }
}

/** Returns true when the server no longer requires a closed-beta code. */
export async function probeInspectBetaOpen(): Promise<boolean> {
  const result = await unlockInspectBeta(getStoredInspectBetaCode() ?? '')
  return result.ok
}
