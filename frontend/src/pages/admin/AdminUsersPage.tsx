import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import AdminPageHeader from '@/components/admin/AdminPageHeader'
import { adminUi } from '@/components/admin/adminStyles'
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
    <div className={adminUi.page}>
      <AdminPageHeader
        title="用户管理"
        description="检索用户、调整积分与余额、冻结账号或强制下线。"
        actions={
          <>
            <input
              value={q}
              onChange={(e) => {
                setQ(e.target.value)
                setPage(1)
              }}
              placeholder="搜索账号/用户名"
              className={adminUi.inputInline}
            />
            <select
              value={tier}
              onChange={(e) => {
                setTier(e.target.value)
                setPage(1)
              }}
              className={adminUi.select}
            >
              <option value="">全部会员</option>
              {['青铜', '白银', '黄金', '铂金', '钻石'].map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
            <button type="button" onClick={exportCsv} className={adminUi.btnInk}>
              导出 CSV
            </button>
          </>
        }
      />

      <div className={adminUi.tableWrap}>
        <table className="w-full text-left">
          <thead className={adminUi.thead}>
            <tr>
              {['账号', '用户名', '会员', '余额', '积分', '状态', '操作'].map((h) => (
                <th key={h} className={adminUi.th}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr>
                <td colSpan={7} className={`${adminUi.td} text-faint`}>
                  加载中…
                </td>
              </tr>
            )}
            {data?.items.map((u) => (
              <tr key={u.id} className="hover:bg-soft/60 transition-colors">
                <td className={adminUi.td}>{u.account}</td>
                <td className={adminUi.td}>{u.display_name}</td>
                <td className={adminUi.td}>
                  <span className={adminUi.badgeBrand}>{u.member_tier}</span>
                </td>
                <td className={`${adminUi.td} tabular-nums`}>¥{u.wallet_balance}</td>
                <td className={`${adminUi.td} tabular-nums`}>{u.points_balance}</td>
                <td className={adminUi.td}>
                  <span className={u.is_frozen ? adminUi.badgeWarn : adminUi.badgeOk}>
                    {u.is_frozen ? '冻结' : '正常'}
                  </span>
                </td>
                <td className={adminUi.td}>
                  <button type="button" className={adminUi.btnLink} onClick={() => setSelected(u.id)}>
                    详情
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="text-muted flex items-center gap-2 text-sm">
        <button
          type="button"
          disabled={page <= 1}
          onClick={() => setPage((p) => p - 1)}
          className={adminUi.btnGhost}
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
          className={adminUi.btnGhost}
        >
          下一页
        </button>
      </div>

      {selected && detail.data && (
        <div className={`${adminUi.panelPad} animate-fade-in`}>
          <div className="flex items-start justify-between gap-2">
            <div>
              <h3 className="text-ink font-semibold">
                {detail.data.user.display_name}
                <span className="text-muted ml-2 font-normal">（{detail.data.user.account}）</span>
              </h3>
              <p className="text-muted mt-1 text-sm">
                积分 {detail.data.user.points_balance} · 余额 ¥{detail.data.user.wallet_balance} ·{' '}
                {detail.data.user.is_frozen ? '已冻结' : '正常'}
              </p>
            </div>
            <button type="button" className={adminUi.btnGhost} onClick={() => setSelected(null)}>
              关闭
            </button>
          </div>
          <div className="mt-4 flex flex-wrap items-end gap-2">
            <label className="text-muted text-xs">
              积分变动
              <input
                value={pointsDelta}
                onChange={(e) => setPointsDelta(e.target.value)}
                className={`${adminUi.inputInline} ml-1 w-20`}
              />
            </label>
            <button type="button" onClick={() => adjustPoints.mutate()} className={adminUi.btnPrimary}>
              调积分
            </button>
            <label className="text-muted text-xs">
              余额变动
              <input
                value={walletDelta}
                onChange={(e) => setWalletDelta(e.target.value)}
                className={`${adminUi.inputInline} ml-1 w-20`}
              />
            </label>
            <button type="button" onClick={() => adjustWallet.mutate()} className={adminUi.btnInk}>
              调余额
            </button>
            <label className="text-muted text-xs">
              备注
              <input
                value={remark}
                onChange={(e) => setRemark(e.target.value)}
                className={`${adminUi.inputInline} ml-1 w-40`}
              />
            </label>
            <button
              type="button"
              onClick={() => freeze.mutate(!detail.data.user.is_frozen)}
              className={adminUi.btnDanger}
            >
              {detail.data.user.is_frozen ? '解冻' : '冻结'}
            </button>
            <button type="button" onClick={() => forceLogout.mutate()} className={adminUi.btnGhost}>
              强制下线
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
