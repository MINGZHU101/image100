import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'

import AdminPageHeader from '@/components/admin/AdminPageHeader'
import { adminUi } from '@/components/admin/adminStyles'
import { adminApi } from '@/api/admin'

export default function AdminInvitesPage() {
  const [page, setPage] = useState(1)
  const { data } = useQuery({
    queryKey: ['admin', 'invites', page],
    queryFn: () => adminApi.invites(page),
  })

  return (
    <div className={adminUi.page}>
      <AdminPageHeader
        title="邀请概览"
        description="已成功领取邀请奖励的用户列表。"
      />
      <div className={adminUi.tableWrap}>
        <table className="w-full text-left">
          <thead className={adminUi.thead}>
            <tr>
              {['账号', '用户名', '会员', '注册时间'].map((h) => (
                <th key={h} className={adminUi.th}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data?.items.map((u) => (
              <tr key={u.id} className="hover:bg-soft/60 transition-colors">
                <td className={adminUi.td}>{u.account}</td>
                <td className={adminUi.td}>{u.display_name}</td>
                <td className={adminUi.td}>
                  <span className={adminUi.badgeBrand}>{u.member_tier}</span>
                </td>
                <td className={`${adminUi.td} text-muted`}>{u.created_at}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="text-muted flex gap-2 text-sm">
        <button
          type="button"
          disabled={page <= 1}
          onClick={() => setPage((p) => p - 1)}
          className={adminUi.btnGhost}
        >
          上一页
        </button>
        <span>共 {data?.total ?? 0} 条</span>
        <button
          type="button"
          disabled={!data || page * data.page_size >= data.total}
          onClick={() => setPage((p) => p + 1)}
          className={adminUi.btnGhost}
        >
          下一页
        </button>
      </div>
    </div>
  )
}
