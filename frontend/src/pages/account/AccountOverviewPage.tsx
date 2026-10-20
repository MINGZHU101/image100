import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { accountApi } from '@/api/account'
import { useCurrentUser } from '@/hooks/useAuth'
import UserAvatar from '@/components/UserAvatar'

export default function AccountOverviewPage() {
  const { user } = useCurrentUser()
  const { data } = useQuery({
    queryKey: ['account', 'me'],
    queryFn: () => accountApi.me(),
  })
  const profile = data?.user ?? user
  const usage = data?.usage

  if (!profile) return null

  return (
    <div className="space-y-6">
      <div className="flex items-start gap-4">
        <UserAvatar user={profile} size="lg" />
        <div className="min-w-0 flex-1">
          <h1 className="text-ink text-xl font-semibold">{profile.display_name}</h1>
          <p className="text-muted mt-1 text-sm">账号 {profile.account}</p>
          <p className="text-muted mt-1 text-sm">
            会员 <span className="text-brand-strong font-medium">{profile.member_tier}</span>
            {' · '}积分 {profile.points_balance}
          </p>
        </div>
        <Link to="/account/profile" className="text-brand-strong text-sm hover:underline">
          编辑资料
        </Link>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label="当前积分" value={String(profile.points_balance)} />
        <Stat label="会员等级" value={profile.member_tier} />
        <Stat
          label="今日 AI"
          value={
            usage?.points_unlimited
              ? '不限'
              : `${usage?.daily_used ?? 0}/${usage?.daily_limit ?? '—'}`
          }
        />
        <Stat
          label="并发占用"
          value={`${usage?.concurrent_active ?? 0}/${usage?.concurrent_limit ?? 1}`}
        />
      </div>

      {profile.next_tier && (
        <p className="text-muted text-sm">
          距升级「{profile.next_tier}」还需消耗 {profile.points_to_next_tier} 积分
        </p>
      )}

      <div className="flex flex-wrap gap-2">
        <Link
          to="/account/points"
          className="bg-ink rounded-control px-3.5 py-2 text-sm font-medium text-white"
        >
          签到 / 充值
        </Link>
        <Link
          to="/account/invite"
          className="border-line hover:bg-soft rounded-control border px-3.5 py-2 text-sm"
        >
          邀请好友
        </Link>
      </div>
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="border-line rounded-card border bg-soft/60 px-3 py-3">
      <p className="text-muted text-xs">{label}</p>
      <p className="text-ink mt-1 text-lg font-semibold tabular-nums">{value}</p>
    </div>
  )
}
