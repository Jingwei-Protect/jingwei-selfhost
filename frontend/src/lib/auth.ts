/** 前端 API 客户端 — 与 FastAPI 后端通信 */

export interface QuotaInfo {
  available_pixels: number
  next_pixel_countdown: number
  daily_settled_today: boolean
  daily_grant_amount: number
  welcome_gifted_applied: boolean
  daily_allowance: number
  jw_works: number
  claimed_amount?: number
}

export interface UserProfile {
  id: number
  email: string | null
  nickname?: string | null
  afdian_user_id: string | null
  nameplate_unlocked: boolean
  tier: string
  is_admin?: boolean
  total_sponsored: number
  jw_works?: number
  quota?: QuotaInfo
}

export interface SeaPixel {
  x: number
  y: number
  color: string
  user_id: number
  updated_at: number
}

export interface SeaFlipAnchor {
  id: number
  zone_col: number
  zone_row: number
  x: number
  y: number
  user_id: number
  group_id: string | null
  created_at: number
  owner_label?: string
}

export interface SeaPixelsResponse {
  pixels: SeaPixel[]
  server_time: number
  flip_anchors?: SeaFlipAnchor[]
}

export interface FlipStatus {
  flip_stones: number
  flip_stones_max: number
  flip_regen_seconds: number
  flip_next_in_seconds: number
  flip_daily_limit: number
  flip_daily_used: number
  flip_daily_left: number
  anchors?: SeaFlipAnchor[]
}

export interface ZoneWorkSave {
  save_id: number
  save_type: 'draft' | 'final'
  zone_col: number
  zone_row: number
  pixel_count: number
  saved_at: number
  skipped?: boolean
}

export interface NameplateRecord {
  username: string
  image_data: string
  text_effect: 'normal' | 'gold' | 'rainbow'
  frame_style: 'default' | 'sustained' | 'deep' | 'patron'
  updated_at: string
  tier?: string
  total_sponsored?: number
  order?: number
}

export interface AdminWorkSave {
  id: number
  user_id: number
  zone_col: number
  zone_row: number
  save_type: 'draft' | 'final'
  pixel_count: number
  saved_at: number
  email?: string | null
}

export interface WallNameplate extends NameplateRecord {
  order: number
}

const TOKEN_KEY = 'jw-auth-token'

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

export async function apiFetch<T = unknown>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (init.body && !headers.has('Content-Type')) {
    if (!(init.body instanceof FormData)) {
      headers.set('Content-Type', 'application/json')
    }
  }
  let res: Response
  try {
    res = await fetch(path, { ...init, headers })
  } catch {
    throw new Error('client:network')
  }
  if (!res.ok) {
    let detail = `client:http:${res.status}`
    try {
      const err = await res.json() as { detail?: unknown; em?: string }
      if (typeof err.detail === 'string') detail = err.detail
      else if (Array.isArray(err.detail)) {
        detail = err.detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join(', ')
      } else if (err.em) detail = err.em
    } catch {
      if (res.status === 404) {
        detail = 'client:api_not_found'
      }
    }
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

export async function fetchMe(): Promise<{ authenticated: boolean; user?: UserProfile }> {
  return apiFetch('/api/auth/me')
}

export async function fetchCommunityStatus(): Promise<{
  authenticated: boolean
  user?: UserProfile
  quota?: QuotaInfo
}> {
  return apiFetch('/api/community/status')
}

export async function loginWithPassword(email: string, password: string) {
  return apiFetch<{ token: string; user: UserProfile }>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
}

export async function registerWithPassword(email: string, password: string, nickname?: string) {
  return apiFetch<{ token: string; user: UserProfile }>('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, password, nickname: nickname?.trim() || undefined }),
  })
}

export async function updateMyNickname(nickname: string) {
  return apiFetch<{ user: UserProfile }>('/api/auth/me/nickname', {
    method: 'PATCH',
    body: JSON.stringify({ nickname }),
  })
}

export async function deleteMyAccount() {
  return apiFetch<{ ok: boolean }>('/api/auth/me', { method: 'DELETE' })
}

