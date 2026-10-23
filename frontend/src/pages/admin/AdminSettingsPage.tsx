import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'

import AdminPageHeader from '@/components/admin/AdminPageHeader'
import { adminUi } from '@/components/admin/adminStyles'
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
    <div className={adminUi.page}>
      <AdminPageHeader
        title="运营参数"
        description="新手礼包、充值兑换汇率等全局开关，保存后立即对用户端生效。"
      />
      <div className={`${adminUi.panelPad} max-w-lg space-y-4`}>
        <label className={adminUi.field}>
          <span className={adminUi.label}>新手礼包积分</span>
          <input value={gift} onChange={(e) => setGift(e.target.value)} className={adminUi.input} />
        </label>
        <label className={adminUi.field}>
          <span className={adminUi.label}>兑换汇率（积分 / 元）</span>
          <input value={rate} onChange={(e) => setRate(e.target.value)} className={adminUi.input} />
        </label>
        <label className={adminUi.field}>
          <span className={adminUi.label}>模拟充值单次上限（元）</span>
          <input
            value={maxYuan}
            onChange={(e) => setMaxYuan(e.target.value)}
            className={adminUi.input}
          />
        </label>
        <button
          type="button"
          onClick={() => save.mutate()}
          disabled={save.isPending}
          className={adminUi.btnPrimary}
        >
          保存参数
        </button>
      </div>
    </div>
  )
}
