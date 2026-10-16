import { useCallback, useEffect, useRef, useState } from 'react'
import {
  cancelAgentRun,
  confirmAgentRun,
  createAgentRun,
  getAgentRun,
  getPlannerOptions,
  type AgentRunOut,
  type PlannerProvider,
} from '../api/agent'

interface UseAgentOptions {
  sessionId: string
  onCompleted: () => void | Promise<void>
}

/** Agent 规划态：规划 → 确认 → 轮询直到 done/failed */
export function useAgent({ sessionId, onCompleted }: UseAgentOptions) {
  const [provider, setProvider] = useState<PlannerProvider>('dashscope')
  const [dashscopeAvailable, setDashscopeAvailable] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [current, setCurrent] = useState<AgentRunOut | null>(null)
  const pollRef = useRef<number | null>(null)

  useEffect(() => {
    let cancelled = false
    void getPlannerOptions()
      .then((options) => {
        if (cancelled) {
          return
        }
        setDashscopeAvailable(options.dashscope_available)
        const initial =
          options.default_provider === 'dashscope' && !options.dashscope_available
            ? 'mock'
            : options.default_provider
        setProvider(initial)
      })
      .catch(() => {
        if (!cancelled) {
          setProvider('mock')
          setDashscopeAvailable(false)
        }
      })
    return () => {
      cancelled = true
    }
  }, [])

  const stopPoll = useCallback(() => {
    if (pollRef.current !== null) {
      window.clearInterval(pollRef.current)
      pollRef.current = null
    }
  }, [])

  useEffect(() => () => stopPoll(), [stopPoll])

  const startPoll = useCallback(
    (agentRunId: string) => {
      stopPoll()
      pollRef.current = window.setInterval(() => {
        void getAgentRun(sessionId, agentRunId)
          .then(async (data) => {
            setCurrent(data)
            if (data.status === 'done') {
              stopPoll()
              setBusy(false)
              await onCompleted()
            } else if (data.status === 'failed' || data.status === 'cancelled') {
              stopPoll()
              setBusy(false)
              if (data.error) {
                setError(data.error)
              }
            }
          })
          .catch((err) => {
            stopPoll()
            setBusy(false)
            setError(err instanceof Error ? err.message : '轮询失败')
          })
      }, 800)
    },
    [sessionId, onCompleted, stopPoll],
  )

  const submitGoal = useCallback(
    async (goal: string) => {
      if (!goal.trim() || busy) {
        return
      }
      setError('')
      setBusy(true)
      setCurrent(null)
      stopPoll()
      try {
        const data = await createAgentRun(sessionId, goal.trim(), provider)
        setCurrent(data)
        setBusy(false)
        if (data.status === 'failed') {
          setError(data.error || data.reply || '规划失败')
        }
      } catch (err) {
        setBusy(false)
        setError(err instanceof Error ? err.message : '规划失败')
      }
    },
    [sessionId, provider, busy, stopPoll],
  )

  const confirm = useCallback(async () => {
    if (!current || current.status !== 'planned' || busy) {
      return
    }
    setError('')
    setBusy(true)
    try {
      await confirmAgentRun(sessionId, current.id)
      startPoll(current.id)
    } catch (err) {
      setBusy(false)
      setError(err instanceof Error ? err.message : '确认失败')
    }
  }, [current, busy, sessionId, startPoll])

  const cancel = useCallback(async () => {
    if (!current || current.status !== 'planned') {
      return
    }
    setError('')
    try {
      const data = await cancelAgentRun(sessionId, current.id)
      setCurrent(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : '取消失败')
    }
  }, [current, sessionId])

  return {
    provider,
    setProvider,
    dashscopeAvailable,
    busy,
    error,
    current,
    submitGoal,
    confirm,
    cancel,
  }
}
