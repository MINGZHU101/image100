import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'

import { adminApi } from '@/api/admin'
import { toast } from '@/stores/toasts'

export default function AdminSettingsPage() {
  const queryClient = useQueryClient()
  const { data } = useQuery({
    queryKey: ['admin', 'settings'],
    queryFn: () => adminApi.settings(),
  })
  const [gift, setGift] = useState('2000')
  const [rate, setRate] = useState('10')
  const [maxYuan, setMaxYuan] = useState('1000')

  useEffect(() => {
    if (!data) return
    setGift(data.newbie_gift_points || '2000')
    setRate(data.points_per_yuan || '10')
    setMaxYuan(data.mock_recharge_max_yuan || '1000')
  }, [data])

  const save = useMutation({
    mutationFn: () =>
      adminApi.updateSettings({
        newbie_gift_points: Number(gift),
        points_per_yuan: Number(rate),
        mock_recharge_max_yuan: Number(maxYuan),
      }),
    onSuccess: () => {
      toast('参数已保存')
      queryClient.invalidateQueries({ queryKey: ['admin', 'settings'] })
    },
  })

  return (
    <div className="max-w-lg space-y-4">
      <h2 className="text-lg font-semibold text-slate-800">运营参数</h2>
      <label className="block text-sm">
        新手礼包积分
        <input
          value={gift}
          onChange={(e) => setGift(e.target.value)}
          className="mt-1 w-full rounded border px-3 py-2"
        />
      </label>
      <label className="block text-sm">
        兑换汇率（积分 / 元）
        <input
          value={rate}
          onChange={(e) => setRate(e.target.value)}
          className="mt-1 w-full rounded border px-3 py-2"
        />
      </label>
      <label className="block text-sm">
        模拟充值单次上限（元）
        <input
          value={maxYuan}
          onChange={(e) => setMaxYuan(e.target.value)}
          className="mt-1 w-full rounded border px-3 py-2"
        />
      </label>
      <button
        type="button"
        onClick={() => save.mutate()}
        disabled={save.isPending}
        className="rounded bg-teal-700 px-4 py-2 text-sm text-white"
      >
        保存
      </button>
    </div>
  )
}
