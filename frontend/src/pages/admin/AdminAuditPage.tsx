import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'

import AdminPageHeader from '@/components/admin/AdminPageHeader'
import { adminUi } from '@/components/admin/adminStyles'
import { adminApi } from '@/api/admin'

export default function AdminAuditPage() {
  const [page, setPage] = useState(1)
  const { data } = useQuery({
    queryKey: ['admin', 'audit', page],
    queryFn: () => adminApi.auditLogs(page),
  })

  return (
    <div className={adminUi.page}>
      <AdminPageHeader title="操作日志" description="管理员关键操作的审计追踪，便于回溯。" />
      <div className={adminUi.tableWrap}>
        <table className="w-full text-left">
          <thead className={adminUi.thead}>
            <tr>
              {['管理员', '动作', '目标', '详情', '时间'].map((h) => (
                <th key={h} className={adminUi.th}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data?.items.map((row) => (
              <tr key={row.id} className="hover:bg-soft/60 transition-colors">
                <td className={adminUi.td}>{row.admin_username}</td>
                <td className={adminUi.td}>
                  <span className={adminUi.badgeBrand}>{row.action}</span>
                </td>
                <td className={adminUi.td}>
                  {row.target_type} {row.target_id}
                </td>
                <td className={`${adminUi.td} max-w-xs truncate`}>{row.detail}</td>
                <td className={`${adminUi.td} text-muted`}>{row.created_at}</td>
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
