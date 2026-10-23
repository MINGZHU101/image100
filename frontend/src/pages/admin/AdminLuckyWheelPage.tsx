import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'

import AdminPageHeader from '@/components/admin/AdminPageHeader'
import { adminUi } from '@/components/admin/adminStyles'
import { adminApi } from '@/api/admin'
import { toast } from '@/stores/toasts'

type SlotEdit = {
  index: number
  kind: string
  label: string
  points: number
  weight: number
  jackpot?: boolean
}

export default function AdminLuckyWheelPage() {
  const queryClient = useQueryClient()
  const [q, setQ] = useState('')
  const [period, setPeriod] = useState('')
  const [jackpotOnly, setJackpotOnly] = useState(false)
  const [page, setPage] = useState(1)
  const [costsText, setCostsText] = useState('')
  const [jackpotProb, setJackpotProb] = useState('0.02')
  const [slots, setSlots] = useState<SlotEdit[]>([])

  const spins = useQuery({
    queryKey: ['admin', 'lucky-wheel', 'spins', q, period, jackpotOnly, page],
    queryFn: () =>
      adminApi.luckyWheelSpins({
        q: q || undefined,
        period_ym: period || undefined,
        jackpot_only: jackpotOnly,
        page,
      }),
  })

  const config = useQuery({
    queryKey: ['admin', 'lucky-wheel', 'config'],
    queryFn: () => adminApi.luckyWheelConfig(),
  })

  useEffect(() => {
    if (!config.data?.next) return
    setCostsText(config.data.next.costs.join(','))
    setJackpotProb(String(config.data.next.jackpot_prob_each ?? 0.02))
    setSlots(config.data.next.slots.map((s) => ({ ...s })))
  }, [config.data])

  const save = useMutation({
    mutationFn: () => {
      const costs = costsText
        .split(',')
        .map((x) => Number(x.trim()))
        .filter((n) => Number.isFinite(n) && n > 0)
      return adminApi.saveLuckyWheelNext({
        costs,
        slots: slots.map((s) => ({ ...s })),
        jackpot_prob_each: Number(jackpotProb),
      })
    },
    onSuccess: (res) => {
      toast(res.message || '已保存，下月生效')
      void queryClient.invalidateQueries({ queryKey: ['admin', 'lucky-wheel', 'config'] })
    },
    onError: () => toast('保存失败'),
  })

  const updateSlot = (i: number, patch: Partial<SlotEdit>) => {
    setSlots((prev) => prev.map((s, idx) => (idx === i ? { ...s, ...patch } : s)))
  }

  return (
    <div className={adminUi.page}>
      <AdminPageHeader
        title="幸运大转盘"
        description="查看全站抽奖记录，并配置下月奖池（本月进行中的奖池不受影响）。"
      />

      <section className={adminUi.panelPad}>
        <h3 className={adminUi.sectionTitle}>全站抽奖记录</h3>
        <div className="mt-3 flex flex-wrap items-end gap-3">
          <label className={adminUi.field}>
            <span className={adminUi.label}>账号/昵称</span>
            <input
              value={q}
              onChange={(e) => {
                setPage(1)
                setQ(e.target.value)
              }}
              className={adminUi.inputInline}
            />
          </label>
          <label className={adminUi.field}>
            <span className={adminUi.label}>周期 YYYY-MM</span>
            <input
              value={period}
              onChange={(e) => {
                setPage(1)
                setPeriod(e.target.value)
              }}
              placeholder="2026-10"
              className={adminUi.inputInline}
            />
          </label>
          <label className="text-ink flex items-center gap-2 pb-2 text-sm">
            <input
              type="checkbox"
              checked={jackpotOnly}
              onChange={(e) => {
                setPage(1)
                setJackpotOnly(e.target.checked)
              }}
              className="accent-brand"
            />
            仅大奖
          </label>
        </div>

        <div className={`${adminUi.tableWrap} mt-4`}>
          <table className="min-w-full text-left">
            <thead className={adminUi.thead}>
              <tr>
                {['时间', '账号', '周期', '次数', '费用', '奖项', '积分'].map((h) => (
                  <th key={h} className={adminUi.th}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(spins.data?.items ?? []).map((row) => (
                <tr key={row.id} className="hover:bg-soft/60 transition-colors">
                  <td className={`${adminUi.td} text-muted text-xs`}>
                    {new Date(row.created_at).toLocaleString()}
                  </td>
                  <td className={adminUi.td}>
                    {row.account}
                    {row.is_jackpot ? (
                      <span className={`${adminUi.badgeBrand} ml-1`}>大奖</span>
                    ) : null}
                  </td>
                  <td className={adminUi.td}>{row.period_ym}</td>
                  <td className={adminUi.td}>{row.spin_index}</td>
                  <td className={adminUi.td}>¥{row.cost_yuan}</td>
                  <td className={adminUi.td}>{row.prize_label}</td>
                  <td className={`${adminUi.td} tabular-nums`}>{row.points_awarded}</td>
                </tr>
              ))}
              {!spins.data?.items.length && (
                <tr>
                  <td colSpan={7} className={`${adminUi.td} text-faint text-center`}>
                    暂无记录
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="text-muted mt-3 flex items-center gap-3 text-sm">
          <button
            type="button"
            disabled={page <= 1}
            className={adminUi.btnGhost}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            上一页
          </button>
          <span>
            第 {page} 页 · 共 {spins.data?.total ?? 0} 条
          </span>
          <button
            type="button"
            className={adminUi.btnGhost}
            onClick={() => setPage((p) => p + 1)}
            disabled={
              !spins.data || page * (spins.data.page_size || 20) >= spins.data.total
            }
          >
            下一页
          </button>
        </div>
      </section>

      <section className={`${adminUi.panelPad} max-w-3xl space-y-4`}>
        <div>
          <h3 className={adminUi.sectionTitle}>奖池配置（下月生效）</h3>
          <p className={`${adminUi.muted} mt-1`}>
            当前周期 {config.data?.period_ym ?? '—'}。{config.data?.note}
          </p>
          <p className={`${adminUi.faint} mt-1`}>
            本月奖池只读：费用 [{(config.data?.current.costs ?? []).join(', ')}] ·{' '}
            {(config.data?.current.slots ?? []).length} 格
          </p>
        </div>

        <label className={adminUi.field}>
          <span className={adminUi.label}>下月费用序列（逗号分隔，元）</span>
          <input
            value={costsText}
            onChange={(e) => setCostsText(e.target.value)}
            className={`${adminUi.input} font-mono`}
          />
        </label>
        <label className={adminUi.field}>
          <span className={adminUi.label}>单个大奖初始概率（0~1，前端不展示）</span>
          <input
            value={jackpotProb}
            onChange={(e) => setJackpotProb(e.target.value)}
            className={`${adminUi.input} w-40`}
          />
        </label>

        <div className="space-y-2">
          <p className={adminUi.sectionTitle}>下月扇区</p>
          {slots.map((slot, i) => (
            <div
              key={`${slot.index}-${i}`}
              className="border-line bg-soft/40 grid grid-cols-2 gap-2 rounded-[12px] border p-3 md:grid-cols-6"
            >
              <label className="text-xs">
                <span className={adminUi.label}>文案</span>
                <input
                  value={slot.label}
                  onChange={(e) => updateSlot(i, { label: e.target.value })}
                  className={adminUi.input}
                />
              </label>
              <label className="text-xs">
                <span className={adminUi.label}>类型</span>
                <select
                  value={slot.kind}
                  onChange={(e) =>
                    updateSlot(i, {
                      kind: e.target.value,
                      jackpot: ['tier_up', 'jackpot_points'].includes(e.target.value),
                    })
                  }
                  className={adminUi.select + ' w-full'}
                >
                  <option value="points">积分</option>
                  <option value="tier_up">会员升一级</option>
                  <option value="jackpot_points">大奖积分</option>
                </select>
              </label>
              <label className="text-xs">
                <span className={adminUi.label}>积分面额</span>
                <input
                  type="number"
                  value={slot.points}
                  onChange={(e) => updateSlot(i, { points: Number(e.target.value) || 0 })}
                  className={adminUi.input}
                />
              </label>
              <label className="text-xs">
                <span className={adminUi.label}>权重（积分格）</span>
                <input
                  type="number"
                  value={slot.weight}
                  onChange={(e) => updateSlot(i, { weight: Number(e.target.value) || 0 })}
                  className={adminUi.input}
                  disabled={Boolean(slot.jackpot) || slot.kind !== 'points'}
                />
              </label>
              <label className="text-ink flex items-end gap-2 text-xs md:col-span-2">
                <input
                  type="checkbox"
                  checked={Boolean(slot.jackpot)}
                  onChange={(e) => updateSlot(i, { jackpot: e.target.checked })}
                  className="accent-brand"
                />
                大奖（弹幕）
              </label>
            </div>
          ))}
        </div>

        <button
          type="button"
          disabled={save.isPending}
          onClick={() => save.mutate()}
          className={adminUi.btnPrimary}
        >
          保存下月配置
        </button>
      </section>
    </div>
  )
}
