import { api } from '@/api/client'

export type User = {
  id: string
  account: string
  display_name: string
  username: string
  member_tier: string
  wallet_balance: number
  points_balance: number
  points_spent_total: number
  invite_reward_claimed: boolean
  newbie_gift_claimed?: boolean
  newbie_gift_eligible?: boolean
  is_frozen?: boolean
  last_checkin_date: string | null
  avatar_url: string | null
  next_tier: string | null
  points_to_next_tier: number
  created_at?: string | null
}

export type Admin = {
  id: string
  username: string
  display_name: string
  created_at?: string | null
}

export type LoginBody = {
  account: string
  password: string
  invite_code?: string
}

export type RegisterBody = {
  account: string
  display_name: string
  password: string
  password_confirm: string
  invite_code?: string
}

/** 兼容旧调用：username 映射为 account。 */
export type Credentials = { username: string; password: string; invite_code?: string }

export const authApi = {
  register: (body: RegisterBody) => api.post<User>('/auth/register', body),
  login: (body: LoginBody) => api.post<User>('/auth/login', body),
  logout: () => api.post<void>('/auth/logout'),
  me: () => api.get<User>('/auth/me'),
  adminLogin: (body: { username: string; password: string }) =>
    api.post<Admin>('/auth/admin/login', body),
  adminLogout: () => api.post<void>('/auth/admin/logout'),
  adminMe: () => api.get<Admin>('/auth/admin/me'),
}
