import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'

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
    <div className="space-y-8">
      <section>
        <h2 className="text-lg font-semibold text-slate-800">幸运大转盘 · 全站记录</h2>
        <div className="mt-3 flex flex-wrap items-end gap-3">
          <label className="text-sm">
            账号/昵称
            <input
              value={q}
              onChange={(e) => {
                setPage(1)
                setQ(e.target.value)
              }}
              className="mt-1 block rounded border px-3 py-1.5"
            />
          </label>
          <label className="text-sm">
            周期 YYYY-MM
            <input
              value={period}
              onChange={(e) => {
                setPage(1)
                setPeriod(e.target.value)
              }}
              placeholder="2026-10"
              className="mt-1 block rounded border px-3 py-1.5"
            />
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={jackpotOnly}
              onChange={(e) => {
                setPage(1)
                setJackpotOnly(e.target.checked)
              }}
            />
            仅大奖
          </label>
        </div>
        <div className="mt-4 overflow-x-auto rounded border bg-white">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-600">
              <tr>
                <th className="px-3 py-2">时间</th>
                <th className="px-3 py-2">账号</th>
                <th className="px-3 py-2">周期</th>
                <th className="px-3 py-2">次数</th>
                <th className="px-3 py-2">费用</th>
                <th className="px-3 py-2">奖项</th>
                <th className="px-3 py-2">积分</th>
              </tr>
            </thead>
            <tbody>
              {(spins.data?.items ?? []).map((row) => (
                <tr key={row.id} className="border-t">
                  <td className="px-3 py-2 text-xs text-slate-500">
                    {new Date(row.created_at).toLocaleString()}
                  </td>
                  <td className="px-3 py-2">
                    {row.account}
                    {row.is_jackpot ? ' ★' : ''}
                  </td>
                  <td className="px-3 py-2">{row.period_ym}</td>
                  <td className="px-3 py-2">{row.spin_index}</td>
                  <td className="px-3 py-2">¥{row.cost_yuan}</td>
                  <td className="px-3 py-2">{row.prize_label}</td>
                  <td className="px-3 py-2">{row.points_awarded}</td>
                </tr>
              ))}
              {!spins.data?.items.length && (
                <tr>
                  <td colSpan={7} className="px-3 py-6 text-center text-slate-400">
                    暂无记录
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="mt-2 flex items-center gap-3 text-sm text-slate-600">
          <button
            type="button"
            disabled={page <= 1}
            className="rounded border px-2 py-1 disabled:opacity-40"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            上一页
          </button>
          <span>
            第 {page} 页 · 共 {spins.data?.total ?? 0} 条
          </span>
          <button
            type="button"
            className="rounded border px-2 py-1"
            onClick={() => setPage((p) => p + 1)}
            disabled={
              !spins.data || page * (spins.data.page_size || 20) >= spins.data.total
            }
          >
            下一页
          </button>
        </div>
      </section>

      <section className="max-w-3xl space-y-4">
        <h2 className="text-lg font-semibold text-slate-800">奖池配置（下月生效）</h2>
        <p className="text-sm text-slate-500">
          当前周期 {config.data?.period_ym ?? '—'}。{config.data?.note}
        </p>
        <p className="text-xs text-slate-400">
          本月奖池只读：费用 [{(config.data?.current.costs ?? []).join(', ')}] ·{' '}
          {(config.data?.current.slots ?? []).length} 格
        </p>

        <label className="block text-sm">
          下月费用序列（逗号分隔，元）
          <input
            value={costsText}
            onChange={(e) => setCostsText(e.target.value)}
            className="mt-1 w-full rounded border px-3 py-2 font-mono text-sm"
          />
        </label>
        <label className="block text-sm">
          单个大奖初始概率（0~1，前端不展示）
          <input
            value={jackpotProb}
            onChange={(e) => setJackpotProb(e.target.value)}
            className="mt-1 w-40 rounded border px-3 py-2"
          />
        </label>

        <div className="space-y-2">
          <p className="text-sm font-medium text-slate-700">下月扇区</p>
          {slots.map((slot, i) => (
            <div
              key={`${slot.index}-${i}`}
              className="grid grid-cols-2 gap-2 rounded border bg-white p-3 md:grid-cols-6"
            >
              <label className="text-xs">
                文案
                <input
                  value={slot.label}
                  onChange={(e) => updateSlot(i, { label: e.target.value })}
                  className="mt-1 w-full rounded border px-2 py-1"
                />
              </label>
              <label className="text-xs">
                类型
                <select
                  value={slot.kind}
                  onChange={(e) =>
                    updateSlot(i, {
                      kind: e.target.value,
                      jackpot: ['tier_up', 'jackpot_points'].includes(e.target.value),
                    })
                  }
                  className="mt-1 w-full rounded border px-2 py-1"
                >
                  <option value="points">积分</option>
                  <option value="tier_up">会员升一级</option>
                  <option value="jackpot_points">大奖积分</option>
                </select>
              </label>
              <label className="text-xs">
                积分面额
                <input
                  type="number"
                  value={slot.points}
                  onChange={(e) => updateSlot(i, { points: Number(e.target.value) || 0 })}
                  className="mt-1 w-full rounded border px-2 py-1"
                />
              </label>
              <label className="text-xs">
                权重（积分格）
                <input
                  type="number"
                  value={slot.weight}
                  onChange={(e) => updateSlot(i, { weight: Number(e.target.value) || 0 })}
                  className="mt-1 w-full rounded border px-2 py-1"
                  disabled={Boolean(slot.jackpot) || slot.kind !== 'points'}
                />
              </label>
              <label className="flex items-end gap-2 text-xs md:col-span-2">
                <input
                  type="checkbox"
                  checked={Boolean(slot.jackpot)}
                  onChange={(e) => updateSlot(i, { jackpot: e.target.checked })}
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
          className="rounded bg-teal-700 px-4 py-2 text-sm text-white disabled:opacity-60"
        >
          保存下月配置
        </button>
      </section>
    </div>
  )
}
