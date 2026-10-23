import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import AdminPageHeader from '@/components/admin/AdminPageHeader'
import { adminUi } from '@/components/admin/adminStyles'
import { adminApi } from '@/api/admin'
import { toast } from '@/stores/toasts'

export default function AdminAnnouncementsPage() {
  const queryClient = useQueryClient()
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const { data } = useQuery({
    queryKey: ['admin', 'announcements'],
    queryFn: () => adminApi.announcements(),
  })

  const create = useMutation({
    mutationFn: () => adminApi.createAnnouncement({ title, body, is_published: true }),
    onSuccess: () => {
      toast('公告已发布')
      setTitle('')
      setBody('')
      queryClient.invalidateQueries({ queryKey: ['admin', 'announcements'] })
    },
  })

  const toggle = useMutation({
    mutationFn: (item: { id: string; title: string; body: string; is_published: boolean }) =>
      adminApi.updateAnnouncement(item.id, {
        title: item.title,
        body: item.body,
        is_published: !item.is_published,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin', 'announcements'] }),
  })

  return (
    <div className={adminUi.page}>
      <AdminPageHeader
        title="公告管理"
        description="发布站内公告，用户登录后可在工作台看到最新通知。"
      />

      <div className={`${adminUi.panelPad} space-y-3`}>
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="标题"
          className={adminUi.input}
        />
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="正文"
          rows={3}
          className={adminUi.textarea}
        />
        <button
          type="button"
          disabled={!title.trim() || create.isPending}
          onClick={() => create.mutate()}
          className={adminUi.btnPrimary}
        >
          发布公告
        </button>
      </div>

      <ul className="space-y-3">
        {data?.map((item) => (
          <li key={item.id} className={`${adminUi.panelPad} text-sm`}>
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-ink font-medium">{item.title}</p>
                  <span className={item.is_published ? adminUi.badgeOk : adminUi.badgeWarn}>
                    {item.is_published ? '已发布' : '已下线'}
                  </span>
                </div>
                <p className="text-muted mt-1 whitespace-pre-wrap">{item.body}</p>
                <p className="text-faint mt-2 text-xs">{item.created_at}</p>
              </div>
              <button
                type="button"
                onClick={() => toggle.mutate(item)}
                className={`${adminUi.btnGhost} shrink-0`}
              >
                {item.is_published ? '下线' : '上线'}
              </button>
            </div>
          </li>
        ))}
        {!data?.length && <li className={adminUi.faint}>暂无公告</li>}
      </ul>
    </div>
  )
}
