import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { accountApi } from '@/api/account'
import RechargeModal from '@/components/RechargeModal'
import { errorMessage, useAuthActions, useCurrentUser } from '@/hooks/useAuth'

const POINT_KIND_LABEL: Record<string, string> = {
  register_bonus: '注册赠送',
  newbie_gift: '新手礼包',
  admin_adjust: '管理员调整',
  admin_batch: '活动发放',
  checkin: '每日签到',
  invite_reward: '邀请奖励',
  exchange_from_wallet: '余额兑换',
  consume_agent: 'Agent 消耗',
  consume_generation: '文生图消耗',
  consume_copywriting: '文案生成',
  lucky_wheel: '幸运大转盘',
  mock_recharge: '模拟充值（旧）',
}

const WALLET_KIND_LABEL: Record<string, string> = {
  mock_recharge: '模拟充值',
  exchange_points: '兑换积分',
  lucky_wheel: '幸运大转盘',
}

export default function AccountPointsPage() {
  const { user } = useCurrentUser()
  const { cacheUser } = useAuthActions()
  const queryClient = useQueryClient()
  const [hint, setHint] = useState('')
  const [rechargeOpen, setRechargeOpen] = useState(false)
  const [exchangeYuan, setExchangeYuan] = useState('10')

  const ledger = useQuery({
    queryKey: ['account', 'ledger'],
    queryFn: () => accountApi.ledger(),
  })
  const walletLedger = useQuery({
    queryKey: ['account', 'wallet-ledger'],
    queryFn: () => accountApi.walletLedger(),
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
    mutationFn: (yuan: number) => accountApi.mockRecharge(yuan),
    onSuccess: async (result) => {
      setHint(`充值成功，余额 +¥${result.yuan}（当前 ¥${result.wallet_balance}）`)
      setRechargeOpen(false)
      await refreshUser()
      void walletLedger.refetch()
    },
  })

  const exchange = useMutation({
    mutationFn: () => accountApi.exchangePoints(Number(exchangeYuan)),
    onSuccess: async (result) => {
      setHint(`兑换成功：¥${result.yuan} → +${result.points_gained} 积分`)
      await refreshUser()
      void ledger.refetch()
      void walletLedger.refetch()
    },
  })

  if (!user) return null
  const checkedToday =
    user.last_checkin_date ===
    new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Shanghai' })
  const wallet = user.wallet_balance ?? 0
  const exchangeAmount = Math.floor(Number(exchangeYuan) || 0)
  const exchangePoints = exchangeAmount * 10

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-ink text-xl font-semibold">积分与会员</h1>
        <p className="text-muted mt-1 text-sm">
          会员 {user.member_tier}
          {user.next_tier ? ` · 距 ${user.next_tier} 还需消耗 ${user.points_to_next_tier}` : ''}
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="border-line rounded-card border bg-soft/60 px-4 py-3">
          <p className="text-muted text-xs">账户余额</p>
          <p className="text-ink mt-1 text-2xl font-semibold tabular-nums">¥{wallet}</p>
        </div>
        <div className="border-line rounded-card border bg-soft/60 px-4 py-3">
          <p className="text-muted text-xs">积分余额</p>
          <p className="text-ink mt-1 text-2xl font-semibold tabular-nums">{user.points_balance}</p>
        </div>
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
        <p className="text-muted text-xs">充值优先进入余额，再自行兑换积分。测试用，非真实支付。</p>
        <button
          type="button"
          onClick={() => setRechargeOpen(true)}
          className="bg-brand-strong rounded-control px-4 py-2 text-sm font-medium text-white"
        >
          充值
        </button>
      </section>

      <section className="space-y-3">
        <h2 className="text-ink text-sm font-medium">余额兑换积分</h2>
        <p className="text-muted text-xs">汇率：1 元 = 10 积分</p>
        <div className="flex max-w-sm flex-wrap items-center gap-2">
          <input
            type="number"
            min={1}
            max={wallet || 1}
            value={exchangeYuan}
            onChange={(event) => setExchangeYuan(event.target.value)}
            className="border-line focus:border-brand rounded-control w-28 border px-3 py-2 text-sm outline-none"
          />
          <span className="text-muted text-sm">
            元 → {exchangeAmount > 0 ? exchangePoints : 0} 积分
          </span>
          <button
            type="button"
            disabled={
              exchange.isPending || exchangeAmount < 1 || exchangeAmount > wallet
            }
            onClick={() => exchange.mutate()}
            className="bg-ink rounded-control px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            兑换
          </button>
        </div>
        {exchange.isError && (
          <p className="text-danger text-sm">{errorMessage(exchange.error)}</p>
        )}
      </section>

      {hint && <p className="text-success text-sm">{hint}</p>}

      <section>
        <h2 className="text-ink mb-3 text-sm font-medium">余额流水</h2>
        <ul className="divide-line border-line divide-y rounded-[12px] border">
          {(walletLedger.data ?? []).map((item) => (
            <li
              key={item.id}
              className="flex items-center justify-between gap-3 px-3 py-2.5 text-sm"
            >
              <div className="min-w-0">
                <p className="text-ink truncate">
                  {WALLET_KIND_LABEL[item.kind] ?? item.kind}
                </p>
                <p className="text-muted truncate text-xs">
                  {item.remark || item.created_at}
                </p>
              </div>
              <span
                className={`tabular-nums font-medium ${item.delta >= 0 ? 'text-success' : 'text-danger'}`}
              >
                {item.delta >= 0 ? `+¥${item.delta}` : `-¥${Math.abs(item.delta)}`}
              </span>
            </li>
          ))}
          {!walletLedger.data?.length && (
            <li className="text-muted px-3 py-4 text-sm">暂无余额流水</li>
          )}
        </ul>
      </section>

      <section>
        <h2 className="text-ink mb-3 text-sm font-medium">积分流水</h2>
        <ul className="divide-line border-line divide-y rounded-[12px] border">
          {(ledger.data ?? []).map((item) => (
            <li
              key={item.id}
              className="flex items-center justify-between gap-3 px-3 py-2.5 text-sm"
            >
              <div className="min-w-0">
                <p className="text-ink truncate">
                  {POINT_KIND_LABEL[item.kind] ?? item.kind}
                </p>
                <p className="text-muted truncate text-xs">
                  {item.remark || item.created_at}
                </p>
              </div>
              <span
                className={`tabular-nums font-medium ${item.delta >= 0 ? 'text-success' : 'text-danger'}`}
              >
                {item.delta >= 0 ? `+${item.delta}` : item.delta}
              </span>
            </li>
          ))}
          {!ledger.data?.length && (
            <li className="text-muted px-3 py-4 text-sm">暂无积分流水</li>
          )}
        </ul>
      </section>

      <RechargeModal
        open={rechargeOpen}
        walletBalance={wallet}
        busy={recharge.isPending}
        error={recharge.isError ? errorMessage(recharge.error) : undefined}
        onClose={() => {
          setRechargeOpen(false)
          recharge.reset()
        }}
        onConfirm={(yuan) => recharge.mutate(yuan)}
      />
    </div>
  )
}
