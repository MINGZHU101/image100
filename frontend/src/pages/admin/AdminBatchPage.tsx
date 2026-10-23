import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'

import AdminPageHeader from '@/components/admin/AdminPageHeader'
import { adminUi } from '@/components/admin/adminStyles'
import { adminApi } from '@/api/admin'
import { errorMessage } from '@/hooks/useAuth'
import { toast } from '@/stores/toasts'

export default function AdminBatchPage() {
  const [amount, setAmount] = useState('100')
  const [remark, setRemark] = useState('活动发放')
  const [accountsText, setAccountsText] = useState('')
  const [allUsers, setAllUsers] = useState(false)

  const grant = useMutation({
    mutationFn: () => {
      const accounts = allUsers
        ? null
        : accountsText
            .split(/[\n,，\s]+/)
            .map((s) => s.trim())
            .filter(Boolean)
      return adminApi.batchGrant({
        amount: Number(amount),
        remark,
        accounts,
      })
    },
    onSuccess: (res) => toast(`已向 ${res.granted_users} 人发放各 ${res.amount} 积分`),
    onError: (e) => toast(errorMessage(e), 'danger'),
  })

  return (
    <div className={adminUi.page}>
      <AdminPageHeader
        title="批量发分"
        description="向指定账号或全体未冻结用户发放活动积分，请谨慎操作。"
      />
      <div className={`${adminUi.panelPad} max-w-lg space-y-4`}>
        <label className={adminUi.field}>
          <span className={adminUi.label}>每人积分</span>
          <input
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            className={adminUi.input}
          />
        </label>
        <label className={adminUi.field}>
          <span className={adminUi.label}>备注</span>
          <input
            value={remark}
            onChange={(e) => setRemark(e.target.value)}
            className={adminUi.input}
          />
        </label>
        <label className="text-ink flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={allUsers}
            onChange={(e) => setAllUsers(e.target.checked)}
            className="accent-brand"
          />
          向全体未冻结用户发放
        </label>
        {!allUsers && (
          <label className={adminUi.field}>
            <span className={adminUi.label}>账号列表（换行或逗号分隔）</span>
            <textarea
              value={accountsText}
              onChange={(e) => setAccountsText(e.target.value)}
              rows={5}
              className={adminUi.textarea}
            />
          </label>
        )}
        <button
          type="button"
          disabled={grant.isPending}
          onClick={() => grant.mutate()}
          className={adminUi.btnPrimary}
        >
          确认发放
        </button>
      </div>
    </div>
  )
}
