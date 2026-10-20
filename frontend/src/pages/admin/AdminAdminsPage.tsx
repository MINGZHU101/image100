import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { adminApi } from '@/api/admin'
import { errorMessage } from '@/hooks/useAuth'
import { toast } from '@/stores/toasts'

export default function AdminAdminsPage() {
  const queryClient = useQueryClient()
  const { data } = useQuery({
    queryKey: ['admin', 'admins'],
    queryFn: () => adminApi.admins(),
  })
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('管理员')
  const [oldPassword, setOldPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirm, setConfirm] = useState('')

  const create = useMutation({
    mutationFn: () =>
      adminApi.createAdmin({ username, password, display_name: displayName }),
    onSuccess: () => {
      toast('管理员已创建')
      setUsername('')
      setPassword('')
      queryClient.invalidateQueries({ queryKey: ['admin', 'admins'] })
    },
    onError: (e) => toast(errorMessage(e), 'danger'),
  })

  const changePwd = useMutation({
    mutationFn: () =>
      adminApi.changePassword({
        old_password: oldPassword,
        new_password: newPassword,
        new_password_confirm: confirm,
      }),
    onSuccess: () => {
      toast('密码已修改')
      setOldPassword('')
      setNewPassword('')
      setConfirm('')
    },
    onError: (e) => toast(errorMessage(e), 'danger'),
  })

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <div className="space-y-3">
        <h2 className="text-lg font-semibold text-slate-800">管理员列表</h2>
        <ul className="rounded-lg border bg-white divide-y">
          {data?.map((a) => (
            <li key={a.id} className="px-4 py-3 text-sm">
              <span className="font-medium">{a.display_name}</span>
              <span className="ml-2 text-slate-500">@{a.username}</span>
            </li>
          ))}
        </ul>
      </div>
      <div className="space-y-6">
        <div className="space-y-2 rounded-lg border bg-white p-4">
          <h3 className="font-medium">创建管理员</h3>
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="账号"
            className="w-full rounded border px-3 py-2 text-sm"
          />
          <input
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="显示名"
            className="w-full rounded border px-3 py-2 text-sm"
          />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="密码"
            className="w-full rounded border px-3 py-2 text-sm"
          />
          <button
            type="button"
            onClick={() => create.mutate()}
            className="rounded bg-teal-700 px-3 py-2 text-sm text-white"
          >
            创建
          </button>
        </div>
        <div className="space-y-2 rounded-lg border bg-white p-4">
          <h3 className="font-medium">修改我的密码</h3>
          <input
            type="password"
            value={oldPassword}
            onChange={(e) => setOldPassword(e.target.value)}
            placeholder="旧密码"
            className="w-full rounded border px-3 py-2 text-sm"
          />
          <input
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            placeholder="新密码"
            className="w-full rounded border px-3 py-2 text-sm"
          />
          <input
            type="password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            placeholder="确认新密码"
            className="w-full rounded border px-3 py-2 text-sm"
          />
          <button
            type="button"
            onClick={() => changePwd.mutate()}
            className="rounded bg-slate-800 px-3 py-2 text-sm text-white"
          >
            保存密码
          </button>
        </div>
      </div>
    </div>
  )
}
