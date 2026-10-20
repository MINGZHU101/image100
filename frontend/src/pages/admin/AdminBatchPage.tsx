import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'

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
    <div className="max-w-lg space-y-4">
      <h2 className="text-lg font-semibold text-slate-800">批量发分</h2>
      <label className="block text-sm">
        每人积分
        <input
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          className="mt-1 w-full rounded border px-3 py-2"
        />
      </label>
      <label className="block text-sm">
        备注
        <input
          value={remark}
          onChange={(e) => setRemark(e.target.value)}
          className="mt-1 w-full rounded border px-3 py-2"
        />
      </label>
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" checked={allUsers} onChange={(e) => setAllUsers(e.target.checked)} />
        向全体未冻结用户发放
      </label>
      {!allUsers && (
        <label className="block text-sm">
          账号列表（换行或逗号分隔）
          <textarea
            value={accountsText}
            onChange={(e) => setAccountsText(e.target.value)}
            rows={5}
            className="mt-1 w-full rounded border px-3 py-2"
          />
        </label>
      )}
      <button
        type="button"
        disabled={grant.isPending}
        onClick={() => grant.mutate()}
        className="rounded bg-teal-700 px-4 py-2 text-sm text-white"
      >
        确认发放
      </button>
    </div>
  )
}