export async function claimDailyPixels() {
  return apiFetch<{ quota: QuotaInfo; user: UserProfile }>('/api/community/claim-daily', {
    method: 'POST',
  })
}

export async function redeemClaimCode(code: string) {
  return apiFetch<{
    claim: { claimed_pixels?: number }
    user: UserProfile
  }>('/api/sponsor/redeem', {
    method: 'POST',
    body: JSON.stringify({ code }),
  })
}

export async function getSeaPixels(
  since = 0,
  zone?: { zoneCol: number; zoneRow: number },
): Promise<SeaPixelsResponse> {
  const params = new URLSearchParams()
  if (since > 0) params.set('since', String(since))
  if (zone) {
    params.set('zone_col', String(zone.zoneCol))
    params.set('zone_row', String(zone.zoneRow))
  }
  const qs = params.toString()
  return apiFetch(`/api/community/sea/pixels${qs ? `?${qs}` : ''}`)
}

export async function getZonePixels(zoneCol: number, zoneRow: number) {
  return apiFetch<{ pixels: SeaPixel[]; server_time: number }>(
    `/api/community/sea/zone-pixels?zone_col=${zoneCol}&zone_row=${zoneRow}`,
  )
}

export async function paintSeaPixel(x: number, y: number, color: string) {
  return apiFetch<{ pixel: SeaPixel; quota: QuotaInfo }>('/api/community/sea/paint', {
    method: 'POST',
    body: JSON.stringify({ x, y, color }),
  })
}

export async function eraseSeaPixel(x: number, y: number) {
  return apiFetch<{ pixel: { x: number; y: number; erased: true }; quota: QuotaInfo }>(
    '/api/community/sea/erase',
    { method: 'POST', body: JSON.stringify({ x, y }) },
  )
}

export async function postSeaHeartbeat() {
  return apiFetch<{ quota: QuotaInfo }>('/api/community/sea/heartbeat', { method: 'POST' })
}

export async function getZonePresence(zoneCol: number, zoneRow: number) {
  return apiFetch<{ editors: number }>(
    `/api/community/sea/zone-presence?zone_col=${zoneCol}&zone_row=${zoneRow}`,
  )
}

export async function touchZonePresence(zoneCol: number, zoneRow: number) {
  return apiFetch<{ editors: number }>('/api/community/sea/zone-presence', {
    method: 'POST',
    body: JSON.stringify({ zone_col: zoneCol, zone_row: zoneRow }),
  })
}

export async function leaveZonePresence() {
  return apiFetch('/api/community/sea/zone-presence', { method: 'DELETE' })
}

export async function getZoneWorkSaves(zoneCol: number, zoneRow: number) {
  return apiFetch<{
    draft: ZoneWorkSave | null
    final: ZoneWorkSave | null
    has_draft: boolean
    has_final: boolean
  }>(`/api/community/sea/save-work?zone_col=${zoneCol}&zone_row=${zoneRow}`)
}

export async function saveZoneDraft(zoneCol: number, zoneRow: number) {
  return apiFetch<ZoneWorkSave>('/api/community/sea/save-work/draft', {
    method: 'POST',
    body: JSON.stringify({ zone_col: zoneCol, zone_row: zoneRow }),
  })
}

export async function saveZoneFinal(zoneCol: number, zoneRow: number) {
  return apiFetch<ZoneWorkSave>('/api/community/sea/save-work/final', {
    method: 'POST',
    body: JSON.stringify({ zone_col: zoneCol, zone_row: zoneRow }),
  })
}

export async function getFlipStatus(zoneCol?: number, zoneRow?: number) {
  const params = new URLSearchParams()
  if (zoneCol != null) params.set('zone_col', String(zoneCol))
  if (zoneRow != null) params.set('zone_row', String(zoneRow))
  const qs = params.toString()
  return apiFetch<FlipStatus>(`/api/community/sea/flip${qs ? `?${qs}` : ''}`)
}

export interface FlipPlaceResult {
  status: 'pending' | 'flipped'
  flip: FlipStatus
  anchor_id?: number
  x?: number
  y?: number
  color?: string
  group_id?: string
  flipped_pixels?: {
    x: number
    y: number
    color: string
    user_id: number
    prev_color?: string
    prev_user_id?: number
  }[]
}

