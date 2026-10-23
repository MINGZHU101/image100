import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'

import AdminPageHeader from '@/components/admin/AdminPageHeader'
import { adminUi } from '@/components/admin/adminStyles'
import { adminApi } from '@/api/admin'

export default function AdminSessionsPage() {
  const [q, setQ] = useState('')
  const [page, setPage] = useState(1)
  const { data } = useQuery({
    queryKey: ['admin', 'sessions', q, page],
    queryFn: () => adminApi.sessions({ q: q || undefined, page }),
  })

  return (
    <div className={adminUi.page}>
      <AdminPageHeader
        title="会话概览"
        description="按用户汇总编辑会话数量与最近活跃时间（只读）。"
        actions={
          <input
            value={q}
            onChange={(e) => {
              setQ(e.target.value)
              setPage(1)
            }}
            placeholder="按账号筛选"
            className={adminUi.inputInline}
          />
        }
      />
      <div className={adminUi.tableWrap}>
        <table className="w-full text-left">
          <thead className={adminUi.thead}>
            <tr>
              {['账号', '用户名', '会话数', '最近更新'].map((h) => (
                <th key={h} className={adminUi.th}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data?.items.map((row) => (
              <tr key={row.user_id} className="hover:bg-soft/60 transition-colors">
                <td className={adminUi.td}>{row.account}</td>
                <td className={adminUi.td}>{row.display_name}</td>
                <td className={`${adminUi.td} tabular-nums`}>{row.session_count}</td>
                <td className={`${adminUi.td} text-muted`}>{row.last_updated ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
