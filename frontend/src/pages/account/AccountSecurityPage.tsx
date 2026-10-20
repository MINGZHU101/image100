import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { accountApi } from '@/api/account'
import { errorMessage, useAuthActions } from '@/hooks/useAuth'

export default function AccountSecurityPage() {
  const navigate = useNavigate()
  const { logout } = useAuthActions()
  const [oldPassword, setOldPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [hint, setHint] = useState('')
  const [localError, setLocalError] = useState('')

  const change = useMutation({
    mutationFn: () =>
      accountApi.changePassword({
        old_password: oldPassword,
        new_password: newPassword,
        new_password_confirm: confirm,
      }),
    onSuccess: () => {
      setHint('密码已更新')
      setOldPassword('')
      setNewPassword('')
      setConfirm('')
    },
  })

  const submit = (event: React.FormEvent) => {
    event.preventDefault()
    setLocalError('')
    if (newPassword !== confirm) {
      setLocalError('两次输入的新密码不一致')
      return
    }
    change.mutate()
  }

  return (
    <div className="space-y-8">
      <h1 className="text-ink text-xl font-semibold">安全设置</h1>

      <form onSubmit={submit} className="max-w-sm space-y-3">
        <Field label="旧密码" type="password" value={oldPassword} onChange={setOldPassword} />
        <Field label="新密码" type="password" value={newPassword} onChange={setNewPassword} />
        <Field label="确认新密码" type="password" value={confirm} onChange={setConfirm} />
        {(localError || change.isError) && (
          <p className="text-danger text-sm">{localError || errorMessage(change.error)}</p>
        )}
        {hint && <p className="text-success text-sm">{hint}</p>}
        <button
          type="submit"
          disabled={change.isPending}
          className="bg-ink rounded-control px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          修改密码
        </button>
      </form>

      <button
        type="button"
        onClick={() => logout.mutate(undefined, { onSuccess: () => navigate('/', { replace: true }) })}
        className="text-danger text-sm hover:underline"
      >
        退出登录
      </button>
    </div>
  )
}

function Field({
  label,
  value,
  onChange,
  type = 'text',
}: {
  label: string
  value: string
  onChange: (value: string) => void
  type?: string
}) {
  return (
    <label className="block">
      <span className="text-muted mb-1.5 block text-sm">{label}</span>
      <input
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        required
        minLength={type === 'password' ? 6 : undefined}
        className="border-line rounded-control w-full border px-3.5 py-2.5 text-sm outline-none focus:border-brand"
      />
    </label>
  )
}
