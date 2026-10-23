import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import AdminPageHeader from '@/components/admin/AdminPageHeader'
import { adminUi } from '@/components/admin/adminStyles'
import { adminApi } from '@/api/admin'

type StatTone = 'brand' | 'ink' | 'success' | 'warn'

const TONE_BAR: Record<StatTone, string> = {
  brand: 'from-brand/80 to-brand-soft',
  ink: 'from-ink/80 to-soft',
  success: 'from-success/70 to-brand-soft',
  warn: 'from-danger/70 to-soft',
}

function StatCard({
  label,
  value,
  hint,
  tone = 'brand',
}: {
  label: string
  value: string | number
  hint?: string
  tone?: StatTone
}) {
  return (
    <div className={`${adminUi.panel} relative overflow-hidden p-4`}>
      <div
        className={`absolute inset-x-0 top-0 h-1 bg-gradient-to-r ${TONE_BAR[tone]}`}
        aria-hidden
      />
      <p className="text-muted text-xs font-medium tracking-wide">{label}</p>
      <p className="text-ink mt-2 text-2xl font-semibold tabular-nums tracking-tight">{value}</p>
      {hint ? <p className="text-faint mt-1 text-[11px]">{hint}</p> : null}
    </div>
  )
}

export default function AdminDashboardPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['admin', 'dashboard'],
    queryFn: () => adminApi.dashboard(),
  })

  if (isLoading || !data) {
    return <p className={adminUi.muted}>加载仪表盘…</p>
  }

  const primary = [
    { label: '用户总数', value: data.users_total, hint: '累计注册', tone: 'ink' as const },
    { label: '今日注册', value: data.today_register, hint: '自然日新增', tone: 'brand' as const },
    { label: '今日签到', value: data.today_checkin, hint: '活跃留存', tone: 'success' as const },
    { label: '今日 AI 次数', value: data.today_ai_runs, hint: 'Agent / 生图等', tone: 'brand' as const },
  ]

  const finance = [
    { label: '积分发放累计', value: data.points_credited_total, tone: 'success' as const },
    { label: '积分消耗累计', value: data.points_debited_total, tone: 'ink' as const },
    { label: '余额充值累计', value: `¥${data.wallet_recharge_total}`, tone: 'brand' as const },
    {
      label: '礼包已领 / 未领',
      value: `${data.newbie_gift_claimed} / ${data.newbie_gift_unclaimed}`,
      tone: 'brand' as const,
    },
    {
      label: '近 24h 失败',
      value: data.failures_24h,
      hint: '任务失败需关注',
      tone: (data.failures_24h > 0 ? 'warn' : 'success') as StatTone,
    },
  ]

  const shortcuts = [
    { to: '/admin/users', label: '用户管理', desc: '调账、冻结、导出' },
    { to: '/admin/lucky-wheel', label: '幸运大转盘', desc: '中奖记录与下月奖池' },
    { to: '/admin/announcements', label: '公告管理', desc: '站内通知' },
    { to: '/admin/batch', label: '批量发分', desc: '活动积分发放' },
  ]

  return (
    <div className={adminUi.page}>
      <AdminPageHeader
        title="仪表盘"
        description="一眼掌握注册、活跃、积分与任务健康度。"
      />

      <section>
        <h3 className={`${adminUi.sectionTitle} mb-3`}>今日与规模</h3>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {primary.map((card) => (
            <StatCard key={card.label} {...card} />
          ))}
        </div>
      </section>

      <section>
        <h3 className={`${adminUi.sectionTitle} mb-3`}>积分与余额</h3>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {finance.map((card) => (
            <StatCard key={card.label} {...card} />
          ))}
        </div>
      </section>

      <section className={adminUi.panelPad}>
        <h3 className={adminUi.sectionTitle}>快捷入口</h3>
        <p className={`${adminUi.faint} mt-1`}>常用运营动作，减少在侧栏里来回找。</p>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {shortcuts.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              className="border-line hover:border-brand hover:bg-brand-soft/40 rounded-control block border p-3 transition"
            >
              <p className="text-ink text-sm font-medium">{item.label}</p>
              <p className="text-muted mt-1 text-xs">{item.desc}</p>
            </Link>
          ))}
        </div>
      </section>
    </div>
  )
}
