import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { accountApi } from '@/api/account'
import { errorMessage, useAuthActions, useCurrentUser } from '@/hooks/useAuth'

export default function AccountInvitePage() {
  const { user } = useCurrentUser()
  const { cacheUser } = useAuthActions()
  const queryClient = useQueryClient()
  const [codeInput, setCodeInput] = useState('')
  const [hint, setHint] = useState('')

  const active = useQuery({
    queryKey: ['account', 'invite-active'],
    queryFn: () => accountApi.activeInvite(),
  })

  const create = useMutation({
    mutationFn: () => accountApi.createInvite(),
    onSuccess: () => {
      setHint('邀请码已生成，10 分钟内有效')
      void active.refetch()
    },
  })

  const redeem = useMutation({
    mutationFn: () => accountApi.redeemInvite(codeInput.trim()),
    onSuccess: (next) => {
      cacheUser(next)
      void queryClient.invalidateQueries({ queryKey: ['account'] })
      setHint('邀请奖励已到账（双方各 +200）')
      setCodeInput('')
    },
  })

  if (!user) return null

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-ink text-xl font-semibold">邀请码</h1>
        <p className="text-muted mt-1 text-sm">
          生成五位邀请码分享好友；好友在登录/注册填写后，双方各得 200 积分。码有效期 10 分钟。
        </p>
      </div>

      <section className="space-y-3">
        <h2 className="text-ink text-sm font-medium">我的邀请码</h2>
        {active.data ? (
          <p className="text-ink text-2xl font-semibold tracking-[0.2em]">{active.data.code}</p>
        ) : (
          <p className="text-muted text-sm">当前没有有效邀请码</p>
        )}
        <button
          type="button"
          disabled={create.isPending}
          onClick={() => create.mutate()}
          className="bg-ink rounded-control px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          生成邀请码
        </button>
        {create.isError && <p className="text-danger text-sm">{errorMessage(create.error)}</p>}
      </section>

      <section className="space-y-3">
        <h2 className="text-ink text-sm font-medium">填写他人邀请码</h2>
        {user.invite_reward_claimed ? (
          <p className="text-muted text-sm">您已领取过邀请奖励</p>
        ) : (
          <div className="flex max-w-sm gap-2">
            <input
              value={codeInput}
              onChange={(event) => setCodeInput(event.target.value.toUpperCase())}
              maxLength={5}
              placeholder="五位码"
              className="border-line rounded-control flex-1 border px-3 py-2 text-sm tracking-widest outline-none focus:border-brand"
            />
            <button
              type="button"
              disabled={redeem.isPending || codeInput.trim().length < 5}
              onClick={() => redeem.mutate()}
              className="bg-brand-strong rounded-control px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              领取
            </button>
          </div>
        )}
        {redeem.isError && <p className="text-danger text-sm">{errorMessage(redeem.error)}</p>}
      </section>

      {hint && <p className="text-success text-sm">{hint}</p>}
    </div>
  )
}
