import { api } from '@/api/client'
import type { Admin, User } from '@/api/auth'

export type PageResult<T> = {
  items: T[]
  total: number
  page: number
  page_size: number
}

export type DashboardStats = {
  users_total: number
  today_register: number
  today_checkin: number
  today_ai_runs: number
  points_credited_total: number
  points_debited_total: number
  wallet_recharge_total: number
  newbie_gift_claimed: number
  newbie_gift_unclaimed: number
  failures_24h: number
}

export type LedgerRow = {
  id: string
  account: string
  delta: number
  balance_after: number
  kind: string
  remark: string
  created_at: string
}

export type Announcement = {
  id: string
  title: string
  body: string
  is_published: boolean
  created_at: string
  updated_at?: string | null
}

export const adminApi = {
  dashboard: () => api.get<DashboardStats>('/admin/dashboard'),
  users: (params: {
    q?: string
    member_tier?: string
    frozen?: boolean
    page?: number
    page_size?: number
  }) => {
    const qs = new URLSearchParams()
    if (params.q) qs.set('q', params.q)
    if (params.member_tier) qs.set('member_tier', params.member_tier)
    if (params.frozen !== undefined) qs.set('frozen', String(params.frozen))
    qs.set('page', String(params.page ?? 1))
    qs.set('page_size', String(params.page_size ?? 20))
    return api.get<PageResult<User>>(`/admin/users?${qs}`)
  },
  userDetail: (id: string) => api.get<{ user: User; point_ledger: unknown[]; wallet_ledger: unknown[] }>(`/admin/users/${id}`),
  adjustPoints: (id: string, body: { delta: number; remark: string }) =>
    api.post<User>(`/admin/users/${id}/adjust-points`, body),
  adjustWallet: (id: string, body: { delta: number; remark: string }) =>
    api.post<User>(`/admin/users/${id}/adjust-wallet`, body),
  freeze: (id: string, frozen: boolean) =>
    api.post<User>(`/admin/users/${id}/freeze`, { frozen }),
  forceLogout: (id: string) => api.post<User>(`/admin/users/${id}/force-logout`),
  exportUsers: async (params: { q?: string; member_tier?: string; frozen?: boolean }) => {
    const qs = new URLSearchParams()
    if (params.q) qs.set('q', params.q)
    if (params.member_tier) qs.set('member_tier', params.member_tier)
    if (params.frozen !== undefined) qs.set('frozen', String(params.frozen))
    const response = await fetch(`/api/admin/users/export?${qs}`, { credentials: 'include' })
    if (!response.ok) throw new Error('导出失败')
    return response.text()
  },
  pointLedgers: (params: { q?: string; kind?: string; page?: number }) => {
    const qs = new URLSearchParams()
    if (params.q) qs.set('q', params.q)
    if (params.kind) qs.set('kind', params.kind)
    qs.set('page', String(params.page ?? 1))
    return api.get<PageResult<LedgerRow>>(`/admin/point-ledgers?${qs}`)
  },
  walletLedgers: (params: { q?: string; page?: number }) => {
    const qs = new URLSearchParams()
    if (params.q) qs.set('q', params.q)
    qs.set('page', String(params.page ?? 1))
    return api.get<PageResult<LedgerRow>>(`/admin/wallet-ledgers?${qs}`)
  },
  invites: (page = 1) => api.get<PageResult<User>>(`/admin/invites?page=${page}`),
  sessions: (params: { q?: string; page?: number }) => {
    const qs = new URLSearchParams()
    if (params.q) qs.set('q', params.q)
    qs.set('page', String(params.page ?? 1))
    return api.get<
      PageResult<{
        user_id: string
        account: string
        display_name: string
        session_count: number
        last_updated: string | null
      }>
    >(`/admin/sessions?${qs}`)
  },
  announcements: () => api.get<Announcement[]>('/admin/announcements'),
  createAnnouncement: (body: { title: string; body: string; is_published: boolean }) =>
    api.post<Announcement>('/admin/announcements', body),
  updateAnnouncement: (
    id: string,
    body: { title: string; body: string; is_published: boolean },
  ) => api.patch<Announcement>(`/admin/announcements/${id}`, body),
  settings: () => api.get<Record<string, string>>('/admin/settings'),
  updateSettings: (body: Record<string, unknown>) =>
    api.put<Record<string, string>>('/admin/settings', body),
  auditLogs: (page = 1) =>
    api.get<
      PageResult<{
        id: string
        admin_username: string
        action: string
        target_type: string
        target_id: string
        detail: string
        created_at: string
      }>
    >(`/admin/audit-logs?page=${page}`),
  batchGrant: (body: { amount: number; remark: string; accounts?: string[] | null }) =>
    api.post<{ granted_users: number; amount: number }>('/admin/batch-grant', body),
  admins: () => api.get<Admin[]>('/admin/admins'),
  createAdmin: (body: { username: string; password: string; display_name: string }) =>
    api.post<Admin>('/admin/admins', body),
  changePassword: (body: {
    old_password: string
    new_password: string
    new_password_confirm: string
  }) => api.post<void>('/admin/admins/me/password', body),
}
