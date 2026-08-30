import { type ReactNode } from 'react'

/** Self-host edition has no accounts. Kept so leftover imports compile. */
export function AuthProvider({ children }: { children: ReactNode }) {
  return children
}

export function useAuth(): never {
  throw new Error('Auth is not available in jingwei-selfhost')
}
