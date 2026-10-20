import { useEffect, useState } from 'react'

const PRESETS = [10, 20, 50, 100] as const

/** 模拟充值弹窗：预设金额 + 自定义。 */
export default function RechargeModal({
  open,
  walletBalance,
  busy,
  error,
  onClose,
  onConfirm,
}: {
  open: boolean
  walletBalance: number
  busy?: boolean
  error?: string
  onClose: () => void
  onConfirm: (yuan: number) => void
}) {
  const [preset, setPreset] = useState<number | 'custom'>(10)
  const [custom, setCustom] = useState('')

  useEffect(() => {
    if (open) {
      setPreset(10)
      setCustom('')
    }
  }, [open])

  if (!open) return null

  const yuan =
    preset === 'custom' ? Math.floor(Number(custom) || 0) : preset
  const valid = yuan >= 1 && yuan <= 1000

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/35 px-4">
      <div className="border-line bg-paper rounded-panel shadow-panel w-full max-w-md border p-6">
        <h2 className="text-ink text-lg font-semibold">模拟充值</h2>
        <p className="text-muted mt-1 text-sm">
          当前余额 <span className="text-ink font-medium tabular-nums">¥{walletBalance}</span>
          · 测试用，非真实支付 · 单次 ≤ 1000 元
        </p>

        <div className="mt-4 grid grid-cols-4 gap-2">
          {PRESETS.map((amount) => (
            <button
              key={amount}
              type="button"
              onClick={() => setPreset(amount)}
              className={`rounded-control border py-2.5 text-sm font-medium transition-colors ${
                preset === amount
                  ? 'border-brand bg-brand-soft text-brand-strong'
                  : 'border-line text-ink hover:bg-soft'
              }`}
            >
              ¥{amount}
            </button>
          ))}
        </div>

        <button
          type="button"
          onClick={() => setPreset('custom')}
          className={`rounded-control mt-2 w-full border py-2.5 text-sm font-medium transition-colors ${
            preset === 'custom'
              ? 'border-brand bg-brand-soft text-brand-strong'
              : 'border-line text-ink hover:bg-soft'
          }`}
        >
          自定义金额
        </button>

        {preset === 'custom' && (
          <label className="mt-3 block">
            <span className="text-muted mb-1.5 block text-sm">金额（元）</span>
            <input
              type="number"
              min={1}
              max={1000}
              value={custom}
              onChange={(event) => setCustom(event.target.value)}
              placeholder="1～1000"
              className="border-line focus:border-brand rounded-control w-full border px-3.5 py-2.5 text-sm outline-none"
              autoFocus
            />
          </label>
        )}

        <p className="text-muted mt-3 text-xs">
          充值将进入余额；可在下方自行兑换为积分（1 元 = 10 积分）。
        </p>

        {error && <p className="text-danger mt-2 text-sm">{error}</p>}

        <div className="mt-5 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="border-line text-ink hover:bg-soft rounded-control border px-3.5 py-2 text-sm"
          >
            取消
          </button>
          <button
            type="button"
            disabled={!valid || busy}
            onClick={() => onConfirm(yuan)}
            className="bg-ink hover:bg-dark rounded-control px-3.5 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {busy ? '处理中…' : `确认充值 ¥${valid ? yuan : '—'}`}
          </button>
        </div>
      </div>
    </div>
  )
}
