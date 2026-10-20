import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'

import { adminApi } from '@/api/admin'

export default function AdminPointsPage() {
  const [q, setQ] = useState('')
  const [kind, setKind] = useState('')
  const [page, setPage] = useState(1)
  const [tab, setTab] = useState<'points' | 'wallet'>('points')

  const points = useQuery({
    queryKey: ['admin', 'point-ledgers', q, kind, page],
    queryFn: () => adminApi.pointLedgers({ q: q || undefined, kind: kind || undefined, page }),
    enabled: tab === 'points',
  })
  const wallet = useQuery({
    queryKey: ['admin', 'wallet-ledgers', q, page],
    queryFn: () => adminApi.walletLedgers({ q: q || undefined, page }),
    enabled: tab === 'wallet',
  })
  const data = tab === 'points' ? points.data : wallet.data

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-slate-800">积分与余额流水</h2>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => {
            setTab('points')
            setPage(1)
          }}
          className={`rounded px-3 py-1.5 text-sm ${tab === 'points' ? 'bg-slate-800 text-white' : 'border'}`}
        >
          积分流水
        </button>
        <button
          type="button"
          onClick={() => {
            setTab('wallet')
            setPage(1)
          }}
          className={`rounded px-3 py-1.5 text-sm ${tab === 'wallet' ? 'bg-slate-800 text-white' : 'border'}`}
        >
          余额流水
        </button>
        <input
          value={q}
          onChange={(e) => {
            setQ(e.target.value)
            setPage(1)
          }}
          placeholder="按账号筛选"
          className="rounded border px-3 py-1.5 text-sm"
        />
        {tab === 'points' && (
          <input
            value={kind}
            onChange={(e) => {
              setKind(e.target.value)
              setPage(1)
            }}
            placeholder="类型如 newbie_gift"
            className="rounded border px-3 py-1.5 text-sm"
          />
        )}
      </div>
      <div className="overflow-hidden rounded-lg border bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-500">
            <tr>
              <th className="px-3 py-2">账号</th>
              <th className="px-3 py-2">变动</th>
              <th className="px-3 py-2">余额后</th>
              <th className="px-3 py-2">类型</th>
              <th className="px-3 py-2">备注</th>
              <th className="px-3 py-2">时间</th>
            </tr>
          </thead>
          <tbody>
            {data?.items.map((row) => (
              <tr key={row.id} className="border-t">
                <td className="px-3 py-2">{row.account}</td>
                <td className="px-3 py-2 tabular-nums">{row.delta}</td>
                <td className="px-3 py-2 tabular-nums">{row.balance_after}</td>
                <td className="px-3 py-2">{row.kind}</td>
                <td className="px-3 py-2">{row.remark}</td>
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
        <span>第 {page} 页 · 共 {data?.total ?? 0} 条</span>
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
