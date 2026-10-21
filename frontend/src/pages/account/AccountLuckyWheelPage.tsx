import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { accountApi } from '@/api/account'
import { luckyWheelApi, type WheelSlot, type WheelState } from '@/api/luckyWheel'
import RechargeModal from '@/components/RechargeModal'
import { errorMessage, useAuthActions, useCurrentUser } from '@/hooks/useAuth'

const GOLD = '#d4af37'
const GOLD_DIM = '#8a7340'
const BLACK = '#0c0a08'

function sectorPath(cx: number, cy: number, r: number, startDeg: number, endDeg: number) {
  const toRad = (d: number) => ((d - 90) * Math.PI) / 180
  const x1 = cx + r * Math.cos(toRad(startDeg))
  const y1 = cy + r * Math.sin(toRad(startDeg))
  const x2 = cx + r * Math.cos(toRad(endDeg))
  const y2 = cy + r * Math.sin(toRad(endDeg))
  const large = endDeg - startDeg > 180 ? 1 : 0
  return `M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2} Z`
}

function labelPosition(cx: number, cy: number, r: number, midDeg: number) {
  const toRad = (d: number) => ((d - 90) * Math.PI) / 180
  return {
    x: cx + r * 0.62 * Math.cos(toRad(midDeg)),
    y: cy + r * 0.62 * Math.sin(toRad(midDeg)),
  }
}

function WheelDisk({
  slots,
  rotation,
  spinning,
}: {
  slots: WheelSlot[]
  rotation: number
  spinning: boolean
}) {
  const n = Math.max(slots.length, 1)
  const step = 360 / n
  const cx = 200
  const cy = 200
  const r = 188

  return (
    <div className="relative mx-auto h-[min(72vw,420px)] w-[min(72vw,420px)]">
      {/* 外环光晕 */}
      <div
        className="absolute inset-0 rounded-full opacity-80"
        style={{
          background:
            'radial-gradient(circle, rgba(212,175,55,0.35) 0%, rgba(12,10,8,0) 70%)',
          filter: 'blur(8px)',
        }}
      />
      <svg
        viewBox="0 0 400 400"
        className="relative h-full w-full drop-shadow-[0_0_40px_rgba(212,175,55,0.25)]"
        style={{
          transform: `rotate(${rotation}deg)`,
          transition: spinning
            ? 'transform 4.2s cubic-bezier(0.12, 0.75, 0.08, 1)'
            : 'none',
        }}
      >
        <defs>
          <linearGradient id="goldRing" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#f5e6a6" />
            <stop offset="45%" stopColor="#d4af37" />
            <stop offset="100%" stopColor="#7a5c12" />
          </linearGradient>
        </defs>
        <circle cx={cx} cy={cy} r={198} fill="url(#goldRing)" />
        <circle cx={cx} cy={cy} r={190} fill={BLACK} />
        {slots.map((slot, i) => {
          const start = i * step
          const end = (i + 1) * step
          const mid = start + step / 2
          const pos = labelPosition(cx, cy, r, mid)
          const jackpot = slot.jackpot
          const drawn = slot.drawn
          const fill = drawn
            ? '#2a2620'
            : jackpot
              ? i % 2 === 0
                ? '#3d2e0f'
                : '#4a3814'
              : i % 2 === 0
                ? '#161310'
                : '#1c1812'
          const stroke = drawn ? '#3a342c' : GOLD_DIM
          return (
            <g key={slot.index}>
              <path
                d={sectorPath(cx, cy, r, start, end)}
                fill={fill}
                stroke={stroke}
                strokeWidth={1}
                opacity={drawn ? 0.45 : 1}
              />
              <text
                x={pos.x}
                y={pos.y}
                fill={drawn ? '#6b655c' : jackpot ? '#f5e6a6' : '#e8d9a8'}
                fontSize={jackpot ? 11 : 10}
                fontWeight={jackpot ? 700 : 500}
                textAnchor="middle"
                dominantBaseline="middle"
                transform={`rotate(${mid}, ${pos.x}, ${pos.y})`}
              >
                {slot.label.length > 8 ? `${slot.label.slice(0, 7)}…` : slot.label}
              </text>
            </g>
          )
        })}
        <circle cx={cx} cy={cy} r={36} fill="#1a1510" stroke={GOLD} strokeWidth={3} />
        <text
          x={cx}
          y={cy}
          fill={GOLD}
          fontSize={13}
          fontWeight={700}
          textAnchor="middle"
          dominantBaseline="middle"
        >
          LUCKY
        </text>
      </svg>
      {/* 顶部指针 */}
      <div
        className="absolute left-1/2 top-0 z-10 -translate-x-1/2 -translate-y-1"
        aria-hidden
      >
        <div
          className="h-0 w-0 border-l-[10px] border-r-[10px] border-t-[22px] border-l-transparent border-r-transparent"
          style={{ borderTopColor: GOLD }}
        />
      </div>
    </div>
  )
}

