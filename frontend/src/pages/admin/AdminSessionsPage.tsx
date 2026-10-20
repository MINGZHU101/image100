import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'

import { adminApi } from '@/api/admin'

export default function AdminSessionsPage() {
  const [q, setQ] = useState('')
  const [page, setPage] = useState(1)
  const { data } = useQuery({
    queryKey: ['admin', 'sessions', q, page],
    queryFn: () => adminApi.sessions({ q: q || undefined, page }),
  })

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-slate-800">会话概览（只读）</h2>
      <input
        value={q}
        onChange={(e) => {
          setQ(e.target.value)
          setPage(1)
        }}
        placeholder="按账号筛选"
        className="rounded border px-3 py-1.5 text-sm"
      />
      <div className="overflow-hidden rounded-lg border bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-500">
            <tr>
              <th className="px-3 py-2">账号</th>
              <th className="px-3 py-2">用户名</th>
              <th className="px-3 py-2">会话数</th>
              <th className="px-3 py-2">最近更新</th>
            </tr>
          </thead>
          <tbody>
            {data?.items.map((row) => (
              <tr key={row.user_id} className="border-t">
                <td className="px-3 py-2">{row.account}</td>
                <td className="px-3 py-2">{row.display_name}</td>
                <td className="px-3 py-2 tabular-nums">{row.session_count}</td>
                <td className="px-3 py-2 text-slate-500">{row.last_updated ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
