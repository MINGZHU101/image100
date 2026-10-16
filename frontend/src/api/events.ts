/** SSE 事件负载（与后端约定对齐） */
export interface RunEventPayload {
  event?: string
  run_id?: string
  session_id?: string
  asset_id?: string | null
  progress?: number
  message?: string
}

export type RunEventHandler = (eventName: string, data: RunEventPayload) => void

/**
 * 订阅工具运行 SSE。
 * 返回关闭函数；收到 completed/error 后也会自动关闭。
 */
export function subscribeRunEvents(runId: string, onEvent: RunEventHandler): () => void {
  const source = new EventSource(`/api/events/${runId}`)

  const handle = (eventName: string) => (event: MessageEvent) => {
    let data: RunEventPayload = {}
    try {
      data = JSON.parse(event.data) as RunEventPayload
    } catch {
      data = { message: event.data }
    }
    onEvent(eventName, data)
    if (eventName === 'completed' || eventName === 'error') {
      source.close()
    }
  }

  source.addEventListener('progress', handle('progress'))
  source.addEventListener('completed', handle('completed'))
  source.addEventListener('error', handle('error'))

  source.onerror = () => {
    // EventSource 会自动重连；终态后我们已 close，此处忽略
  }

  return () => source.close()
}
