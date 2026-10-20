import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { accountApi } from '@/api/account'
import NewbieGiftModal from '@/components/NewbieGiftModal'
import UserAvatar from '@/components/UserAvatar'
import { errorMessage, useAuthActions, useCurrentUser } from '@/hooks/useAuth'
import { toast } from '@/stores/toasts'

export default function AccountOverviewPage() {
  const { user } = useCurrentUser()
  const { cacheUser } = useAuthActions()
  const queryClient = useQueryClient()
  const [giftOpen, setGiftOpen] = useState(false)

  const { data } = useQuery({
    queryKey: ['account', 'me'],
    queryFn: () => accountApi.me(),
  })
  const { data: announcements } = useQuery({
    queryKey: ['account', 'announcements'],
    queryFn: () => accountApi.announcements(),
  })

  const profile = data?.user ?? user
  const usage = data?.usage
  const eligible = Boolean(profile?.newbie_gift_eligible)
  const claimed = Boolean(profile?.newbie_gift_claimed)

  const claim = useMutation({
    mutationFn: () => accountApi.claimNewbieGift(),
    onSuccess: async (result) => {
      toast(`已领取 ${result.points_gained} 积分`)
      const me = await accountApi.me()
      cacheUser(me.user)
      queryClient.setQueryData(['account', 'me'], me)
      queryClient.invalidateQueries({ queryKey: ['auth', 'me'] })
    },
  })

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
            {' · '}余额 ¥{profile.wallet_balance ?? 0}
            {' · '}积分 {profile.points_balance}
          </p>
        </div>
        {(eligible || claimed) && (
          <button
            type="button"
            onClick={() => setGiftOpen(true)}
            className="shrink-0 transition-transform hover:scale-105 active:scale-95"
            title={claimed ? '礼包已领取' : '领取新手礼包'}
          >
            <img
              src="/newbie-gift.png"
              alt="新手礼包"
              className={`h-14 w-14 object-contain ${claimed ? 'opacity-45 grayscale' : ''}`}
            />
          </button>
        )}
        <Link to="/account/profile" className="text-brand-strong text-sm hover:underline">
          编辑资料
        </Link>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <Stat label="账户余额" value={`¥${profile.wallet_balance ?? 0}`} />
        <Stat label="积分余额" value={String(profile.points_balance)} />
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

      {announcements && announcements.length > 0 && (
        <div className="border-line rounded-card border bg-soft/40 px-4 py-3">
          <p className="text-ink text-sm font-medium">公告</p>
          <ul className="mt-2 space-y-2">
            {announcements.slice(0, 5).map((item) => (
              <li key={item.id} className="text-muted text-sm">
                <span className="text-ink font-medium">{item.title}</span>
                {item.body ? ` — ${item.body}` : ''}
              </li>
            ))}
          </ul>
        </div>
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

      <NewbieGiftModal
        open={giftOpen}
        claimed={claimed}
        busy={claim.isPending}
        error={claim.isError ? errorMessage(claim.error) : undefined}
        onClose={() => {
          setGiftOpen(false)
          claim.reset()
        }}
        onClaim={() => claim.mutate()}
      />
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
