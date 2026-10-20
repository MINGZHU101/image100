import { api, apiError } from '@/api/client'
import type { User } from '@/api/auth'

export type Usage = {
  daily_used: number
  daily_limit: number | null
  concurrent_active: number
  concurrent_limit: number
  points_unlimited: boolean
}

export type LedgerItem = {
  id: string
  delta: number
  balance_after: number
  kind: string
  remark: string
  created_at: string
}

export type InviteCode = {
  code: string
  expires_at: string
  ttl_seconds: number
}

export const accountApi = {
  me: () => api.get<{ user: User; usage: Usage }>('/account/me'),
  usage: () => api.get<Usage>('/account/usage'),
  ledger: (limit = 50) => api.get<LedgerItem[]>(`/account/ledger?limit=${limit}`),
  walletLedger: (limit = 50) =>
    api.get<LedgerItem[]>(`/account/wallet-ledger?limit=${limit}`),
  checkin: () => api.post<{ points_gained: number; points_balance: number }>('/account/checkin'),
  mockRecharge: (yuan: number) =>
    api.post<{ yuan: number; wallet_balance: number; points_balance: number }>(
      '/account/mock-recharge',
      { yuan },
    ),
  exchangePoints: (yuan: number) =>
    api.post<{
      yuan: number
      points_gained: number
      wallet_balance: number
      points_balance: number
    }>('/account/exchange-points', { yuan }),
  updateDisplayName: (display_name: string) =>
    api.patch<User>('/account/display-name', { display_name }),
  changePassword: (body: {
    old_password: string
    new_password: string
    new_password_confirm: string
  }) => api.post<void>('/account/password', body),
  createInvite: () => api.post<InviteCode>('/account/invite-codes'),
  activeInvite: () => api.get<InviteCode | null>('/account/invite-codes/active'),
  redeemInvite: (invite_code: string) =>
    api.post<User>('/account/invite-codes/redeem', { invite_code }),
  claimNewbieGift: () =>
    api.post<{ points_gained: number; points_balance: number; newbie_gift_claimed: boolean }>(
      '/account/newbie-gift',
    ),
  announcements: () =>
    api.get<{ id: string; title: string; body: string; created_at: string }[]>(
      '/account/announcements',
    ),
  latestAnnouncement: () =>
    api.get<{ id: string; title: string; body: string; created_at: string } | null>(
      '/account/announcements/latest',
    ),
  uploadAvatar: async (file: File) => {
    const form = new FormData()
    form.append('file', file)
    const response = await fetch('/api/account/avatar', {
      method: 'POST',
      credentials: 'include',
      body: form,
    })
    if (!response.ok) throw await apiError(response, '头像上传失败')
    return (await response.json()) as User
  },
}