export async function placeFlipStone(
  zoneCol: number,
  zoneRow: number,
  x: number,
  y: number,
  color: string,
) {
  return apiFetch<FlipPlaceResult>('/api/community/sea/flip/place', {
    method: 'POST',
    body: JSON.stringify({ zone_col: zoneCol, zone_row: zoneRow, x, y, color }),
  })
}

export async function displaceFlipStone(zoneCol: number, zoneRow: number, x: number, y: number) {
  return apiFetch<{ displaced: boolean; x: number; y: number; flip: FlipStatus }>(
    '/api/community/sea/flip/displace',
    { method: 'POST', body: JSON.stringify({ zone_col: zoneCol, zone_row: zoneRow, x, y }) },
  )
}

export async function cancelPendingFlip(zoneCol: number, zoneRow: number) {
  return apiFetch<{ cancelled: boolean; flip?: FlipStatus }>('/api/community/sea/flip/cancel-pending', {
    method: 'POST',
    body: JSON.stringify({ zone_col: zoneCol, zone_row: zoneRow, x: 0, y: 0 }),
  })
}

export async function undoFlipGroup(
  zoneCol: number,
  zoneRow: number,
  groupId: string,
  restores: { x: number; y: number; prev_color: string | null; prev_user_id: number | null }[],
) {
  return apiFetch<{
    undone: boolean
    group_id: string
    restored_pixels: { x: number; y: number; color: string | null; user_id: number | null }[]
    flip: FlipStatus
  }>('/api/community/sea/flip/undo', {
    method: 'POST',
    body: JSON.stringify({
      zone_col: zoneCol,
      zone_row: zoneRow,
      group_id: groupId,
      restores,
    }),
  })
}

export async function getMyNameplate() {
  return apiFetch<{ nameplate: NameplateRecord | null }>('/api/nameplates/me')
}

export async function saveMyNameplate(
  username: string,
  image_data: string,
  text_effect: 'normal' | 'gold' | 'rainbow',
  frame_style: 'default' | 'sustained' | 'deep' | 'patron' = 'default',
) {
  return apiFetch<{ nameplate: NameplateRecord }>('/api/nameplates/me', {
    method: 'PUT',
    body: JSON.stringify({ username, image_data, text_effect, frame_style }),
  })
}

export async function deleteMyNameplate() {
  return apiFetch<{ ok: boolean; deleted: boolean }>('/api/nameplates/me', { method: 'DELETE' })
}

export async function getNameplateWall(limit = 60, offset = 0) {
  return apiFetch<{ nameplates: WallNameplate[]; total: number }>(
    `/api/nameplates/wall?limit=${limit}&offset=${offset}`,
  )
}

export async function adminListWorkSaves(limit = 100, offset = 0) {
  return apiFetch<{ saves: AdminWorkSave[] }>(
    `/api/admin/sea/work-saves?limit=${limit}&offset=${offset}`,
  )
}

export async function adminRestoreWorkSave(saveId: number) {
  return apiFetch(`/api/admin/sea/work-saves/${saveId}/restore`, { method: 'POST' })
}

export async function adminDeleteZone(zoneCol: number, zoneRow: number) {
  return apiFetch('/api/admin/sea/zone', {
    method: 'DELETE',
    body: JSON.stringify({ zone_col: zoneCol, zone_row: zoneRow }),
  })
}

export async function adminDeleteUserPixels(userId: number) {
  return apiFetch(`/api/admin/sea/user/${userId}/pixels`, { method: 'DELETE' })
}

export async function adminBanUser(userId: number, reason: string, days: number | null) {
  return apiFetch(`/api/admin/users/${userId}/ban`, {
    method: 'POST',
    body: JSON.stringify({ reason, days: days ?? 0 }),
  })
}

export async function adminUnbanUser(userId: number) {
  return apiFetch(`/api/admin/users/${userId}/unban`, { method: 'POST' })
}

export type FeedbackCategory = 'bug' | 'feature' | 'account' | 'other'
export type FeedbackPageSource = 'protect' | 'verify' | 'delivery' | 'community' | 'support' | 'footer' | 'direct'

