import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { adminApi } from '@/api/admin'
import { errorMessage } from '@/hooks/useAuth'
import { toast } from '@/stores/toasts'

export default function AdminUsersPage() {
  const queryClient = useQueryClient()
  const [q, setQ] = useState('')
  const [tier, setTier] = useState('')
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState<string | null>(null)
  const [pointsDelta, setPointsDelta] = useState('100')
  const [walletDelta, setWalletDelta] = useState('10')
  const [remark, setRemark] = useState('运营调整')

  const { data, isLoading } = useQuery({
    queryKey: ['admin', 'users', q, tier, page],
    queryFn: () =>
      adminApi.users({
        q: q || undefined,
        member_tier: tier || undefined,
        page,
      }),
  })

  const detail = useQuery({
    queryKey: ['admin', 'user', selected],
    queryFn: () => adminApi.userDetail(selected!),
    enabled: Boolean(selected),
  })

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'users'] })
    if (selected) queryClient.invalidateQueries({ queryKey: ['admin', 'user', selected] })
  }

  const adjustPoints = useMutation({
    mutationFn: () =>
      adminApi.adjustPoints(selected!, { delta: Number(pointsDelta), remark }),
    onSuccess: () => {
      toast('积分已调整')
      invalidate()
    },
    onError: (e) => toast(errorMessage(e), 'danger'),
  })
  const adjustWallet = useMutation({
    mutationFn: () =>
      adminApi.adjustWallet(selected!, { delta: Number(walletDelta), remark }),
    onSuccess: () => {
      toast('余额已调整')
      invalidate()
    },
    onError: (e) => toast(errorMessage(e), 'danger'),
  })
  const freeze = useMutation({
    mutationFn: (frozen: boolean) => adminApi.freeze(selected!, frozen),
    onSuccess: () => {
      toast('状态已更新')
      invalidate()
    },
  })
  const forceLogout = useMutation({
    mutationFn: () => adminApi.forceLogout(selected!),
    onSuccess: () => toast('已强制下线'),
  })

  const exportCsv = async () => {
    const text = await adminApi.exportUsers({ q: q || undefined, member_tier: tier || undefined })
    const blob = new Blob(['\uFEFF' + text], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'users.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-2">
        <h2 className="mr-auto text-lg font-semibold text-slate-800">用户管理</h2>
        <input
          value={q}
          onChange={(e) => {
            setQ(e.target.value)
            setPage(1)
          }}
          placeholder="搜索账号/用户名"
          className="rounded border border-slate-300 px-3 py-1.5 text-sm"
        />
        <select
          value={tier}
          onChange={(e) => {
            setTier(e.target.value)
            setPage(1)
          }}
          className="rounded border border-slate-300 px-2 py-1.5 text-sm"
        >
          <option value="">全部会员</option>
          {['青铜', '白银', '黄金', '铂金', '钻石'].map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
        <button
          type="button"
          onClick={exportCsv}
          className="rounded bg-slate-800 px-3 py-1.5 text-sm text-white"
        >
          导出 CSV
        </button>
      </div>

      <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-500">
            <tr>
              <th className="px-3 py-2 font-medium">账号</th>
              <th className="px-3 py-2 font-medium">用户名</th>
              <th className="px-3 py-2 font-medium">会员</th>
              <th className="px-3 py-2 font-medium">余额</th>
              <th className="px-3 py-2 font-medium">积分</th>
              <th className="px-3 py-2 font-medium">状态</th>
              <th className="px-3 py-2 font-medium">操作</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr>
                <td colSpan={7} className="px-3 py-6 text-slate-400">
                  加载中…
                </td>
              </tr>
            )}
            {data?.items.map((u) => (
              <tr key={u.id} className="border-t border-slate-100">
                <td className="px-3 py-2">{u.account}</td>
                <td className="px-3 py-2">{u.display_name}</td>
                <td className="px-3 py-2">{u.member_tier}</td>
                <td className="px-3 py-2 tabular-nums">¥{u.wallet_balance}</td>
                <td className="px-3 py-2 tabular-nums">{u.points_balance}</td>
                <td className="px-3 py-2">{u.is_frozen ? '冻结' : '正常'}</td>
                <td className="px-3 py-2">
                  <button
                    type="button"
                    className="text-teal-700 hover:underline"
                    onClick={() => setSelected(u.id)}
                  >
                    详情
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex items-center gap-2 text-sm text-slate-600">
        <button
          type="button"
          disabled={page <= 1}
          onClick={() => setPage((p) => p - 1)}
          className="rounded border px-2 py-1 disabled:opacity-40"
        >
          上一页
        </button>
        <span>
          第 {page} 页 / 共 {data?.total ?? 0} 条
        </span>
        <button
          type="button"
          disabled={!data || page * data.page_size >= data.total}
          onClick={() => setPage((p) => p + 1)}
          className="rounded border px-2 py-1 disabled:opacity-40"
        >
          下一页
        </button>
      </div>

      {selected && detail.data && (
        <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-start justify-between gap-2">
            <div>
              <h3 className="font-medium text-slate-800">
                {detail.data.user.display_name}（{detail.data.user.account}）
              </h3>
              <p className="mt-1 text-sm text-slate-500">
                积分 {detail.data.user.points_balance} · 余额 ¥{detail.data.user.wallet_balance} ·{' '}
                {detail.data.user.is_frozen ? '已冻结' : '正常'}
              </p>
            </div>
            <button type="button" className="text-sm text-slate-500" onClick={() => setSelected(null)}>
              关闭
            </button>
          </div>
          <div className="mt-3 flex flex-wrap items-end gap-2">
            <label className="text-xs text-slate-500">
              积分变动
              <input
                value={pointsDelta}
                onChange={(e) => setPointsDelta(e.target.value)}
                className="ml-1 w-20 rounded border px-2 py-1 text-sm"
              />
            </label>
            <button
              type="button"
              onClick={() => adjustPoints.mutate()}
              className="rounded bg-teal-700 px-3 py-1.5 text-sm text-white"
            >
              调积分
            </button>
            <label className="text-xs text-slate-500">
              余额变动
              <input
                value={walletDelta}
                onChange={(e) => setWalletDelta(e.target.value)}
                className="ml-1 w-20 rounded border px-2 py-1 text-sm"
              />
            </label>
            <button
              type="button"
              onClick={() => adjustWallet.mutate()}
              className="rounded bg-slate-700 px-3 py-1.5 text-sm text-white"
            >
              调余额
            </button>
            <label className="text-xs text-slate-500">
              备注
              <input
                value={remark}
                onChange={(e) => setRemark(e.target.value)}
                className="ml-1 w-40 rounded border px-2 py-1 text-sm"
              />
            </label>
            <button
              type="button"
              onClick={() => freeze.mutate(!detail.data.user.is_frozen)}
              className="rounded border border-amber-600 px-3 py-1.5 text-sm text-amber-700"
            >
              {detail.data.user.is_frozen ? '解冻' : '冻结'}
            </button>
            <button
              type="button"
              onClick={() => forceLogout.mutate()}
              className="rounded border px-3 py-1.5 text-sm"
            >
              强制下线
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
