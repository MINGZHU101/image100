import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getSession, patchSelection, type SessionOut } from '../api/sessions'
import { AgentConversation } from '../components/editor/AgentConversation'
import { CanvasStage } from '../components/editor/CanvasStage'
import { EditorToolbar } from '../components/editor/EditorToolbar'
import { ProgressBar } from '../components/editor/ProgressBar'
import { useAgent } from '../hooks/useAgent'
import { useSelection } from '../hooks/useSelection'
import { useToolRun } from '../hooks/useToolRun'
import type { CanvasSelection, SelectionMode } from '../types/selection'

/** 编辑器页：选区 + 工具栏 + Agent 对话 + 画布 */
export function EditorPage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const [session, setSession] = useState<SessionOut | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const selectionApi = useSelection()

  const syncSelection = useCallback(
    async (next: CanvasSelection | null) => {
      if (!sessionId) {
        return
      }
      try {
        const data = await patchSelection(sessionId, next)
        setSession(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : '同步选区失败')
      }
    },
    [sessionId],
  )

  const reloadSession = useCallback(async () => {
    if (!sessionId) {
      return
    }
    const data = await getSession(sessionId)
    setSession(data)
    // 工具成功后后端会清空选区，前端对齐
    const remote = data.document.selection
    selectionApi.replaceSelection(remote)
  }, [sessionId, selectionApi.replaceSelection])

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
          selectionApi.replaceSelection(data.document.selection)
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
    // 仅随 sessionId 加载一次
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

  const handleModeChange = useCallback(
    (mode: SelectionMode) => {
      selectionApi.setMode(mode)
      // 切换到选区工具时清空远端选区，避免脏数据
      if (mode === 'rect' || mode === 'brush') {
        void syncSelection(null)
      }
    },
    [selectionApi, syncSelection],
  )

  const handleClearSelection = useCallback(() => {
    selectionApi.clear()
    void syncSelection(null)
  }, [selectionApi, syncSelection])

  const handleEndStroke = useCallback(() => {
    const next = selectionApi.endStroke()
    void syncSelection(next)
  }, [selectionApi, syncSelection])

  const handleEndRect = useCallback(() => {
    const next = selectionApi.endRect()
    void syncSelection(next)
  }, [selectionApi, syncSelection])

  const handleRunTool = useCallback(
    async (name: string, params?: Record<string, unknown>) => {
      // 局部提亮前再强制同步一次当前选区
      if (name === 'adjust_region') {
        await syncSelection(selectionApi.selection)
      }
      void runTool(name, params)
    },
    [runTool, selectionApi.selection, syncSelection],
  )

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
          selectionMode={selectionApi.mode}
          onSelectionModeChange={handleModeChange}
          onClearSelection={handleClearSelection}
          onRunTool={(name, params) => {
            void handleRunTool(name, params)
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
            selectionMode={selectionApi.mode}
            selection={selectionApi.selection}
            draftPoints={selectionApi.draftPoints}
            onBeginStroke={selectionApi.beginStroke}
            onExtendStroke={selectionApi.extendStroke}
            onEndStroke={handleEndStroke}
            onBeginRect={selectionApi.beginRect}
            onUpdateRect={selectionApi.updateRect}
            onEndRect={handleEndRect}
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
