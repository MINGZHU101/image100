import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'

import { adminApi } from '@/api/admin'

export default function AdminAuditPage() {
  const [page, setPage] = useState(1)
  const { data } = useQuery({
    queryKey: ['admin', 'audit', page],
    queryFn: () => adminApi.auditLogs(page),
  })

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-slate-800">操作日志</h2>
      <div className="overflow-hidden rounded-lg border bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-500">
            <tr>
              <th className="px-3 py-2">管理员</th>
              <th className="px-3 py-2">动作</th>
              <th className="px-3 py-2">目标</th>
              <th className="px-3 py-2">详情</th>
              <th className="px-3 py-2">时间</th>
            </tr>
          </thead>
          <tbody>
            {data?.items.map((row) => (
              <tr key={row.id} className="border-t">
                <td className="px-3 py-2">{row.admin_username}</td>
                <td className="px-3 py-2">{row.action}</td>
                <td className="px-3 py-2">
                  {row.target_type} {row.target_id}
                </td>
                <td className="max-w-xs truncate px-3 py-2">{row.detail}</td>
                <td className="px-3 py-2 text-slate-500">{row.created_at}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex gap-2 text-sm">
        <button type="button" disabled={page <= 1} onClick={() => setPage((p) => p - 1)} className="rounded border px-2 py-1 disabled:opacity-40">
          上一页
        </button>
        <span>共 {data?.total ?? 0} 条</span>
        <button
          type="button"
          disabled={!data || page * data.page_size >= data.total}
          onClick={() => setPage((p) => p + 1)}
          className="rounded border px-2 py-1 disabled:opacity-40"
        >
          下一页
        </button>
      </div>
    </div>
  )
}
