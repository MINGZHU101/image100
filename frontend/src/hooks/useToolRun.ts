import { useCallback, useRef, useState } from 'react'
import { subscribeRunEvents } from '../api/events'
import { invokeTool } from '../api/tools'

interface UseToolRunOptions {
  sessionId: string
  onCompleted: () => void | Promise<void>
}

/** 工具调用 + SSE 进度；完成后触发刷新回调 */
export function useToolRun({ sessionId, onCompleted }: UseToolRunOptions) {
  const [progress, setProgress] = useState(0)
  const [message, setMessage] = useState('')
  const [running, setRunning] = useState(false)
  const [error, setError] = useState('')
  const closeRef = useRef<(() => void) | null>(null)

  const runTool = useCallback(
    async (toolName: string, params: Record<string, unknown> = {}) => {
      if (running) {
        return
      }
      setError('')
      setProgress(0)
      setMessage('排队中…')
      setRunning(true)
      closeRef.current?.()

      try {
        const { run_id } = await invokeTool(sessionId, toolName, params)
        closeRef.current = subscribeRunEvents(run_id, (eventName, data) => {
          if (eventName === 'progress') {
            setProgress(data.progress ?? 0)
            setMessage(data.message ?? '处理中…')
            return
          }
          if (eventName === 'completed') {
            setProgress(100)
            setMessage('完成')
            setRunning(false)
            void onCompleted()
            return
          }
          if (eventName === 'error') {
            setError(data.message ?? '工具执行失败')
            setRunning(false)
          }
        })
      } catch (err) {
        setError(err instanceof Error ? err.message : '调用失败')
        setRunning(false)
      }
    },
    [sessionId, running, onCompleted],
  )

  const reset = useCallback(() => {
    closeRef.current?.()
    closeRef.current = null
    setProgress(0)
    setMessage('')
    setError('')
    setRunning(false)
  }, [])

  return { progress, message, running, error, runTool, reset }
}
