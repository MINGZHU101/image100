import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getSession, type SessionOut } from '../api/sessions'
import { AgentConversation } from '../components/editor/AgentConversation'
import { CanvasStage } from '../components/editor/CanvasStage'
import { EditorToolbar } from '../components/editor/EditorToolbar'
import { ProgressBar } from '../components/editor/ProgressBar'
import { useAgent } from '../hooks/useAgent'
import { useToolRun } from '../hooks/useToolRun'

/** 编辑器页：工具栏 + Agent 对话 + 画布 */
export function EditorPage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const [session, setSession] = useState<SessionOut | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const reloadSession = useCallback(async () => {
    if (!sessionId) {
      return
    }
    const data = await getSession(sessionId)
    setSession(data)
  }, [sessionId])

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

  const onCompleted = useCallback(async () => {
    try {
      await reloadSession()
    } catch (err) {
      setError(err instanceof Error ? err.message : '刷新会话失败')
    }
  }, [reloadSession])

  const { progress, message, running, error: runError, runTool } = useToolRun({
    sessionId: sessionId ?? '',
    onCompleted,
  })

  const agent = useAgent({
    sessionId: sessionId ?? '',
    onCompleted,
  })

  const mainLayer = session?.document.layers.find((layer) => layer.visible) ?? null
  const imageUrl = mainLayer
    ? `/api/assets/${mainLayer.asset_id}/file?t=${session?.updated_at ?? ''}`
    : ''

  const toolsBusy = running || agent.busy

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

      {sessionId && !loading && !error && session && (
        <EditorToolbar
          sessionId={sessionId}
          disabled={toolsBusy}
          onRunTool={(name, params) => {
            void runTool(name, params)
          }}
        />
      )}

      <ProgressBar progress={progress} message={message} visible={running || progress > 0} />
      {runError && <p className="status-error">{runError}</p>}

      {loading && <p className="muted">正在加载会话…</p>}
      {error && <p className="status-error">{error}</p>}

      {!loading && !error && session && mainLayer && sessionId && (
        <div className="editor-body">
          <CanvasStage
            imageUrl={imageUrl}
            canvasWidth={session.document.canvas.width}
            canvasHeight={session.document.canvas.height}
          />
          <AgentConversation
            provider={agent.provider}
            dashscopeAvailable={agent.dashscopeAvailable}
            busy={agent.busy}
            error={agent.error}
            current={agent.current}
            onProviderChange={agent.setProvider}
            onSubmit={(goal) => {
              void agent.submitGoal(goal)
            }}
            onConfirm={() => {
              void agent.confirm()
            }}
            onCancel={() => {
              void agent.cancel()
            }}
          />
        </div>
      )}
    </div>
  )
}
