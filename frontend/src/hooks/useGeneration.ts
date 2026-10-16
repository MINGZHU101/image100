import { useCallback, useEffect, useRef, useState } from 'react'
import { subscribeRunEvents } from '../api/events'
import {
  createGeneration,
  getGeneration,
  getImageProviderOptions,
  type ImageProvider,
} from '../api/generations'

/** 创作页：Mock/真实切换 + 入队 + 进度 + 候选图 */
export function useGeneration() {
  const [provider, setProvider] = useState<ImageProvider>('dashscope')
  const [dashscopeAvailable, setDashscopeAvailable] = useState(true)
  const [busy, setBusy] = useState(false)
  const [progress, setProgress] = useState(0)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [assetIds, setAssetIds] = useState<string[]>([])
  const closeRef = useRef<(() => void) | null>(null)

  useEffect(() => {
    let cancelled = false
    void getImageProviderOptions()
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

  useEffect(() => () => closeRef.current?.(), [])

  const generate = useCallback(
    async (prompt: string, count: number) => {
      if (!prompt.trim() || busy) {
        return
      }
      setError('')
      setAssetIds([])
      setProgress(0)
      setMessage('排队中…')
      setBusy(true)
      closeRef.current?.()
      try {
        const created = await createGeneration({
          prompt: prompt.trim(),
          width: 1024,
          height: 1024,
          count,
          image_provider: provider,
        })
        closeRef.current = subscribeRunEvents(created.generation_id, (eventName, data) => {
          if (eventName === 'progress') {
            setProgress(data.progress ?? 0)
            setMessage(data.message ?? '生成中…')
          }
        })
        for (let i = 0; i < 120; i += 1) {
          await new Promise((resolve) => window.setTimeout(resolve, 800))
          const current = await getGeneration(created.generation_id)
          setProgress(current.progress)
          if (current.status === 'succeeded') {
            setAssetIds(current.result_asset_ids)
            setMessage('完成')
            setBusy(false)
            closeRef.current?.()
            return
          }
          if (current.status === 'failed') {
            setError(current.error || '生图失败')
            setBusy(false)
            closeRef.current?.()
            return
          }
        }
        setError('生图超时')
        setBusy(false)
      } catch (err) {
        setBusy(false)
        setError(err instanceof Error ? err.message : '生图失败')
      }
    },
    [busy, provider],
  )

  return {
    provider,
    setProvider,
    dashscopeAvailable,
    busy,
    progress,
    message,
    error,
    assetIds,
    generate,
  }
}
