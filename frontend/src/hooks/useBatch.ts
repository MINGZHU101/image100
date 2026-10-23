import { useEffect } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { batchesApi, type BatchInput } from '@/api/batches'
import { isTerminal } from '@/api/runs'
import { errorMessage } from '@/hooks/useAuth'
import { useRun } from '@/hooks/useRun'
import { toast } from '@/stores/toasts'

const LIST_KEY = ['batches']
const batchKey = (id: string) => ['batch', id]

export function useBatches() {
  return useQuery({ queryKey: LIST_KEY, queryFn: batchesApi.list })
}

function itemsStillRunning(items: { status: string }[] | undefined): boolean {
  if (!items?.length) return false
  return items.some(
    (item) => item.status === 'pending' || item.status === 'queued' || item.status === 'running',
  )
}

export function useBatch(id: string | null) {
  const live = useRun(id)
  const queryClient = useQueryClient()
  const detail = useQuery({
    queryKey: batchKey(id ?? ''),
    queryFn: () => batchesApi.get(id as string),
    enabled: Boolean(id),
    // 按「整批」是否结束轮询，避免只看第一张跑完就停刷新
    refetchInterval: (query) => {
      if (!id) return false
      if (itemsStillRunning(query.state.data?.items)) return 1200
      if (live.status && !isTerminal(live.status)) return 1200
      return false
    },
  })

  useEffect(() => {
    if (!id) return
    const items = detail.data?.items
    const batchDone = items?.length
      ? !itemsStillRunning(items)
      : Boolean(live.status && isTerminal(live.status))
    if (!batchDone) return
    void queryClient.invalidateQueries({ queryKey: batchKey(id) })
    void queryClient.invalidateQueries({ queryKey: LIST_KEY })
  }, [id, live.status, detail.data?.items, queryClient])

  return { ...detail, live }
}

export function useCreateBatch() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: BatchInput) => batchesApi.create(input),
    onSuccess: (run) => {
      void queryClient.invalidateQueries({ queryKey: LIST_KEY })
      queryClient.setQueryData(batchKey(run.id), undefined)
    },
    onError: (error) => toast(errorMessage(error), 'danger'),
  })
}

export function useExportBatch(id: string) {
  return useMutation({
    mutationFn: () => batchesApi.export(id),
    onError: (error) => toast(errorMessage(error), 'danger'),
  })
}
