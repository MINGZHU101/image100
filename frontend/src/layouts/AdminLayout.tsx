import { useMutation, useQueryClient } from '@tanstack/react-query'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'

import { authApi } from '@/api/auth'
import ToastHost from '@/components/ToastHost'

const NAV = [
  { to: '/admin', label: '仪表盘', end: true },
  { to: '/admin/users', label: '用户管理' },
  { to: '/admin/points', label: '积分流水' },
  { to: '/admin/lucky-wheel', label: '幸运大转盘' },
  { to: '/admin/invites', label: '邀请概览' },
  { to: '/admin/sessions', label: '会话概览' },
  { to: '/admin/announcements', label: '公告管理' },
  { to: '/admin/settings', label: '运营参数' },
  { to: '/admin/batch', label: '批量发分' },
  { to: '/admin/admins', label: '管理员' },
  { to: '/admin/audit', label: '操作日志' },
]

export default function AdminLayout() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const logout = useMutation({
    mutationFn: () => authApi.adminLogout(),
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: ['auth', 'admin'] })
      navigate('/auth?as=admin', { replace: true })
    },
  })

  return (
    <div className="flex min-h-screen bg-[#f3f5f7]">
      <aside className="flex w-56 shrink-0 flex-col bg-[#1e293b] text-slate-200">
        <div className="border-b border-white/10 px-4 py-5">
          <p className="text-sm font-semibold text-white">电商商品视觉管理台</p>
          <p className="mt-1 text-xs text-slate-400">Admin Console</p>
        </div>
        <nav className="flex-1 space-y-0.5 p-2">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `block rounded-md px-3 py-2 text-sm transition ${
                  isActive ? 'bg-teal-600/90 text-white' : 'hover:bg-white/10'
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <button
          type="button"
          onClick={() => logout.mutate()}
          className="m-2 rounded-md px-3 py-2 text-left text-sm text-slate-300 hover:bg-white/10"
        >
          退出管理端
        </button>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center border-b border-slate-200 bg-white px-6">
          <h1 className="text-sm font-medium text-slate-700">运营后台</h1>
        </header>
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
      <ToastHost />
    </div>
  )
}
