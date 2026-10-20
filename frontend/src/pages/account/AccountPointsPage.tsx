import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { accountApi } from '@/api/account'
import { errorMessage, useAuthActions, useCurrentUser } from '@/hooks/useAuth'

const KIND_LABEL: Record<string, string> = {
  register_bonus: '注册赠送',
  checkin: '每日签到',
  mock_recharge: '模拟充值',
  invite_reward: '邀请奖励',
  consume_agent: 'Agent 消耗',
  consume_generation: '文生图消耗',
}

export default function AccountPointsPage() {
  const { user } = useCurrentUser()
  const { cacheUser } = useAuthActions()
  const queryClient = useQueryClient()
  const [yuan, setYuan] = useState('10')
  const [hint, setHint] = useState('')

  const ledger = useQuery({
    queryKey: ['account', 'ledger'],
    queryFn: () => accountApi.ledger(),
  })

  const refreshUser = async () => {
    const me = await accountApi.me()
    cacheUser(me.user)
    void queryClient.invalidateQueries({ queryKey: ['account'] })
  }

  const checkin = useMutation({
    mutationFn: () => accountApi.checkin(),
    onSuccess: async (result) => {
      setHint(`签到成功，+${result.points_gained} 积分`)
      await refreshUser()
      void ledger.refetch()
    },
  })

  const recharge = useMutation({
    mutationFn: () => accountApi.mockRecharge(Number(yuan)),
    onSuccess: async (result) => {
      setHint(`模拟充值成功，+${result.points_gained} 积分`)
      await refreshUser()
      void ledger.refetch()
    },
  })

  if (!user) return null
  const checkedToday = user.last_checkin_date === new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Shanghai' })

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-ink text-xl font-semibold">积分与会员</h1>
        <p className="text-muted mt-1 text-sm">
          当前 {user.points_balance} 积分 · {user.member_tier}
          {user.next_tier ? ` · 距 ${user.next_tier} 还需消耗 ${user.points_to_next_tier}` : ''}
        </p>
      </div>

      <section className="space-y-3">
        <h2 className="text-ink text-sm font-medium">每日签到</h2>
        <button
          type="button"
          disabled={checkin.isPending || checkedToday}
          onClick={() => checkin.mutate()}
          className="bg-ink rounded-control px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {checkedToday ? '今日已签到' : '立即签到'}
        </button>
        {checkin.isError && <p className="text-danger text-sm">{errorMessage(checkin.error)}</p>}
      </section>

      <section className="space-y-3">
        <h2 className="text-ink text-sm font-medium">模拟充值</h2>
        <p className="text-muted text-xs">测试用：1 元 = 10 积分，单次不超过 1000 元，非真实支付。</p>
        <div className="flex max-w-sm items-center gap-2">
          <input
            type="number"
            min={1}
            max={1000}
            value={yuan}
            onChange={(event) => setYuan(event.target.value)}
            className="border-line rounded-control w-28 border px-3 py-2 text-sm outline-none focus:border-brand"
          />
          <span className="text-muted text-sm">元 → {(Number(yuan) || 0) * 10} 积分</span>
          <button
            type="button"
            disabled={recharge.isPending}
            onClick={() => recharge.mutate()}
            className="bg-brand-strong rounded-control px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            充值
          </button>
        </div>
        {recharge.isError && <p className="text-danger text-sm">{errorMessage(recharge.error)}</p>}
      </section>

      {hint && <p className="text-success text-sm">{hint}</p>}

      <section>
        <h2 className="text-ink mb-3 text-sm font-medium">积分流水</h2>
        <ul className="divide-line border-line divide-y rounded-[12px] border">
          {(ledger.data ?? []).map((item) => (
            <li key={item.id} className="flex items-center justify-between gap-3 px-3 py-2.5 text-sm">
              <div className="min-w-0">
                <p className="text-ink truncate">{KIND_LABEL[item.kind] ?? item.kind}</p>
                <p className="text-muted truncate text-xs">{item.remark || item.created_at}</p>
              </div>
              <span className={`tabular-nums font-medium ${item.delta >= 0 ? 'text-success' : 'text-danger'}`}>
                {item.delta >= 0 ? `+${item.delta}` : item.delta}
              </span>
            </li>
          ))}
          {!ledger.data?.length && <li className="text-muted px-3 py-4 text-sm">暂无流水</li>}
        </ul>
      </section>
    </div>
  )
}
