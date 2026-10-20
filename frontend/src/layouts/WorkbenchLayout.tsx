import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'

import { accountApi } from '@/api/account'
import BrandMark from '@/components/BrandMark'
import PointsGuideModal from '@/components/PointsGuideModal'
import ToastHost from '@/components/ToastHost'
import UserAvatar from '@/components/UserAvatar'
import { useAuthActions, useCurrentUser } from '@/hooks/useAuth'

const NAV_ITEMS = [
  { to: '/create', label: '创作', icon: 'M12 4v16m8-8H4' },
  { to: '/editor', label: '编辑', icon: 'M4 20h4L20 8l-4-4L4 16v4z' },
  { to: '/marketing', label: '导出', icon: 'M12 3v12m0 0-4-4m4 4 4-4M5 21h14' },
  { to: '/batch', label: '批量', icon: 'M4 6h16M4 12h16M4 18h10' },
]

function NavIcon({ path }: { path: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="size-5 shrink-0" aria-hidden>
      <path d={path} stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  )
}

/** 工作台外壳：左侧导航默认收起为图标，悬停展开文字。 */
export default function WorkbenchLayout() {
  const navigate = useNavigate()
  const { user } = useCurrentUser()
  const { logout } = useAuthActions()
  const [pointsMessage, setPointsMessage] = useState('')
  const { data: latestAnnouncement } = useQuery({
    queryKey: ['account', 'announcement', 'latest'],
    queryFn: () => accountApi.latestAnnouncement(),
    staleTime: 60_000,
  })

  useEffect(() => {
    const onPoints = (event: Event) => {
      const detail = (event as CustomEvent<string>).detail
      setPointsMessage(detail || '积分不足，请先充值')
    }
    window.addEventListener('points-insufficient', onPoints)
    return () => window.removeEventListener('points-insufficient', onPoints)
  }, [])

  const signOut = () =>
    logout.mutate(undefined, { onSuccess: () => navigate('/', { replace: true }) })

  return (
    <div className="flex h-screen overflow-hidden">
      <nav className="relative z-30 w-16 shrink-0" aria-label="工作台">
        <div className="group border-line bg-paper absolute inset-y-0 left-0 flex w-16 flex-col overflow-hidden border-r py-4 transition-[width,box-shadow] duration-200 hover:w-52 hover:shadow-panel">
          <BrandMark size="sm" className="mb-6 px-5">
            <span className="text-ink truncate text-sm font-semibold opacity-0 transition-opacity group-hover:opacity-100">
              电商商品视觉工作台
            </span>
          </BrandMark>

          <ul className="flex flex-1 flex-col gap-1 px-2">
            {NAV_ITEMS.map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  title={item.label}
                  className={({ isActive }) =>
                    `flex items-center gap-3 rounded-[12px] px-3 py-2.5 text-sm transition-colors ${
                      isActive
                        ? 'bg-brand-soft text-brand-strong font-medium'
                        : 'text-muted hover:bg-soft hover:text-ink'
                    }`
                  }
                >
                  <NavIcon path={item.icon} />
                  <span className="truncate opacity-0 transition-opacity group-hover:opacity-100">
                    {item.label}
                  </span>
                </NavLink>
              </li>
            ))}
          </ul>

          <div className="border-line mt-2 space-y-1 border-t px-2 pt-3">
            <NavLink
              to="/account"
              title={user ? `${user.display_name || user.username} · 个人中心` : '个人中心'}
              className={({ isActive }) =>
                `text-muted hover:bg-soft hover:text-ink flex w-full items-center gap-3 rounded-[12px] px-3 py-2.5 text-sm transition-colors ${
                  isActive ? 'bg-brand-soft text-brand-strong' : ''
                }`
              }
            >
              <UserAvatar user={user} />
              <span className="truncate opacity-0 transition-opacity group-hover:opacity-100">
                个人中心
              </span>
            </NavLink>
            <button
              type="button"
              onClick={signOut}
              title="退出登录"
              className="text-muted hover:bg-soft hover:text-ink flex w-full items-center gap-3 rounded-[12px] px-3 py-2.5 text-sm transition-colors"
            >
              <span className="grid size-5 shrink-0 place-items-center text-xs" aria-hidden>
                ⎋
              </span>
              <span className="truncate opacity-0 transition-opacity group-hover:opacity-100">
                退出登录
              </span>
            </button>
          </div>
        </div>
      </nav>

      <main className="min-w-0 flex-1 overflow-auto">
        {latestAnnouncement && (
          <div className="border-line bg-brand-soft/40 text-ink border-b px-4 py-2 text-sm">
            <span className="font-medium">公告</span>
            <span className="text-muted mx-2">·</span>
            {latestAnnouncement.title}
            {latestAnnouncement.body ? (
              <span className="text-muted"> — {latestAnnouncement.body}</span>
            ) : null}
          </div>
        )}
        <Outlet />
      </main>
      <ToastHost />
      <PointsGuideModal
        open={Boolean(pointsMessage)}
        message={pointsMessage}
        onClose={() => setPointsMessage('')}
      />
    </div>
  )
}
