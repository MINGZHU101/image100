import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import AdminPageHeader from '@/components/admin/AdminPageHeader'
import { adminUi } from '@/components/admin/adminStyles'
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
    <div className={adminUi.page}>
      <AdminPageHeader
        title="管理员"
        description="维护后台账号，并修改当前登录管理员的密码。"
      />
      <div className="grid gap-5 lg:grid-cols-2">
        <div className={adminUi.panelPad}>
          <h3 className={adminUi.sectionTitle}>管理员列表</h3>
          <ul className="border-line mt-3 divide-y">
            {data?.map((a) => (
              <li key={a.id} className="flex items-center justify-between py-3 text-sm">
                <span className="text-ink font-medium">{a.display_name}</span>
                <span className="text-muted">@{a.username}</span>
              </li>
            ))}
            {!data?.length && <li className={`${adminUi.faint} py-3`}>暂无管理员</li>}
          </ul>
        </div>

        <div className="space-y-5">
          <div className={`${adminUi.panelPad} space-y-3`}>
            <h3 className={adminUi.sectionTitle}>创建管理员</h3>
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="账号"
              className={adminUi.input}
            />
            <input
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="显示名"
              className={adminUi.input}
            />
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="密码"
              className={adminUi.input}
            />
            <button type="button" onClick={() => create.mutate()} className={adminUi.btnPrimary}>
              创建
            </button>
          </div>
          <div className={`${adminUi.panelPad} space-y-3`}>
            <h3 className={adminUi.sectionTitle}>修改我的密码</h3>
            <input
              type="password"
              value={oldPassword}
              onChange={(e) => setOldPassword(e.target.value)}
              placeholder="旧密码"
              className={adminUi.input}
            />
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="新密码"
              className={adminUi.input}
            />
            <input
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              placeholder="确认新密码"
              className={adminUi.input}
            />
            <button type="button" onClick={() => changePwd.mutate()} className={adminUi.btnInk}>
              保存密码
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
