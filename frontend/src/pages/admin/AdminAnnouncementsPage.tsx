import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

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
    mutationFn: () =>
      adminApi.createAnnouncement({ title, body, is_published: true }),
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
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-slate-800">公告管理</h2>
      <div className="space-y-2 rounded-lg border bg-white p-4">
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="标题"
          className="w-full rounded border px-3 py-2 text-sm"
        />
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="正文"
          rows={3}
          className="w-full rounded border px-3 py-2 text-sm"
        />
        <button
          type="button"
          disabled={!title.trim() || create.isPending}
          onClick={() => create.mutate()}
          className="rounded bg-teal-700 px-4 py-2 text-sm text-white disabled:opacity-50"
        >
          发布公告
        </button>
      </div>
      <ul className="space-y-2">
        {data?.map((item) => (
          <li key={item.id} className="rounded-lg border bg-white p-3 text-sm">
            <div className="flex items-start justify-between gap-2">
              <div>
                <p className="font-medium text-slate-800">{item.title}</p>
                <p className="mt-1 text-slate-500">{item.body}</p>
                <p className="mt-1 text-xs text-slate-400">
                  {item.is_published ? '已发布' : '已下线'} · {item.created_at}
                </p>
              </div>
              <button
                type="button"
                onClick={() => toggle.mutate(item)}
                className="shrink-0 text-teal-700 hover:underline"
              >
                {item.is_published ? '下线' : '上线'}
              </button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}
