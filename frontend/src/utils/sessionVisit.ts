/** Self-host: no public visit counter. */
export function recordSessionVisit(): Promise<null> {
  return Promise.resolve(null)
}
