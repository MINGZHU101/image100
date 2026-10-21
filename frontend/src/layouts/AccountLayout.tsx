import { NavLink, Outlet } from 'react-router-dom'

const NAV = [
  { to: '/account', end: true, label: '总览' },
  { to: '/account/profile', end: false, label: '基本信息' },
  { to: '/account/points', end: false, label: '积分与会员' },
  { to: '/account/lucky-wheel', end: false, label: '幸运大转盘' },
  { to: '/account/invite', end: false, label: '邀请码' },
  { to: '/account/security', end: false, label: '安全设置' },
]

/** 个人中心：左侧子导航 + 右侧内容（布局 A）。 */
export default function AccountLayout() {
  return (
    <div className="bg-canvas min-h-full">
      <div className="mx-auto flex max-w-5xl gap-6 px-6 py-8">
        <aside className="border-line bg-paper rounded-panel shadow-card w-52 shrink-0 border p-3">
          <p className="text-muted px-2 pb-2 text-xs font-medium tracking-wide">会员中心</p>
          <ul className="flex flex-col gap-0.5">
            {NAV.map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  end={item.end}
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
        </aside>
        <div className="border-line bg-paper rounded-panel shadow-card min-w-0 flex-1 border p-6">
          <Outlet />
        </div>
      </div>
    </div>
  )
}
