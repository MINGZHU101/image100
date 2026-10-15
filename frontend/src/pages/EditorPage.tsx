import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getSession, type SessionOut } from '../api/sessions'
import { CanvasStage } from '../components/editor/CanvasStage'

/** 编辑器页：加载会话并在画布显示主图层 */
export function EditorPage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const [session, setSession] = useState<SessionOut | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!sessionId) {
      setError('缺少会话 ID')
      setLoading(false)
      return
    }
    let cancelled = false
    async function load() {
      try {
        const data = await getSession(sessionId!)
        if (!cancelled) {
          setSession(data)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : '加载失败')
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [sessionId])

  const mainLayer = session?.document.layers.find((layer) => layer.visible) ?? null
  const imageUrl = mainLayer ? `/api/assets/${mainLayer.asset_id}/file` : ''

  return (
    <div className="editor-page">
      <header className="editor-header">
        <Link to="/" className="back-link">
          ← 返回
        </Link>
        <div>
          <p className="brand">image100</p>
          <h1>{session?.title ?? '编辑器'}</h1>
        </div>
      </header>

      {loading && <p className="muted">正在加载会话…</p>}
      {error && <p className="status-error">{error}</p>}

      {!loading && !error && session && mainLayer && (
        <CanvasStage
          imageUrl={imageUrl}
          canvasWidth={session.document.canvas.width}
          canvasHeight={session.document.canvas.height}
        />
      )}
    </div>
  )
}
