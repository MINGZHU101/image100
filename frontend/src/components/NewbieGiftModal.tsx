/** 新手大礼包弹窗：标题 + 积分说明 + 马上领取。 */

export default function NewbieGiftModal({
  open,
  claimed,
  busy,
  error,
  points = 2000,
  onClose,
  onClaim,
}: {
  open: boolean
  claimed: boolean
  busy?: boolean
  error?: string
  points?: number
  onClose: () => void
  onClaim: () => void
}) {
  if (!open) return null

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40 px-4">
      <div className="border-line bg-paper rounded-panel shadow-panel relative w-full max-w-sm border p-6 text-center">
        <button
          type="button"
          onClick={onClose}
          className="text-muted hover:text-ink absolute right-3 top-3 text-sm"
          aria-label="关闭"
        >
          ✕
        </button>
        <img
          src="/newbie-gift.png"
          alt="新手礼包"
          className="mx-auto h-24 w-24 object-contain drop-shadow-md"
        />
        <h2 className="text-ink mt-4 text-xl font-semibold">新手大礼包</h2>
        <p className="text-muted mt-2 text-sm">
          {claimed
            ? '礼包已领取，积分已到账'
            : `新用户专享 ${points} 积分，开启电商视觉创作之旅`}
        </p>
        {error && <p className="text-danger mt-3 text-sm">{error}</p>}
        {!claimed ? (
          <button
            type="button"
            disabled={busy}
            onClick={onClaim}
            className="mt-5 w-full rounded-control bg-[#e5484d] py-2.5 text-sm font-medium text-white transition hover:bg-[#d13b40] disabled:opacity-50"
          >
            {busy ? '领取中…' : '马上领取'}
          </button>
        ) : (
          <button
            type="button"
            onClick={onClose}
            className="border-line text-ink hover:bg-soft rounded-control mt-5 w-full border py-2.5 text-sm"
          >
            知道了
          </button>
        )}
      </div>
    </div>
  )
}
