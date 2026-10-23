import { useMutation, useQueryClient } from '@tanstack/react-query'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'

import BrandMark from '@/components/BrandMark'
import ToastHost from '@/components/ToastHost'
import { authApi } from '@/api/auth'

type NavItem = { to: string; label: string; end?: boolean; hint: string }

const NAV_GROUPS: { title: string; items: NavItem[] }[] = [
  {
    title: '总览',
    items: [{ to: '/admin', label: '仪表盘', end: true, hint: '核心运营指标' }],
  },
  {
    title: '用户与资产',
    items: [
      { to: '/admin/users', label: '用户管理', hint: '查询 / 调账 / 冻结' },
      { to: '/admin/points', label: '积分流水', hint: '积分与余额明细' },
      { to: '/admin/invites', label: '邀请概览', hint: '邀请关系' },
      { to: '/admin/lucky-wheel', label: '幸运大转盘', hint: '记录与奖池' },
    ],
  },
  {
    title: '内容与运营',
    items: [
      { to: '/admin/sessions', label: '会话概览', hint: '编辑会话统计' },
      { to: '/admin/announcements', label: '公告管理', hint: '站内通知' },
      { to: '/admin/settings', label: '运营参数', hint: '礼包与汇率' },
      { to: '/admin/batch', label: '批量发分', hint: '活动发放积分' },
    ],
  },
  {
    title: '系统',
    items: [
      { to: '/admin/admins', label: '管理员', hint: '账号与改密' },
      { to: '/admin/audit', label: '操作日志', hint: '审计追踪' },
    ],
  },
]

function titleFromPath(pathname: string): string {
  for (const group of NAV_GROUPS) {
    for (const item of group.items) {
      if (item.end ? pathname === item.to : pathname.startsWith(item.to)) {
        return item.label
      }
    }
  }
  return '运营后台'
}

/** 管理端外壳：与用户端同色板（canvas / paper / brand）。 */
export default function AdminLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const queryClient = useQueryClient()
  const pageTitle = titleFromPath(location.pathname)

  const logout = useMutation({
    mutationFn: () => authApi.adminLogout(),
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: ['auth', 'admin'] })
      navigate('/auth?as=admin', { replace: true })
    },
  })

  return (
    <div className="bg-canvas flex min-h-screen">
      <aside className="border-line bg-paper shadow-panel sticky top-0 flex h-screen w-60 shrink-0 flex-col border-r">
        <div className="border-line border-b px-4 py-5">
          <BrandMark size="sm">
            <span className="min-w-0">
              <span className="text-ink block truncate text-sm font-semibold">管理台</span>
              <span className="text-faint block text-[11px]">电商商品视觉 · Admin</span>
            </span>
          </BrandMark>
        </div>

        <nav className="flex-1 space-y-5 overflow-y-auto px-2 py-4">
          {NAV_GROUPS.map((group) => (
            <div key={group.title}>
              <p className="text-faint px-3 pb-1.5 text-[11px] font-medium tracking-wide uppercase">
                {group.title}
              </p>
              <ul className="space-y-0.5">
                {group.items.map((item) => (
                  <li key={item.to}>
                    <NavLink
                      to={item.to}
                      end={item.end}
                      title={item.hint}
                      className={({ isActive }) =>
                        `block rounded-[12px] px-3 py-2.5 text-sm transition-colors ${
                          isActive
                            ? 'bg-brand-soft text-brand-strong font-medium'
                            : 'text-muted hover:bg-soft hover:text-ink'
                        }`
                      }
                    >
                      {item.label}
                    </NavLink>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </nav>

        <div className="border-line space-y-2 border-t p-3">
          <a
            href="/create"
            className="text-muted hover:bg-soft hover:text-ink block rounded-[12px] px-3 py-2 text-sm transition-colors"
          >
            返回工作台
          </a>
          <button
            type="button"
            onClick={() => logout.mutate()}
            disabled={logout.isPending}
            className="text-muted hover:bg-soft hover:text-ink w-full rounded-[12px] px-3 py-2 text-left text-sm transition-colors disabled:opacity-50"
          >
            退出管理端
          </button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="border-line bg-paper/90 sticky top-0 z-10 flex h-14 items-center justify-between border-b px-6 backdrop-blur">
          <div>
            <p className="text-faint text-[11px] tracking-wide">运营后台</p>
            <h1 className="text-ink text-sm font-semibold">{pageTitle}</h1>
          </div>
          <span className="bg-brand-soft text-brand-strong rounded-full px-2.5 py-1 text-[11px] font-medium">
            Admin
          </span>
        </header>
        <main className="flex-1 overflow-auto p-6">
          <div className="mx-auto max-w-6xl">
            <Outlet />
          </div>
        </main>
      </div>
      <ToastHost />
    </div>
  )
}
