import { useQuery } from '@tanstack/react-query'

import { adminApi } from '@/api/admin'

export default function AdminDashboardPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['admin', 'dashboard'],
    queryFn: () => adminApi.dashboard(),
  })

  if (isLoading || !data) {
    return <p className="text-sm text-slate-500">加载仪表盘…</p>
  }

  const cards = [
    { label: '用户总数', value: data.users_total },
    { label: '今日注册', value: data.today_register },
    { label: '今日签到', value: data.today_checkin },
    { label: '今日 AI 次数', value: data.today_ai_runs },
    { label: '积分发放累计', value: data.points_credited_total },
    { label: '积分消耗累计', value: data.points_debited_total },
    { label: '余额充值累计', value: data.wallet_recharge_total },
    { label: '礼包已领 / 未领', value: `${data.newbie_gift_claimed} / ${data.newbie_gift_unclaimed}` },
    { label: '近 24h 失败', value: data.failures_24h },
  ]

  return (
    <div>
      <h2 className="text-lg font-semibold text-slate-800">仪表盘</h2>
      <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {cards.map((card) => (
          <div key={card.label} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs text-slate-500">{card.label}</p>
            <p className="mt-2 text-2xl font-semibold tabular-nums text-slate-800">{card.value}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
