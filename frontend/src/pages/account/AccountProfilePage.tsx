import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { accountApi } from '@/api/account'
import UserAvatar from '@/components/UserAvatar'
import { errorMessage, useAuthActions, useCurrentUser } from '@/hooks/useAuth'

export default function AccountProfilePage() {
  const { user } = useCurrentUser()
  const { cacheUser } = useAuthActions()
  const queryClient = useQueryClient()
  const [displayName, setDisplayName] = useState(user?.display_name ?? '')
  const [msg, setMsg] = useState('')

  const saveName = useMutation({
    mutationFn: () => accountApi.updateDisplayName(displayName),
    onSuccess: (next) => {
      cacheUser(next)
      void queryClient.invalidateQueries({ queryKey: ['account'] })
      setMsg('用户名已更新')
    },
  })

  const upload = useMutation({
    mutationFn: (file: File) => accountApi.uploadAvatar(file),
    onSuccess: (next) => {
      cacheUser(next)
      void queryClient.invalidateQueries({ queryKey: ['account'] })
      setMsg('头像已更新')
    },
  })

  if (!user) return null

  return (
    <div className="space-y-6">
      <h1 className="text-ink text-xl font-semibold">基本信息</h1>

      <div className="flex items-center gap-4">
        <UserAvatar user={user} size="lg" />
        <label className="border-line hover:bg-soft rounded-control cursor-pointer border px-3 py-2 text-sm">
          上传头像
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            className="hidden"
            onChange={(event) => {
              const file = event.target.files?.[0]
              if (file) upload.mutate(file)
            }}
          />
        </label>
      </div>
      <p className="text-muted text-xs">支持 jpg / png / webp，最大 2MB</p>

      <label className="block max-w-sm">
        <span className="text-muted mb-1.5 block text-sm">账号（不可改）</span>
        <input
          value={user.account}
          disabled
          className="border-line bg-soft text-muted rounded-control w-full border px-3.5 py-2.5 text-sm"
        />
      </label>

      <label className="block max-w-sm">
        <span className="text-muted mb-1.5 block text-sm">用户名</span>
        <input
          value={displayName}
          onChange={(event) => setDisplayName(event.target.value)}
          maxLength={32}
          className="border-line rounded-control w-full border px-3.5 py-2.5 text-sm outline-none focus:border-brand"
        />
      </label>

      {(msg || saveName.isError || upload.isError) && (
        <p className={`text-sm ${saveName.isError || upload.isError ? 'text-danger' : 'text-success'}`}>
          {saveName.isError
            ? errorMessage(saveName.error)
            : upload.isError
              ? errorMessage(upload.error)
              : msg}
        </p>
      )}

      <button
        type="button"
        disabled={saveName.isPending || !displayName.trim()}
        onClick={() => saveName.mutate()}
        className="bg-ink rounded-control px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
      >
        保存用户名
      </button>
    </div>
  )
}
