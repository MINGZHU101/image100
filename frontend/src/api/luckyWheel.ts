import { api } from '@/api/client'

export type WheelSlot = {
  index: number
  kind: string
  label: string
  points: number
  jackpot: boolean
  drawn: boolean
}

export type WheelState = {
  period_ym: string
  countdown: { days: number; hours: number; minutes: number; total_seconds: number }
  wallet_balance: number
  points_balance: number
  member_tier: string
  spin_count: number
  max_spins: number
  next_cost_yuan: number | null
  exhausted: boolean
  slots: WheelSlot[]
  history: Array<{
    spin_index: number
    cost_yuan: number
    slot_index: number
    prize_kind: string
    prize_label: string
    points_awarded: number
    is_jackpot: boolean
    created_at: string
  }>
}

export type SpinResult = {
  spin_index: number
  cost_yuan: number
  slot_index: number
  prize_kind: string
  prize_label: string
  points_awarded: number
  is_jackpot: boolean
  remark: string
  member_tier: string
  wallet_balance: number
  points_balance: number
}

export type BarrageItem = {
  masked_name: string
  prize_label: string
  created_at: string
}

export const luckyWheelApi = {
  state: () => api.get<WheelState>('/lucky-wheel/state'),
  barrage: () => api.get<BarrageItem[]>('/lucky-wheel/barrage'),
  spin: (confirmed: boolean) =>
    api.post<{ result: SpinResult; state: WheelState }>('/lucky-wheel/spin', {
      confirmed,
    }),
}