export default function AccountLuckyWheelPage() {
  const { user } = useCurrentUser()
  const { cacheUser } = useAuthActions()
  const queryClient = useQueryClient()
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [rechargeOpen, setRechargeOpen] = useState(false)
  const [hint, setHint] = useState('')
  const [error, setError] = useState('')
  const [rotation, setRotation] = useState(0)
  const [spinning, setSpinning] = useState(false)
  const [pendingResult, setPendingResult] = useState<string | null>(null)

  const stateQuery = useQuery({
    queryKey: ['lucky-wheel', 'state'],
    queryFn: () => luckyWheelApi.state(),
  })
  const barrageQuery = useQuery({
    queryKey: ['lucky-wheel', 'barrage'],
    queryFn: () => luckyWheelApi.barrage(),
    refetchInterval: 8000,
  })

  const state: WheelState | undefined = stateQuery.data
  const slots = state?.slots ?? []
  const exhausted = Boolean(state?.exhausted)
  const nextCost = state?.next_cost_yuan
  const canAfford =
    nextCost != null && (state?.wallet_balance ?? user?.wallet_balance ?? 0) >= nextCost

  const countdownText = useMemo(() => {
    const c = state?.countdown
    if (!c) return '—'
    return `${c.days} 天 ${c.hours} 时 ${c.minutes} 分`
  }, [state?.countdown])

  const refreshMe = async () => {
    const me = await accountApi.me()
    cacheUser(me.user)
    void queryClient.invalidateQueries({ queryKey: ['account'] })
    void queryClient.invalidateQueries({ queryKey: ['lucky-wheel'] })
  }

  const spinMut = useMutation({
    mutationFn: () => luckyWheelApi.spin(true),
    onSuccess: async (data) => {
      const n = Math.max(data.state.slots.length, 1)
      const step = 360 / n
      // 按 slots 数组顺序定位扇区（与绘制一致）
      const orderIndex = data.state.slots.findIndex((s) => s.index === data.result.slot_index)
      const targetIndex = orderIndex >= 0 ? orderIndex : data.result.slot_index
      const slotCenter = targetIndex * step + step / 2
      setSpinning(true)
      setRotation((prev) => {
        const base = prev % 360
        return prev + 360 * 5 + (360 - slotCenter) - base
      })
      setPendingResult(
        data.result.is_jackpot
          ? `大奖！${data.result.prize_label}${data.result.remark ? ` · ${data.result.remark}` : ''}`
          : `恭喜获得 ${data.result.prize_label}${
              data.result.points_awarded ? `（+${data.result.points_awarded} 积分）` : ''
            }`,
      )
      window.setTimeout(async () => {
        setSpinning(false)
        setHint(
          data.result.is_jackpot
            ? `大奖揭晓：${data.result.prize_label}`
            : `抽中 ${data.result.prize_label}`,
        )
        setPendingResult(null)
        await refreshMe()
        queryClient.setQueryData(['lucky-wheel', 'state'], data.state)
        void queryClient.invalidateQueries({ queryKey: ['lucky-wheel', 'barrage'] })
      }, 4300)
    },
    onError: (err) => {
      const msg = errorMessage(err)
      setError(msg)
      if (msg.includes('充值') || msg.includes('余额不足')) {
        setRechargeOpen(true)
      }
    },
  })

  const recharge = useMutation({
    mutationFn: (yuan: number) => accountApi.mockRecharge(yuan),
    onSuccess: async () => {
      setRechargeOpen(false)
      setError('')
      setHint('充值成功')
      await refreshMe()
      void stateQuery.refetch()
    },
    onError: (err) => setError(errorMessage(err)),
  })

  useEffect(() => {
    if (!hint) return
    const t = window.setTimeout(() => setHint(''), 4000)
    return () => window.clearTimeout(t)
  }, [hint])

  const onClickSpin = () => {
    setError('')
    if (exhausted) return
    if (nextCost == null) return
    if (!canAfford) {
      setError('余额不足，请先充值')
      setRechargeOpen(true)
      return
    }
    setConfirmOpen(true)
  }

  const confirmSpin = () => {
    setConfirmOpen(false)
    if (spinning || spinMut.isPending) return
    spinMut.mutate()
  }

  return (
    <div
      className="-m-6 overflow-hidden rounded-[inherit]"
      style={{
        minHeight: '70vh',
        background:
          'radial-gradient(ellipse at 50% 0%, #2a2114 0%, #0c0a08 55%, #050403 100%)',
      }}
    >
      <div className="relative px-5 pb-10 pt-5">
        {/* 左上角倒计时 */}
        <div className="absolute left-5 top-5 z-20">
          <p className="text-[10px] tracking-[0.2em] text-[#a8945c] uppercase">本期剩余</p>
          <p className="mt-1 font-serif text-lg tracking-wide text-[#f5e6a6] tabular-nums">
            {countdownText}
          </p>
          <p className="mt-0.5 text-xs text-[#7a6b4a]">{state?.period_ym ?? '—'} 期</p>
        </div>

        {/* 弹幕 */}
        <div className="pointer-events-none absolute right-4 top-5 z-20 w-[min(42%,220px)] space-y-1.5 overflow-hidden">
          {(barrageQuery.data ?? []).slice(0, 10).map((item, i) => (
            <div
              key={`${item.created_at}-${i}`}
              className="animate-pulse truncate rounded-full border border-[#d4af37]/25 bg-black/40 px-3 py-1 text-[11px] text-[#e8d9a8]"
              style={{ animationDelay: `${i * 0.15}s` }}
            >
              {item.masked_name} 抽中 {item.prize_label}
            </div>
          ))}
        </div>

        <header className="mx-auto max-w-lg pt-14 text-center">
          <p className="text-[11px] tracking-[0.35em] text-[#a8945c]">BLACK · GOLD</p>
          <h1
            className="mt-2 text-3xl font-semibold tracking-wide text-[#f5e6a6]"
            style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}
          >
            幸运大转盘
          </h1>
          <p className="mt-2 text-sm text-[#9a8b68]">
            每一次旋转，都是对好运的邀请 · 仅消耗账户余额
          </p>
        </header>

        <div className="mt-8">
          {stateQuery.isLoading ? (
            <p className="text-center text-sm text-[#9a8b68]">加载奖池中…</p>
          ) : (
            <WheelDisk slots={slots} rotation={rotation} spinning={spinning} />
          )}
        </div>

        <div className="mx-auto mt-8 max-w-md text-center">
          <p className="text-sm text-[#c4b48a]">
            余额{' '}
            <span className="tabular-nums text-[#f5e6a6]">
              ¥{state?.wallet_balance ?? user?.wallet_balance ?? 0}
            </span>
            <span className="mx-2 text-[#5c5340]">·</span>
            本月第{' '}
            <span className="tabular-nums text-[#f5e6a6]">{(state?.spin_count ?? 0) + 1}</span> /{' '}
            {state?.max_spins ?? 11} 次
          </p>

          {exhausted ? (
            <button
              type="button"
              disabled
              className="mt-5 w-full max-w-xs cursor-not-allowed rounded-full border border-[#5c5340] bg-[#1a1510] py-3.5 text-sm text-[#6b655c]"
            >
              本月已抽完 · 下月重置
            </button>
          ) : (
            <button
              type="button"
              onClick={onClickSpin}
              disabled={spinning || spinMut.isPending || stateQuery.isLoading}
              className="mt-5 w-full max-w-xs rounded-full py-3.5 text-sm font-semibold tracking-wide text-[#1a1205] transition hover:brightness-110 disabled:opacity-60"
              style={{
                background: 'linear-gradient(135deg, #f5e6a6 0%, #d4af37 45%, #a67c00 100%)',
                boxShadow: '0 8px 32px rgba(212,175,55,0.35)',
              }}
            >
              {spinning || spinMut.isPending
                ? '命运转动中…'
                : `抽取好运 · ¥${nextCost ?? '—'}`}
            </button>
          )}

          <p className="mt-3 text-xs text-[#6b655c]">
            <Link to="/account/points" className="text-[#a8945c] underline-offset-2 hover:underline">
              去充值余额
            </Link>
          </p>

          {pendingResult && (
            <p className="mt-4 text-sm font-medium text-[#f5e6a6]">{pendingResult}</p>
          )}
          {hint && !pendingResult && (
            <p className="mt-4 text-sm text-[#d4af37]">{hint}</p>
          )}
          {error && <p className="mt-3 text-sm text-rose-300">{error}</p>}
        </div>

        {state && state.history.length > 0 && (
          <div className="mx-auto mt-10 max-w-md border-t border-[#d4af37]/15 pt-5">
            <p className="mb-2 text-xs tracking-wide text-[#a8945c]">本月记录</p>
            <ul className="space-y-1.5 text-xs text-[#9a8b68]">
              {state.history.map((h) => (
                <li key={h.spin_index} className="flex justify-between gap-2">
                  <span>
                    第 {h.spin_index} 次 · {h.prize_label}
                    {h.is_jackpot ? ' ★' : ''}
                  </span>
                  <span className="tabular-nums text-[#7a6b4a]">-¥{h.cost_yuan}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {confirmOpen && nextCost != null && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/70 px-4">
          <div
            className="w-full max-w-sm rounded-2xl border border-[#d4af37]/40 p-6 shadow-2xl"
            style={{ background: 'linear-gradient(180deg, #1c1610 0%, #0c0a08 100%)' }}
          >
            <h2 className="text-lg font-semibold text-[#f5e6a6]">确认抽奖</h2>
            <p className="mt-3 text-sm leading-relaxed text-[#c4b48a]">
              本次将扣除{' '}
              <span className="font-semibold text-[#f5e6a6]">¥{nextCost}</span>
              <br />
              当前余额{' '}
              <span className="tabular-nums">¥{state?.wallet_balance ?? 0}</span>
              <br />
              本月第{' '}
              <span className="tabular-nums">{(state?.spin_count ?? 0) + 1}</span> 次抽奖
            </p>
            <div className="mt-6 flex gap-3">
              <button
                type="button"
                className="flex-1 rounded-full border border-[#5c5340] py-2.5 text-sm text-[#9a8b68]"
                onClick={() => setConfirmOpen(false)}
              >
                再想想
              </button>
              <button
                type="button"
                className="flex-1 rounded-full py-2.5 text-sm font-semibold text-[#1a1205]"
                style={{
                  background: 'linear-gradient(135deg, #f5e6a6, #d4af37)',
                }}
                onClick={confirmSpin}
              >
                确认抽取
              </button>
            </div>
          </div>
        </div>
      )}

      <RechargeModal
        open={rechargeOpen}
        walletBalance={state?.wallet_balance ?? user?.wallet_balance ?? 0}
        busy={recharge.isPending}
        error={recharge.isError ? errorMessage(recharge.error) : undefined}
        onClose={() => setRechargeOpen(false)}
        onConfirm={(yuan) => recharge.mutate(yuan)}
      />
    </div>
  )
}
