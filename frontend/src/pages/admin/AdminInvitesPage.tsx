import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'

import { adminApi } from '@/api/admin'

export default function AdminInvitesPage() {
  const [page, setPage] = useState(1)
  const { data } = useQuery({
    queryKey: ['admin', 'invites', page],
    queryFn: () => adminApi.invites(page),
  })

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-slate-800">邀请概览</h2>
      <p className="text-sm text-slate-500">已成功领取邀请奖励的用户</p>
      <div className="overflow-hidden rounded-lg border bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-500">
            <tr>
              <th className="px-3 py-2">账号</th>
              <th className="px-3 py-2">用户名</th>
              <th className="px-3 py-2">会员</th>
              <th className="px-3 py-2">注册时间</th>
            </tr>
          </thead>
          <tbody>
            {data?.items.map((u) => (
              <tr key={u.id} className="border-t">
                <td className="px-3 py-2">{u.account}</td>
                <td className="px-3 py-2">{u.display_name}</td>
                <td className="px-3 py-2">{u.member_tier}</td>
                <td className="px-3 py-2 text-slate-500">{u.created_at}</td>
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
