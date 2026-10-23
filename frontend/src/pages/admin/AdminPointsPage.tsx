import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'

import AdminPageHeader from '@/components/admin/AdminPageHeader'
import { adminUi } from '@/components/admin/adminStyles'
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
    <div className={adminUi.page}>
      <AdminPageHeader
        title="积分与余额流水"
        description="全站积分入账/消耗与余额充值兑换明细，支持按账号筛选。"
        actions={
          <>
            <button
              type="button"
              onClick={() => {
                setTab('points')
                setPage(1)
              }}
              className={`${adminUi.tab} ${tab === 'points' ? adminUi.tabActive : adminUi.tabIdle}`}
            >
              积分流水
            </button>
            <button
              type="button"
              onClick={() => {
                setTab('wallet')
                setPage(1)
              }}
              className={`${adminUi.tab} ${tab === 'wallet' ? adminUi.tabActive : adminUi.tabIdle}`}
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
              className={adminUi.inputInline}
            />
            {tab === 'points' && (
              <input
                value={kind}
                onChange={(e) => {
                  setKind(e.target.value)
                  setPage(1)
                }}
                placeholder="类型如 newbie_gift"
                className={adminUi.inputInline}
              />
            )}
          </>
        }
      />

      <div className={adminUi.tableWrap}>
        <table className="w-full text-left">
          <thead className={adminUi.thead}>
            <tr>
              {['账号', '变动', '余额后', '类型', '备注', '时间'].map((h) => (
                <th key={h} className={adminUi.th}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data?.items.map((row) => (
              <tr key={row.id} className="hover:bg-soft/60 transition-colors">
                <td className={adminUi.td}>{row.account}</td>
                <td
                  className={`${adminUi.td} tabular-nums ${
                    row.delta >= 0 ? 'text-success' : 'text-danger'
                  }`}
                >
                  {row.delta > 0 ? `+${row.delta}` : row.delta}
                </td>
                <td className={`${adminUi.td} tabular-nums`}>{row.balance_after}</td>
                <td className={adminUi.td}>
                  <span className={adminUi.badgeBrand}>{row.kind}</span>
                </td>
                <td className={adminUi.td}>{row.remark}</td>
                <td className={`${adminUi.td} text-muted`}>{row.created_at}</td>
              </tr>
            ))}
            {!data?.items.length && (
              <tr>
                <td colSpan={6} className={`${adminUi.td} text-faint text-center`}>
                  暂无记录
                </td>
              </tr>
            )}
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
        <span>
          第 {page} 页 · 共 {data?.total ?? 0} 条
        </span>
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
