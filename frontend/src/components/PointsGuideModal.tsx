import { Link } from 'react-router-dom'

/** 积分不足时引导去模拟充值。 */
export default function PointsGuideModal({
  open,
  message,
  onClose,
}: {
  open: boolean
  message: string
  onClose: () => void
}) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/35 px-4">
      <div className="border-line bg-paper rounded-panel shadow-panel w-full max-w-sm border p-6">
        <h2 className="text-ink text-lg font-semibold">积分不足</h2>
        <p className="text-muted mt-2 text-sm leading-relaxed">{message}</p>
        <p className="text-muted mt-2 text-sm">
          可前往个人中心充值余额，再兑换为积分（测试用，非真实支付）。
        </p>
        <div className="mt-5 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="border-line text-ink hover:bg-soft rounded-control border px-3.5 py-2 text-sm"
          >
            关闭
          </button>
          <Link
            to="/account/points"
            onClick={onClose}
            className="bg-ink hover:bg-dark rounded-control px-3.5 py-2 text-sm font-medium text-white"
          >
            去充值 / 兑换
          </Link>
        </div>
      </div>
    </div>
  )
}