export interface FeedbackSubmitResult {
  id: number
  created_at: number
  message: string
}

export interface AdminFeedbackItem {
  id: number
  user_id: number | null
  user_email: string | null
  contact_email: string | null
  category: FeedbackCategory
  title: string
  body: string
  page_source: string
  context: Record<string, unknown> | null
  has_screenshot: boolean
  admin_reply: string | null
  admin_status: string
  created_at: number
  replied_at: number | null
}

export interface InboxAnnouncement {
  id: number
  title: string
  body: string
  created_at: number
  read: boolean
  read_at: number | null
}

export interface InboxFeedbackReply {
  id: number
  category: FeedbackCategory
  title: string
  body: string
  admin_reply: string
  replied_at: number | null
  created_at: number
  read: boolean
}

export interface InboxPayload {
  unread_count: number
  announcements: InboxAnnouncement[]
  feedback_replies: InboxFeedbackReply[]
}

export interface AdminRegisteredUser {
  id: number
  email: string | null
  tier: string
  total_sponsored: number
  nameplate_unlocked: boolean
  jw_works: number
  created_at: string
  banned_until: string | null
}

export interface AdminAnnouncement {
  id: number
  title: string
  body: string
  published: boolean
  created_at: number
  updated_at: number
}

export async function submitFeedback(form: FormData) {
  return apiFetch<FeedbackSubmitResult>('/api/feedback', { method: 'POST', body: form })
}

export async function adminListFeedback(limit = 100, offset = 0) {
  return apiFetch<{ feedback: AdminFeedbackItem[] }>(
    `/api/admin/feedback?limit=${limit}&offset=${offset}`,
  )
}

export async function adminCloseFeedback(id: number) {
  return apiFetch<{ ok: boolean; id: number }>(`/api/admin/feedback/${id}/close`, { method: 'POST' })
}

export function adminFeedbackScreenshotUrl(id: number) {
  return `/api/admin/feedback/${id}/screenshot`
}

export async function adminFetchBlob(path: string): Promise<Blob> {
  const headers = new Headers()
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  let res: Response
  try {
    res = await fetch(path, { headers })
  } catch {
    throw new Error('client:network')
  }
  if (!res.ok) {
    let detail = 'client:load_file'
    try {
      const err = await res.json() as { detail?: string }
      if (typeof err.detail === 'string') detail = err.detail
    } catch {
      /* ignore */
    }
    throw new Error(detail)
  }
  return res.blob()
}

export async function adminReplyFeedback(id: number, reply: string) {
  return apiFetch<{ ok: boolean; id: number; replied_at: number }>(
    `/api/admin/feedback/${id}/reply`,
    { method: 'POST', body: JSON.stringify({ reply }) },
  )
}

export async function fetchMyMessages() {
  return apiFetch<InboxPayload>('/api/me/messages')
}

export async function markAnnouncementRead(id: number) {
  return apiFetch<{ ok: boolean }>(`/api/me/messages/announcements/${id}/read`, { method: 'POST' })
}

export async function markFeedbackReplyRead(id: number) {
  return apiFetch<{ ok: boolean }>(`/api/me/messages/feedback/${id}/read`, { method: 'POST' })
}

export async function adminListUsers(limit = 200, offset = 0) {
  return apiFetch<{ users: AdminRegisteredUser[]; total: number }>(
    `/api/admin/users?limit=${limit}&offset=${offset}`,
  )
}

export async function adminListAnnouncements(limit = 100, offset = 0) {
  return apiFetch<{ announcements: AdminAnnouncement[] }>(
    `/api/admin/announcements?limit=${limit}&offset=${offset}`,
  )
}

export async function adminCreateAnnouncement(title: string, body: string) {
  return apiFetch<{ id: number; title: string; created_at: number }>(
    '/api/admin/announcements',
    { method: 'POST', body: JSON.stringify({ title, body }) },
  )
}

export async function adminPublishAnnouncement(id: number, published: boolean) {
  return apiFetch<{ ok: boolean; id: number; published: boolean }>(
    `/api/admin/announcements/${id}/publish`,
    { method: 'POST', body: JSON.stringify({ published }) },
  )
}
